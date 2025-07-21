import streamlit as st
from sqlalchemy.engine import URL
from pipeline.agent_pipeline import get_agent_executor, run_agent_with_memory

# --- Configuração da Página ---
st.set_page_config(
    page_title="DataSpeak 🤖",
    page_icon="🤖",
    layout="wide"
)
# --- NOVO: Adicionando o Logo Alinhado à Esquerda ---
st.image(
    "https://livingnet.com.br/wp-content/uploads/2022/09/WhatsApp-Image-2022-06-29-at-20.20-1.png",
    width=200  # Ajuste a largura conforme necessário
)
# --- FIM DO LOGO ---
st.markdown("<h1 style='font-size: 32px;'>✨ DataSpeak - Converse com seu banco de dados usando IA</h1>", unsafe_allow_html=True)

# --- Lógica de Estado da Sessão ---
def initialize_session_state():
    """Define os valores padrão para o estado da sessão."""
    defaults = {
        "db_type": "SQLite",
        "agent_executor": None,
        "table_names": [],
        "messages": [],
        "connection_configured": False
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
        
        if st.button("🔌 Desconectar"):
            reset_connection()
            st.rerun()

    else:
        # Usa st.session_state para os widgets para manter o estado
        st.session_state.db_type = st.selectbox(
            "Tipo de Banco de Dados",
            ("SQLite", "PostgreSQL", "MySQL"),
            index=["SQLite", "PostgreSQL", "MySQL"].index(st.session_state.db_type) # Garante que o índice seja o correto
        )
        
        if st.session_state.db_type == "SQLite":
            db_path = st.text_input("Caminho para o arquivo .db", "data/database.db")
        else:
            db_host = st.text_input("Host", "localhost")
            db_port = st.text_input("Porta", "5432" if st.session_state.db_type == "PostgreSQL" else "3306")
            db_user = st.text_input("Usuário", "root")
            db_password = st.text_input("Senha", type="password")
            db_name = st.text_input("Nome do Banco de Dados")

        if st.button("🔗 Conectar"):
            if not openai_api_key:
                st.error("Por favor, insira sua chave da API da OpenAI para continuar.")
            else:            
                uri = None
                try:
                    with st.spinner("Conectando e inicializando o agente..."):
                        if st.session_state.db_type == "SQLite":
                            uri = f"sqlite:///{db_path}"
                        else:
                            drivername = "postgresql+psycopg2" if st.session_state.db_type == "PostgreSQL" else "mysql+mysqlconnector"
                            uri = URL.create(
                                drivername=drivername, username=db_user, password=db_password,
                                host=db_host, port=db_port, database=db_name
                            ).render_as_string(hide_password=False)
                        
                        agent_executor, table_names = get_agent_executor(uri, openai_api_key)
                        
                        # Atualiza o estado da sessão
                        st.session_state.agent_executor = agent_executor
                        st.session_state.table_names = table_names
                        st.session_state.connection_configured = True
                        st.session_state.messages = [
                            {"role": "assistant", "content": f"Conectado com sucesso ao banco **{st.session_state.db_type}**! As tabelas `{', '.join(table_names)}` estão disponíveis. Como posso ajudar?"}
                        ]
                    st.rerun()

                except Exception as e:
                    st.error(f"Falha na conexão: {e}")
                    reset_connection() # Garante que o estado volte ao normal em caso de falha

# --- Interface Principal do Chat (sem alterações) ---
if not st.session_state.connection_configured:
    st.info("👈 Por favor, configure e conecte-se a um banco de dados na barra lateral para começar.")
    st.stop()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Faça sua pergunta sobre o banco de dados..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("🤔 Pensando...")

        try:
            history = []
            for msg in st.session_state.messages:
                if msg["role"] == "user": history.append(("user", msg["content"]))
                elif msg["role"] == "assistant": history.append(("ai", msg["content"]))

            answer = run_agent_with_memory(
                agent_executor=st.session_state.agent_executor,
                question=prompt,
                chat_history=history
            )
            message_placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            error_message = f"Ocorreu um erro: {e}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})