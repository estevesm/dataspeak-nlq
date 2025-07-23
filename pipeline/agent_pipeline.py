import langchain
from langchain_community.cache import SQLiteCache
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from langchain.agents import AgentExecutor
from langchain.agents.openai_tools.base import create_openai_tools_agent
import io
from contextlib import redirect_stdout

from strategies.llms.openai_llm import get_openai_llm
from pipeline.tools.viz_tool import create_chart_from_data
from utils.security import is_query_safe
from utils.formatter import clean_ansi_codes

# --- Configuração ---
langchain.llm_cache = SQLiteCache(database_path="data/llm_cache.db")

# --- Prompts ---
BASE_SYSTEM_MESSAGE = """
Você é um agente especialista em análise de dados e SQL.
Sua função é interagir com um banco de dados SQL para responder perguntas em linguagem natural.
Você tem acesso a ferramentas para consultar o banco de dados e para visualizar dados (`create_chart_from_data`).

Instruções:
1.  Analise o HISTÓRICO DA CONVERSA (chat_history) para entender o contexto da pergunta atual (input). 
2.  Se a pergunta atual for uma continuação da conversa anterior, formule sua resposta com base nesse contexto.
3.  Se a pergunta puder ser respondida com uma query SQL, gere e execute-a.
4.  Se o usuário pedir por um 'gráfico' ou 'visualização', use a ferramenta `create_chart_from_data` APÓS obter os dados da query SQL.
5.  Sempre retorne a resposta final de forma clara para o usuário.
6. IMPORTANTE: Você só tem permissão para executar queries de leitura (SELECT). Qualquer tentativa de modificar o banco de dados (DROP, DELETE, UPDATE, etc.) será bloqueada.
"""

TABLE_SELECTION_PROMPT = """
Dada a pergunta do usuário e o histórico da conversa, identifique as tabelas do banco de dados estritamente necessárias para responder à pergunta.

Histórico da Conversa:
{chat_history}

Pergunta do Usuário:
{question}

Tabelas Disponíveis:
{table_list}

Retorne apenas os nomes das tabelas relevantes, separados por vírgula. Se nenhuma tabela parecer relevante, não retorne nada.
Exemplo: Customers, Orders, Products
"""

def _create_sql_agent(llm, db, custom_metadata=""):
    """Função interna para criar um agente SQL com um conjunto específico de tabelas."""
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    all_tools = toolkit.get_tools()

    # Aplica o Guardrail de Segurança
    original_sql_tool = next((tool for tool in all_tools if tool.name == "sql_db_query"), None)

    def safe_sql_run_wrapper(query: str):
        if not is_query_safe(query):
            return "Erro: A sua pergunta resultou em uma query SQL que foi bloqueada por razões de segurança. Por favor, faça apenas perguntas de consulta (leitura de dados)."
        return original_sql_tool.run(query)

    if original_sql_tool:
        safe_sql_query_tool = Tool(
            name="sql_db_query",
            func=safe_sql_run_wrapper,
            description=original_sql_tool.description + " IMPORTANTE: Apenas queries de leitura (SELECT) são permitidas."
        )
        original_tool_index = next((i for i, tool in enumerate(all_tools) if tool.name == "sql_db_query"), -1)
        if original_tool_index != -1:
            all_tools[original_tool_index] = safe_sql_query_tool

    # Adiciona ferramentas customizadas
    custom_tools = [create_chart_from_data]
    final_tools = all_tools + custom_tools

    # Monta o prompt dinâmico
    system_message_content = BASE_SYSTEM_MESSAGE
    if custom_metadata:
        custom_data_dictionary = f"""
--- Dicionário de Dados Customizado Fornecido pelo Usuário ---
O usuário forneceu o seguinte contexto sobre as tabelas e colunas.
Use este dicionário para entender a semântica dos dados e gerar queries mais precisas:

{custom_metadata}
-------------------------------------------------------------
"""
        # A concatenação agora está DENTRO do bloco 'if'.
        system_message_content += custom_data_dictionary  
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_message_content),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent_runnable = create_openai_tools_agent(llm, final_tools, prompt)
    return AgentExecutor(agent=agent_runnable, tools=final_tools, verbose=True, handle_parsing_errors=True)

def get_agent_executor(db_uri: str, openai_api_key: str, custom_metadata: str = ""):
    """
    Cria e retorna um AgentExecutor inicial.
    NOTA: a criação real do agente acontecerá dinamicamente em cada chamada.
    """
    return {
        "db_uri": db_uri,
        "openai_api_key": openai_api_key,
        "custom_metadata": custom_metadata
    }

def run_agent_with_memory(agent_config: dict, question: str, chat_history: list[tuple]):
    """
    Orquestra o fluxo de duas etapas: 1. Seleciona tabelas. 2. Executa o agente SQL.
    """
    db_uri = agent_config["db_uri"]
    openai_api_key = agent_config["openai_api_key"]
    custom_metadata = agent_config["custom_metadata"]
    
    llm = get_openai_llm(api_key=openai_api_key)
    
    # --- ETAPA 1: SELEÇÃO DE TABELAS ---
    db_for_schema = SQLDatabase.from_uri(db_uri)
    all_table_names = db_for_schema.get_usable_table_names()
    
    history_str = "\n".join([f"{role}: {content}" for role, content in chat_history])
    
    selection_prompt = TABLE_SELECTION_PROMPT.format(
        chat_history=history_str,
        question=question,
        table_list=all_table_names
    )
    
    # Captura o log da primeira chamada também
    log_stream = io.StringIO()
    log_stream.write("> Etapa 1: Selecionando tabelas relevantes...\n")
    
    table_selection_response = llm.invoke(selection_prompt)
    selected_tables_str = table_selection_response.content
    
    if not selected_tables_str.strip() or "nenhuma" in selected_tables_str.lower():
         relevant_tables = all_table_names # Fallback: usa todas se nenhuma for selecionada
         log_stream.write("> Nenhuma tabela específica selecionada, usando todas as tabelas (fallback).\n")
    else:
        relevant_tables = [table.strip() for table in selected_tables_str.split(',') if table.strip() in all_table_names]
        log_stream.write(f"> Tabelas selecionadas: {relevant_tables}\n")
    
    log_stream.write("\n> Etapa 2: Executando o agente SQL principal...\n\n")

    # --- ETAPA 2: EXECUÇÃO DO AGENTE SQL PRINCIPAL ---
    # Cria o objeto de DB APENAS com as tabelas relevantes
    db_for_agent = SQLDatabase.from_uri(
        db_uri,
        include_tables=relevant_tables,
        sample_rows_in_table_info=2
    )
    
    # Cria o agente SQL "descartável" para esta chamada
    agent_executor = _create_sql_agent(llm, db_for_agent, custom_metadata)
    
    # Formata o histórico para o agente principal
    formatted_history = [HumanMessage(content=content) if role == "user" else AIMessage(content=content) for role, content in chat_history if isinstance(content, str)]
    
    try:
        with redirect_stdout(log_stream):
            response = agent_executor.invoke({
                "input": question,
                "chat_history": formatted_history
            })
        
        verbose_log_raw = log_stream.getvalue()
        final_answer = response.get("output", "Não consegui encontrar uma resposta.")
        clean_log = clean_ansi_codes(verbose_log_raw)
        
        return final_answer, clean_log
    except Exception as e:
        verbose_log_raw = log_stream.getvalue()
        clean_log = clean_ansi_codes(verbose_log_raw)
        error_message = f"Ocorreu um erro ao executar o agente: {e}"
        return error_message, clean_log