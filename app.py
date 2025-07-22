import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy.engine import URL
from pipeline.agent_pipeline import get_agent_executor, run_agent_with_memory

# --- Configuração da Página ---
st.set_page_config(
    page_title="DataSpeak",
    page_icon="🤖",
    layout="wide"
)

st.image(
    "https://livingnet.com.br/wp-content/uploads/2022/09/WhatsApp-Image-2022-06-29-at-20.20-1.png",
    width=200  # Ajuste a largura conforme necessário
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

# --- Lógica da Modal (st.dialog) ---
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
                agent_executor, _ = get_agent_executor(
                    db_uri=st.session_state.db_uri,
                    openai_api_key=st.session_state.openai_api_key,
                    custom_metadata=st.session_state.custom_metadata
                )
                st.session_state.agent_executor = agent_executor
                st.toast("Agente atualizado com sucesso!", icon="🧠")
                st.rerun() # Fecha a dialog e atualiza a interface
    
    with col2:
        if st.button("Cancelar"):
            st.rerun() # Apenas fecha a dialog

# --- Formulário de Conexão na Sidebar ---
with st.sidebar:
    st.header("🗝️ Chave da API OpenAI")
    openai_api_key = st.text_input(
        "Insira sua chave da API da OpenAI aqui:",
        type="password",
        help="Sua chave não será armazenada. É necessária para cada sessão."
    )
        
    st.header("⚙️ Configuração do Banco de Dados")

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
                value=st.session_state.get('db_path', "data/database.db"),
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
                        
                        st.session_state.openai_api_key = openai_api_key
                        st.session_state.db_uri = uri
                        st.session_state.custom_metadata = ""
                        
                        agent_executor, table_names = get_agent_executor(
                            uri, 
                            st.session_state.openai_api_key, 
                            st.session_state.custom_metadata
                        )
                        
                        st.session_state.agent_executor = agent_executor
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

chat_container = st.container()

with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "verbose_log" in message and message["verbose_log"]:
                with st.expander("Ver detalhes da execução"):
                    st.code(message["verbose_log"], language="bash")
   
# Entrada do usuário (Chat Input)
if prompt := st.chat_input("Faça sua pergunta sobre o banco de dados..."):
    # Adiciona a mensagem do usuário ao histórico ANTES de re-renderizar
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Re-renderiza a mensagem do usuário imediatamente dentro do container
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

    # Execução do agente e resposta
    with chat_container:
        with st.chat_message("assistant"):
            with st.spinner("🤔 Pensando..."):
                try:
                    history = []
                    for msg in st.session_state.messages[:-1]:
                        if msg["role"] == "user": history.append(("user", msg["content"]))
                        elif msg["role"] == "assistant": history.append(("ai", msg["content"]))

                    answer, verbose_log = run_agent_with_memory(
                        agent_executor=st.session_state.agent_executor,
                        question=prompt,
                        chat_history=history
                    )
                    
                    st.markdown(answer)
                    if verbose_log:
                        with st.expander("Ver detalhes da execução"):
                            st.code(verbose_log, language="bash")
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer,
                        "verbose_log": verbose_log
                    })
                except Exception as e:
                    error_message = f"Ocorreu um erro: {e}"
                    st.error(error_message)
                    st.session_state.messages.append({"role": "assistant", "content": error_message, "verbose_log": ""})