import re

# 1. DENY LIST: Palavras-chave que são sempre proibidas.
# Mantemos esta lista para bloquear operações de escrita/modificação.
DANGEROUS_KEYWORDS = [
    r'\bDROP\b',
    r'\bDELETE\b',
    r'\bTRUNCATE\b',
    r'\bUPDATE\b',
    r'\bGRANT\b',
    r'\bREVOKE\b',
    r'\bALTER\b',
    r'\bINSERT\b'
]
DANGEROUS_SQL_PATTERN = re.compile('|'.join(DANGEROUS_KEYWORDS), re.IGNORECASE)

# 2. ALLOW LIST: Palavras-chave com as quais uma query de leitura segura DEVE começar.
# Adicionamos 'WITH' a esta lista para permitir CTEs.
SAFE_START_KEYWORDS = ['SELECT', 'WITH']

def is_query_safe(query: str) -> bool:
    """
    Verifica se uma query SQL é segura através de uma abordagem de duas camadas:
    1. Garante que a query não contém palavras-chave destrutivas (Deny List).
    2. Garante que a query começa com uma palavra-chave de leitura conhecida (Allow List).
    Retorna True se a query for segura, False caso contrário.
    """
    if not query:
        return False
        
    stripped_query = query.strip().upper()

    # --- Teste 1: Verificar a presença de palavras-chave perigosas ---
    dangerous_match = DANGEROUS_SQL_PATTERN.search(stripped_query)
    if dangerous_match:
        print(f"⚠️ ALERTA DE SEGURANÇA: Query bloqueada! Palavra-chave perigosa encontrada: '{dangerous_match.group()}'")
        return False

    # --- Teste 2: Verificar se a query começa com uma palavra-chave segura ---
    is_safe_start = False
    for keyword in SAFE_START_KEYWORDS:
        if stripped_query.startswith(keyword):
            is_safe_start = True
            break
    
    if not is_safe_start:
        print(f"⚠️ ALERTA DE SEGURANÇA: Query bloqueada! A query não começa com uma operação de leitura segura (ex: SELECT, WITH). Query: \"{query[:100]}...\"")
        return False

    # Se passou em ambos os testes, a query é considerada segura.
    return True