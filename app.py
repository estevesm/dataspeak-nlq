import time
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy.engine import URL
from langchain_community.utilities import SQLDatabase
from pipeline.agent_pipeline import get_agent_executor, run_agent_with_memory
from utils.storage import load_saved_questions, save_question, delete_question

# --- Configuração da Página ---
st.set_page_config(
    page_title="DataSpeak",
    page_icon="🤖",
    layout="wide"
)

st.image(
    "https://livingnet.com.br/wp-content/uploads/2022/09/WhatsApp-Image-2022-06-29-at-20.20-1.png",
    width=200
)

st.markdown("<h1 style='font-size: 32px;'>✨ DataSpeak - Converse com seu banco de dados usando IA</h1>", unsafe_allow_html=True)

# --- Lógica de Estado da Sessão ---
def initialize_session_state():
    """Define os valores padrão para o estado da sessão."""
    defaults = {
        "db_type": "SQLite",
        "agent_executor": None,
        "table_names": [],
        "messages": [],
        "connection_configured": False,
        "db_uri": "",
        "openai_api_key": "",
        "custom_metadata": "",
        "dashboard_results": {},
        "show_context_dialog": False
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_connection():
    """Reseta o estado da conexão e limpa o chat."""
    st.session_state.connection_configured = False
    st.session_state.agent_executor = None
    st.session_state.table_names = []
    st.session_state.messages = []
    
# Inicializa o estado uma vez no início da sessão.
initialize_session_state()

# --- Dicionário de Configurações Unificado ---
DB_CONFIGS = {
    "SQLite": {"driver": "sqlite"},
    "PostgreSQL": {"port": "5432", "user": "postgres", "driver": "postgresql+psycopg2"},
    "MySQL": {"port": "3306", "user": "root", "driver": "mysql+mysqlconnector"},
    "SQL Server": {"port": "1433", "user": "sa", "driver": "mssql+pyodbc"}
}

# --- Modal para Salvar Contexto Prompt---
@st.dialog("Editar Contexto de Negócio", width="large" )
def context_editor_dialog():
    """Esta função renderiza o conteúdo da modal."""
    st.info("Descreva suas tabelas e colunas para ajudar a IA a entender a semântica dos seus dados.")
    
    new_metadata = st.text_area(
        "Ex: 'tbl_vendas armazena as vendas. col_dt_venda é a data da transação.'",
        value=st.session_state.custom_metadata,
        height=250,
        key="metadata_input"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar Contexto e Atualizar Agente"):
            with st.spinner("Reconfigurando o agente com o novo contexto..."):
                st.session_state.custom_metadata = new_metadata

                agent_config = get_agent_executor(
                    db_uri=st.session_state.db_uri,
                    openai_api_key=st.session_state.openai_api_key,
                    custom_metadata=st.session_state.custom_metadata
                )

                st.session_state.agent_config = agent_config
                st.toast("Agente atualizado com sucesso!", icon="🧠")
                st.rerun() # Fecha a dialog e atualiza a interface
    
    with col2:
        if st.button("Cancelar"):
            st.rerun() # Apenas fecha a dialog

# --- Modal para Salvar Pergunta ---
@st.dialog("Salvar Pergunta como Métrica")
def save_question_dialog(question_to_save: str):
    st.write("Dê um nome para esta métrica para encontrá-la facilmente no seu dashboard.")
    metric_name = st.text_input("Nome da Métrica", placeholder="Ex: Vendas Mensais")
    st.text_area("Pergunta", value=question_to_save, disabled=True)
    if st.button("Salvar Métrica"):
        if metric_name:
            save_question(metric_name, question_to_save)
            st.toast(f"Métrica '{metric_name}' salva!", icon="🔖")
            st.rerun()
        else:
            st.error("Por favor, dê um nome para a métrica.")

# --- Função para Renderizar Resultados de Métricas ---
def render_metric_result(result):
    """
    Renderiza o resultado de uma métrica de forma inteligente,
    adaptando-se ao tipo de dado (texto, número, tabela, gráfico).
    """
    if isinstance(result, str):
        try:
            # Tenta converter para uma estrutura de dados Python (ex: lista de listas)
            data = eval(result)
            if isinstance(data, list) and data:
                # Se for uma lista de listas/tuplas, é uma tabela
                if all(isinstance(row, (list, tuple)) for row in data):
                    df = pd.DataFrame(data)
                    # Use st.dataframe para tabelas interativas e com bom visual
                    st.dataframe(df, height=210, use_container_width=True)
                else:
                    # Se for uma lista simples, apenas mostra o texto
                    st.markdown(f"<p style='font-family: sans-serif; font-size: 16px;'>{result}</p>", unsafe_allow_html=True)
            # Se for um número (convertido de uma string)
            elif isinstance(data, (int, float)):
                 st.markdown(f"<p style='text-align: center; font-size: 2.5rem; font-weight: bold; margin: 0;'>{data:,.2f}</p>", unsafe_allow_html=True)
            else:
                st.markdown(f"<p style='font-family: sans-serif; font-size: 16px;'>{result}</p>", unsafe_allow_html=True)

        except (SyntaxError, NameError):
            # Se não puder ser convertido (é um texto puro)
            # Tenta detectar se é um texto de sucesso de gráfico
            if "gráfico" in result.lower() and "gerado" in result.lower():
                # O gráfico já foi renderizado pela ferramenta viz_tool.
                # Apenas mostramos uma confirmação.
                st.success("Gráfico renderizado acima! ✅")
            else:
                 # Para textos longos, usamos um markdown normal
                 st.markdown(f"<p style='font-family: sans-serif; font-size: 16px;'>{result}</p>", unsafe_allow_html=True)
    else:
        # Para outros tipos de dados não esperados
        st.write(result)

# --- Formulário de Conexão na Sidebar ---
with st.sidebar:
    st.header("🗝️ Chave da API OpenAI")
    openai_api_key = st.text_input(
        "Insira sua chave da API da OpenAI aqui:",
        type="password",
        help="Sua chave não será armazenada. É necessária para cada sessão."
    )
        
    st.header("⚙️ Conectar ao Banco de Dados")

    if st.session_state.connection_configured:
        st.success(f"Conectado ao **{st.session_state.db_type}**.")
        with st.expander("Tabelas Disponíveis", expanded=True):
            if st.session_state.table_names:
                for table in st.session_state.table_names:
                    st.markdown(f"- `{table}`")
            else:
                st.markdown("Nenhuma tabela encontrada.")

        st.divider()
        
        st.header("🧠 Contexto de Negócio")
        if st.button("Editar Contexto / Dicionário de Dados"):
            context_editor_dialog()
            
        st.divider()
        
        if st.button("🔌 Desconectar"):
            reset_connection()
            st.rerun()
    else:
        db_options = list(DB_CONFIGS.keys())
        # Usar uma chave única para o selectbox e monitorar mudanças
        new_db_type = st.selectbox(
            label="Tipo de Banco de Dados",
            options=db_options,
            index=db_options.index(st.session_state.db_type),
            key="db_type_selector"  # Chave única para o selectbox
        )

        # Verificar se o db_type mudou
        if new_db_type != st.session_state.db_type:
            st.session_state.db_type = new_db_type
            # Limpar variáveis de sessão relacionadas aos campos de entrada
            for key in ['db_host', 'db_port', 'db_user', 'db_password', 'db_name', 'db_path']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

        # Renderizar campos de entrada condicionalmente
        if st.session_state.db_type == "SQLite":
            st.session_state.db_path = st.text_input(
                "Caminho para o arquivo .db",
                value=st.session_state.get('db_path', "data/example.db"),
                key="db_path_input"
            )
        else:
            config = DB_CONFIGS[st.session_state.db_type]
            st.session_state.db_host = st.text_input(
                "Host",
                value=st.session_state.get('db_host', "localhost"),
                key="db_host_input"
            )
            st.session_state.db_port = st.text_input(
                "Porta",
                value=st.session_state.get('db_port', config["port"]),
                key="pipes_input"
            )
            st.session_state.db_user = st.text_input(
                "Usuário",
                value=st.session_state.get('db_user', config["user"]),
                key="db_user_input"
            )
            st.session_state.db_password = st.text_input(
                "Senha",
                type="password",
                value=st.session_state.get('db_password', ""),
                key="db_password_input"
            )
            st.session_state.db_name = st.text_input(
                "Nome do Banco de Dados",
                value=st.session_state.get('db_name', ""),
                key="db_name_input"
            )

        if st.button("🔗 Conectar"):
            if not openai_api_key:
                st.error("Por favor, insira sua chave da API da OpenAI para continuar.")
            else:
                uri = None
                try:
                    with st.spinner("Conectando e inicializando o agente..."):
                        config = DB_CONFIGS[st.session_state.db_type]
                        drivername = config["driver"]

                        if st.session_state.db_type == "SQLite":
                            uri = f"{drivername}:///{st.session_state.db_path}"
                        elif st.session_state.db_type == "SQL Server":
                            odbc_driver = "ODBC Driver 17 for SQL Server".replace(' ', '+')
                            uri = f"{drivername}://{st.session_state.db_user}:{st.session_state.db_password}@{st.session_state.db_host}:{st.session_state.db_port}/{st.session_state.db_name}?driver={odbc_driver}"
                        else:  # Para PostgreSQL e MySQL
                            uri = URL.create(
                                drivername=drivername,
                                username=st.session_state.db_user,
                                password=st.session_state.db_password,
                                host=st.session_state.db_host,
                                port=st.session_state.db_port,
                                database=st.session_state.db_name
                            ).render_as_string(hide_password=False)
                        
                        st.info("Obtendo schema do banco de dados...")
                        db = SQLDatabase.from_uri(uri)
                        table_names = db.get_usable_table_names()        
                        
                        st.session_state.openai_api_key = openai_api_key
                        st.session_state.db_uri = uri
                        st.session_state.custom_metadata = ""
                        
                        agent_config = get_agent_executor(uri, st.session_state.openai_api_key, st.session_state.custom_metadata)
                        
                        st.session_state.agent_config = agent_config
                        st.session_state.table_names = table_names
                        st.session_state.connection_configured = True
                        st.session_state.messages = [
                            {"role": "assistant", "content": f"Conectado com sucesso ao banco **{st.session_state.db_type}**! As tabelas `{', '.join(table_names)}` estão disponíveis. Como posso ajudar?"}
                        ]
                        st.rerun()

                except Exception as e:
                    st.error(f"Falha na conexão: {e}")
                    reset_connection()

# --- Interface Principal do Chat ---
if not st.session_state.connection_configured:
    st.info("👈 Por favor, configure e conecte-se a um banco de dados na barra lateral para começar.")
    st.stop()

# Cria as abas  
tab_chat, tab_dashboard = st.tabs(["💬 Chat", "📊 Dashboard"])

# --- Aba de Chat ---
with tab_chat:
    chat_container = st.container(height=500, border=False)
    
    with chat_container:
        for i, message in enumerate(st.session_state.messages):
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    col1, col2 = st.columns([0.9, 0.1])
                    with col1:
                        st.markdown(message["content"])
                    with col2:
                        if st.button("🔖", key=f"save_{i}", help="Salvar esta pergunta"):
                            save_question_dialog(message["content"])
                else:
                    st.markdown(message["content"])
                    if "verbose_log" in message and message["verbose_log"]:
                        with st.expander("Ver detalhes da execução"):
                            st.code(message["verbose_log"], language="bash")
    
    # Lógica de processamento de prompt do chat
    if prompt := st.chat_input("Faça sua pergunta..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()

    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        last_message = st.session_state.messages[-1]
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("🤔 Pensando..."):
                    history = st.session_state.messages[:-1]
                    answer, log = run_agent_with_memory(
                        agent_config=st.session_state.agent_config,
                        question=last_message["content"],
                        chat_history=history
                    )
                    st.session_state.messages.append({"role": "assistant", "content": answer, "verbose_log": log})
                    st.rerun()
                    
# --- Aba de Dashboard ---
with tab_dashboard:
   
    saved_questions = load_saved_questions()

    if not saved_questions:
        st.info("Você ainda não salvou nenhuma métrica. Volte ao chat e clique no ícone 🔖 para salvar suas perguntas favoritas!")
    else:
        if st.button("🔄 Atualizar Tudo"):
            st.session_state.dashboard_results = {}
            st.rerun()

        cols = st.columns(3)
        col_idx = 0
        for metric_name, data in saved_questions.items():
            with cols[col_idx % len(cols)]:
                with st.container(border=True):
                    # --- Cabeçalho do Card ---
                    st.subheader(metric_name)
                    st.caption(f"Pergunta: *{data['question']}*")
                    
                    # --- Corpo do Card (onde o resultado será renderizado) ---
                    result_placeholder = st.empty()

                    # --- Lógica de Execução ---
                    # Se o resultado não estiver no cache, executa
                    if metric_name not in st.session_state.dashboard_results:
                        with result_placeholder:
                            with st.spinner("Calculando..."):
                                # Se a pergunta contiver "gráfico", o resultado será a renderização
                                # da ferramenta viz_tool, que já usa st.pyplot()
                                if "gráfico" in data["question"].lower() or "plot" in data["question"].lower():
                                    answer, _ = run_agent_with_memory(
                                        agent_config=st.session_state.agent_config,
                                        question=data["question"],
                                        chat_history=[]
                                    )
                                    st.session_state.dashboard_results[metric_name] = answer
                                else:
                                    # Para outras perguntas, pegamos a resposta e renderizamos depois
                                    answer, _ = run_agent_with_memory(
                                        agent_config=st.session_state.agent_config,
                                        question=data["question"],
                                        chat_history=[]
                                    )
                                    st.session_state.dashboard_results[metric_name] = answer
                                
                                # Re-renderiza para exibir o resultado final
                                st.rerun()
                    
                    # --- Lógica de Exibição ---
                    if metric_name in st.session_state.dashboard_results:
                        with result_placeholder:
                            # Chama nossa função de renderização inteligente
                            render_metric_result(st.session_state.dashboard_results[metric_name])

                    # --- Rodapé do Card com Botões de Ação ---
                    st.markdown("---")
                    col_b1, col_b2 = st.columns([0.7, 0.3])
                    with col_b1:
                        if st.button("Recalcular", key=f"run_{metric_name}"):
                            if metric_name in st.session_state.dashboard_results:
                                del st.session_state.dashboard_results[metric_name]
                            st.rerun()
                    with col_b2:
                        if st.button("🗑️", key=f"del_{metric_name}", help="Deletar métrica"):
                            delete_question(metric_name)
                            if metric_name in st.session_state.dashboard_results:
                                del st.session_state.dashboard_results[metric_name]
                            st.toast(f"Métrica '{metric_name}' deletada.")
                            time.sleep(1)
                            st.rerun()
            col_idx += 1