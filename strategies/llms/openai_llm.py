from langchain_openai import ChatOpenAI
from config import get_openai_temperature

def get_openai_llm(api_key: str, model_name: str):
    """
    Inicializa e retorna o modelo de linguagem da OpenAI usando a chave de API fornecida.
    """
    if not api_key:
        raise ValueError("A chave da API da OpenAI é necessária para inicializar o modelo.")
    
    if not model_name:
        raise ValueError("O nome do modelo da OpenAI é necessário.")
        
    llm = ChatOpenAI(
        model=model_name,
        temperature=get_openai_temperature(),
        api_key=api_key # Usa a chave passada como argumento
    )
    return llm