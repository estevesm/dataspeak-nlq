from pathlib import Path
from dotenv import load_dotenv
import os

# Carrega as variáveis do arquivo .env
load_dotenv()

# OpenAI API Key (necessária para usar as APIs)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Modelo da OpenAI a ser usado (ex: gpt-3.5-turbo, gpt-4, etc.)
OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini-2024-07-18")

# Temperatura da OpenAI a ser usado (ex: 0.2, 0.5, etc.)
OPENAI_TEMPERATURE = os.getenv("OPENAI_TEMPERATURE", "0.2")