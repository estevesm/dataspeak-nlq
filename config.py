import os
from dotenv import load_dotenv

# Tenta importar o streamlit. Se não estiver disponível (ex: em um worker de backend), não tem problema.
try:
    import streamlit as st
except ImportError:
    st = None

# Carrega as variáveis do .env para desenvolvimento local
load_dotenv()

def get_config_value(key: str, default: any = None):
    """
    Busca um valor de configuração com a seguinte prioridade:
    1. Segredos do Streamlit (para deploy)
    2. Variáveis de ambiente / arquivo .env (para desenvolvimento local)
    3. Valor padrão
    """
    value = default
    # Tenta obter dos segredos do Streamlit primeiro
    if st and hasattr(st, 'secrets') and key in st.secrets:
        value = st.secrets[key]
    else:
        # Se não, tenta obter das variáveis de ambiente
        value = os.getenv(key, default)
    
    return value

def get_openai_model():
    """Retorna o nome do modelo da OpenAI."""
    return get_config_value("OPENAI_LLM_MODEL", "gpt-4o-mini")

def get_openai_temperature():
    """Retorna a temperatura do modelo da OpenAI."""
    # Garante que o valor seja float
    return float(get_config_value("OPENAI_TEMPERATURE", 0.1))