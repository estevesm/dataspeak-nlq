import json
from typing import Dict, Any

STORAGE_FILE = "data/saved_questions.json"

def load_saved_questions() -> Dict[str, Any]:
    """Carrega as perguntas salvas do arquivo JSON."""
    try:
        with open(STORAGE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_question(metric_name: str, question: str):
    """Salva uma nova pergunta/métrica no arquivo JSON."""
    questions = load_saved_questions()
    # Usamos o nome da métrica como chave para evitar duplicatas
    questions[metric_name] = {"question": question}
    with open(STORAGE_FILE, 'w') as f:
        json.dump(questions, f, indent=4)
        
def delete_question(metric_name: str):
    """Deleta uma pergunta/métrica salva."""
    questions = load_saved_questions()
    if metric_name in questions:
        del questions[metric_name]
        with open(STORAGE_FILE, 'w') as f:
            json.dump(questions, f, indent=4)