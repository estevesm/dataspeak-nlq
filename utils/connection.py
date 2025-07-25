import hashlib

def get_connection_id(db_type: str, db_host: str = None, db_port: str = None, db_name: str = None, db_path: str = None) -> str:
    """
    Gera um identificador único e seguro para uma configuração de banco de dados.
    """
    if db_type == "SQLite":
        connection_string = f"sqlite_{db_path}"
    else:
        connection_string = f"{db_type}_{db_host}_{db_port}_{db_name}"
    
    # Usamos SHA256 para criar um hash seguro e com nome de arquivo válido.
    return hashlib.sha256(connection_string.encode()).hexdigest()