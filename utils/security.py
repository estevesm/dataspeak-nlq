import re

# Lista de palavras-chave SQL perigosas.
# Usamos \b para garantir que estamos combinando palavras inteiras (ex: não vai pegar 'drop' em 'dropout').
DANGEROUS_KEYWORDS = [
    r'\bDROP\b',
    r'\bDELETE\b',
    r'\bTRUNCATE\b',
    r'\bUPDATE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bALTER\b',
    r'\bINSERT\b' # Podemos até proibir INSERT se o agente for apenas para leitura.
]

# Compilamos a regex para eficiência.
DANGEROUS_SQL_PATTERN = re.compile(
    '|'.join(DANGEROUS_KEYWORDS),
    re.IGNORECASE # Ignora se a palavra está em maiúscula ou minúscula.
)

def is_query_safe(query: str) -> bool:
    """
    Verifica se uma query SQL é segura, ou seja, se não contém palavras-chave perigosas.
    Retorna True se a query for segura (apenas leitura), False caso contrário.
    """
    match = DANGEROUS_SQL_PATTERN.search(query)
    if match:
        print(f"⚠️ ALERTA DE SEGURANÇA: Query bloqueada! Palavra-chave perigosa encontrada: '{match.group()}'")
        return False
    return True