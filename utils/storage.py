import json
import time
from typing import Dict, Any, List
from cryptography.fernet import Fernet, InvalidToken
from config import get_config_value

# --- Configuração de Criptografia ---
# Carrega a chave de criptografia do .env ou st.secrets
encryption_key_str = get_config_value("ENCRYPTION_KEY")
if not encryption_key_str:
    raise ValueError("ENCRYPTION_KEY não encontrada nas configurações. Por favor, gere uma e adicione ao seu .env ou st.secrets.")

# Converte a chave para bytes e inicializa o cifrador
ENCRYPTION_KEY = encryption_key_str.encode()
cipher_suite = Fernet(ENCRYPTION_KEY)

# --- Funções de Armazenamento Genéricas ---
STORAGE_FILE = "data/storage.json"
def _load_storage() -> Dict[str, Any]:
    try:
        with open(STORAGE_FILE, 'r') as f:
            content = f.read()
            if not content: return {"dashboards": {}, "api_key_storage": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"dashboards": {}, "api_key_storage": {}}

def _save_storage(data: Dict[str, Any]):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- NOVAS Funções para Gerenciamento de Dashboards ---
def load_dashboards() -> Dict[str, Any]:
    """Carrega a estrutura completa de dashboards."""
    return _load_storage().get("dashboards", {})

def get_dashboard_names() -> List[str]:
    """Retorna uma lista com os nomes de todos os dashboards salvos."""
    return list(load_dashboards().keys())

def save_metric_to_dashboard(dashboard_name: str, metric_name: str, question: str):
    """Salva ou atualiza uma métrica dentro de um dashboard específico."""
    storage = _load_storage()
    if "dashboards" not in storage:
        storage["dashboards"] = {}
    if dashboard_name not in storage["dashboards"]:
        storage["dashboards"][dashboard_name] = {}
    storage["dashboards"][dashboard_name][metric_name] = {"question": question}
    _save_storage(storage)

def delete_metric_from_dashboard(dashboard_name: str, metric_name: str):
    """Deleta uma métrica de um dashboard específico."""
    storage = _load_storage()
    if dashboard_name in storage.get("dashboards", {}) and metric_name in storage["dashboards"][dashboard_name]:
        del storage["dashboards"][dashboard_name][metric_name]
        _save_storage(storage)

def delete_dashboard(dashboard_name: str):
    """Deleta um dashboard inteiro."""
    storage = _load_storage()
    if dashboard_name in storage.get("dashboards", {}):
        del storage["dashboards"][dashboard_name]
        _save_storage(storage)

# --- Funções Seguras para Gerenciamento da Chave da API ---
def save_api_key(api_key: str):
    """
    Criptografa e salva a chave da API com um timestamp de expiração (24h).
    """
    storage = _load_storage()
    ttl_seconds = 24 * 60 * 60
    expiration_timestamp = int(time.time()) + ttl_seconds
    
    # Criptografa a chave da API antes de salvar
    encrypted_key = cipher_suite.encrypt(api_key.encode()).decode()
    
    storage["api_key_storage"] = {
        "encrypted_key": encrypted_key,
        "expires": expiration_timestamp
    }
    _save_storage(storage)

def load_api_key() -> str:
    """
    Carrega e descriptografa a chave da API, se existir e não estiver expirada.
    """
    storage = _load_storage()
    key_storage = storage.get("api_key_storage")
    
    if not key_storage or "encrypted_key" not in key_storage:
        return ""
    
    expiration_timestamp = key_storage.get("expires", 0)
    
    if int(time.time()) < expiration_timestamp:
        try:
            # Descriptografa a chave antes de retornar
            encrypted_key = key_storage["encrypted_key"].encode()
            decrypted_key = cipher_suite.decrypt(encrypted_key).decode()
            return decrypted_key
        except InvalidToken:
            # Se a chave de criptografia mudou ou o dado está corrompido
            delete_api_key()
            return ""
    else:
        # Se expirou, limpa a chave do armazenamento
        delete_api_key()
        return ""

def delete_api_key():
    """Remove a chave da API do arquivo de armazenamento."""
    storage = _load_storage()
    if "api_key_storage" in storage:
        storage["api_key_storage"] = {}
        _save_storage(storage)