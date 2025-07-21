import re

# Expressão regular para encontrar e remover códigos de escape ANSI
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def clean_ansi_codes(text: str) -> str:
    if not text:
        return ""
    return ANSI_ESCAPE_PATTERN.sub('', text)