import langchain
from langchain_community.cache import SQLiteCache
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool

# --- Imports para a construção manual do agente ---
from langchain.agents import AgentExecutor
from langchain.agents.openai_tools.base import create_openai_tools_agent

from strategies.llms.openai_llm import get_openai_llm
from pipeline.tools.viz_tool import create_chart_from_data
from utils.security import is_query_safe

# --- Configuração ---
langchain.llm_cache = SQLiteCache(database_path=".langchain.db")

# --- Prompt do Agente ---
AGENT_SYSTEM_MESSAGE = """
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

def get_agent_executor(db_uri: str):
    """
    Cria e retorna um AgentExecutor configurado para a URI do banco de dados fornecida.
    Esta função é chamada pelo frontend sempre que uma nova conexão é estabelecida.
    """
    llm = get_openai_llm()
    db = SQLDatabase.from_uri(db_uri)
    
    table_names = db.get_usable_table_names()
    
    # --- Ferramentas e Guardrail (lógica idêntica, mas dentro da função) ---
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    all_tools = toolkit.get_tools()

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

    custom_tools = [create_chart_from_data]
    final_tools = all_tools + custom_tools

    # --- Prompt e Criação do Agente (lógica idêntica, mas dentro da função) ---
    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=AGENT_SYSTEM_MESSAGE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ]
    )
    
    agent_runnable = create_openai_tools_agent(llm, final_tools, prompt)
    
    agent_executor = AgentExecutor(
        agent=agent_runnable,
        tools=final_tools,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor, table_names


def run_agent_with_memory(agent_executor: AgentExecutor, question: str, chat_history: list[tuple]):
    """
    Executa o agente que foi passado como argumento.
    """
    formatted_history = []
    for role, content in chat_history:
        if role == "user":
            formatted_history.append(HumanMessage(content=content))
        elif role == "ai":
            formatted_history.append(AIMessage(content=content))
    
    response = agent_executor.invoke({
        "input": question,
        "chat_history": formatted_history
    })
    return response.get("output", "Não consegui encontrar uma resposta.")