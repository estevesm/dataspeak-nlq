import pandas as pd
from sqlalchemy import create_engine, text
from utils.security import is_query_safe

def execute_sql_query(db_uri: str, query: str) -> pd.DataFrame:
    """
    Conecta-se ao banco de dados, executa uma query SQL de LEITURA e retorna
    o resultado como um DataFrame do Pandas.
    """
    # Validação de segurança básica (redundante com o prompt, mas essencial)
    if not is_query_safe(query):
        # Levanta um erro específico que a UI pode capturar e exibir de forma amigável.
        raise ValueError("Operação não permitida. Apenas queries de consulta que não modificam dados são autorizadas.")
        
    try:
        engine = create_engine(db_uri)
        with engine.connect() as connection:
            result_df = pd.read_sql_query(sql=text(query), con=connection)
        return result_df
    except Exception as e:
        # Retorna o erro de forma que a UI possa exibi-lo
        raise RuntimeError(f"Erro ao executar a query: {e}") from e