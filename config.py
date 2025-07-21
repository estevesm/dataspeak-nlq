import os
from dotenv import load_dotenv

# Carrega as variáveis do .env para desenvolvimento local.
# Isso não afeta o ambiente de deploy, que não terá um .env.
load_dotenv()

# Tenta importar o streamlit. Se não estiver disponível, define como None.
try:
    import streamlit as st
except ImportError:
    st = None

def get_config_value(key: str, default: any = None):
    """
    Busca um valor de configuração com a seguinte prioridade:
    1. Segredos do Streamlit (para deploy no Streamlit Community Cloud).
    2. Variáveis de ambiente / arquivo .env (para desenvolvimento local).
    3. Valor padrão, se nada for encontrado.
    """
    value = None
    
    try:
        if st and hasattr(st, 'secrets') and key in st.secrets:
            value = st.secrets[key]
    except (st.errors.Error, AttributeError):
        pass

    if value is None:
        value = os.getenv(key)

    if value is None:
        value = default
        
    return value

def get_openai_model():
    """Retorna o nome do modelo da OpenAI."""
    return get_config_value("OPENAI_LLM_MODEL", "gpt-4o-mini-2024-07-18")

def get_openai_temperature():
    """Retorna a temperatura do modelo da OpenAI."""
    # Garante que o valor retornado seja float.
    return float(get_config_value("OPENAI_TEMPERATURE", 0.1))