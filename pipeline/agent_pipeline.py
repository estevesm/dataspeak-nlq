# pipeline/agent_pipeline.py
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field 
from typing import List

from strategies.llms.openai_llm import get_openai_llm

# --- Modelo de Saída Estruturada ---
class SQLQuery(BaseModel):
    query: str = Field(description="A query SQL completa e sintaticamente correta.")
    explanation: str = Field(description="Uma breve explicação em linguagem natural do que a query SQL faz e por que ela responde à pergunta do usuário.")

# --- Novo Prompt Focado em Geração de SQL ---
SQL_GENERATION_PROMPT = """
Você é um especialista em SQL de classe mundial. Sua tarefa é analisar o schema de um banco de dados, o contexto de negócio e a pergunta de um usuário para gerar uma query SQL precisa e otimizada.

**Regras Importantes:**
1.  Gere APENAS queries de LEITURA (SELECT). NUNCA gere queries de escrita (INSERT, UPDATE, DELETE, DROP, etc.).
2.  Use o Dicionário de Dados Customizado para entender a semântica de nomes de tabelas e colunas (ex: tbl_cli significa tabela de clientes).
3.  Analise o histórico da conversa para entender perguntas de acompanhamento e usar o contexto.
4.  Retorne a query SQL e uma breve explicação no formato JSON solicitado.

**Dialeto SQL do Banco de Dados Alvo:**
`{dialect}`

**Schema do Banco de Dados:**
{schema}

**Dicionário de Dados Customizado:**
{custom_metadata}

**Histórico da Conversa:**
{chat_history}

**Pergunta do Usuário:**
{question}

{format_instructions}
"""

def generate_sql_query(
    db_uri: str,
    openai_api_key: str,
    model_name: str,
    question: str,
    custom_metadata: str = "",
    chat_history: List[tuple] = None
) -> SQLQuery:
    """
    Gera uma query SQL a partir de uma pergunta em linguagem natural.
    Não executa a query, apenas a gera.
    """
    llm = get_openai_llm(api_key=openai_api_key, model_name=model_name)
    db = SQLDatabase.from_uri(db_uri)
    
    dialect = db.dialect # Obtém o dialeto do banco de dados
    schema_info = db.get_table_info()

    # Adaptação para o histórico do Streamlit
    # Assume que chat_history vem como lista de dicionários (roles e content)
    formatted_chat_history = []
    if chat_history:
        for msg in chat_history:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                formatted_chat_history.append(f"{msg['role']}: {msg['content']}")
            elif isinstance(msg, tuple) and len(msg) == 2: # Compatibilidade com (role, content)
                formatted_chat_history.append(f"{msg[0]}: {msg[1]}")
    history_str = "\n".join(formatted_chat_history)

    parser = PydanticOutputParser(pydantic_object=SQLQuery)

    prompt = ChatPromptTemplate.from_template(
        template=SQL_GENERATION_PROMPT,
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )

    # Cria a cadeia LCEL
    chain = prompt | llm | parser

    try:
        result = chain.invoke({
            "dialect": dialect,
            "schema": schema_info,
            "custom_metadata": custom_metadata if custom_metadata else "Nenhum.",
            "chat_history": history_str if history_str else "Nenhum.",
            "question": question
        })
        return result
    except Exception as e:
        if "Failed to parse" in str(e):
            raise RuntimeError(f"A IA não conseguiu gerar uma query válida. Por favor, tente reformular sua pergunta. Detalhes: {e}")
        raise e