from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_LLM_MODEL, OPENAI_TEMPERATURE

def get_openai_llm():
    """Retorna uma instância do LLM da OpenAI."""
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=OPENAI_LLM_MODEL,
        temperature=OPENAI_TEMPERATURE # Baixa temperatura para respostas mais factuais
    )