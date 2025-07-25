import time
import pandas as pd
import streamlit as st
from sqlalchemy.engine import URL
from langchain_community.utilities import SQLDatabase
from pipeline.agent_pipeline import generate_sql_query
from utils.db_executor import execute_sql_query
from config import OPENAI_MODELS
from utils.storage import  *
from utils.connection import get_connection_id

# --- Configuração da Página ---
st.set_page_config(page_title="DataSpeak", page_icon="✨", layout="wide")
st.markdown("<h3 style='font-size: 26px; margin-top:-40px;'>✨ DataSpeak - Converse com seu banco de dados usando IA</h1>", unsafe_allow_html=True)

# --- Lógica de Estado da Sessão ---
def initialize_session_state():
    defaults = {
        "db_type": "SQLite", 
        "table_names": [], 
        "messages": [], 
        "connection_id": "",
        "connection_configured": False,
        "db_uri": "", 
        "custom_metadata": "", 
        "dashboard_results": {}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
            
    # Carrega a chave da API do armazenamento UMA ÚNICA VEZ
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = load_api_key()            

def reset_connection():
    st.session_state.connection_configured = False
    st.session_state.agent_config = None
    st.session_state.table_names = []
    st.session_state.db_uri = ""
    st.session_state.db_type = "SQLite" # Reseta para o padrão
    st.session_state.messages = [] # Limpa o histórico de chat da conexão anterior
    st.session_state.dashboard_results = {} # Limpa os resultados do dashboard
    st.session_state.custom_metadata = "" # Limpa o contexto

initialize_session_state()

# --- Dicionário de Configurações ---
DB_CONFIGS = {
    "SQLite": {"driver": "sqlite"},
    "PostgreSQL": {"port": "5432", "user": "postgres", "driver": "postgresql+psycopg2"},
    "MySQL": {"port": "3306", "user": "root", "driver": "mysql+mysqlconnector"},
    "SQL Server": {"port": "1433", "user": "sa", "driver": "mssql+pyodbc"}
}

# --- Modais ---
@st.dialog("Editar Contexto de Negócio", width="large")
def context_editor_dialog():
    st.info("Descreva suas tabelas e colunas para ajudar a IA a entender a semântica dos seus dados.")
    new_metadata = st.text_area(
        "Ex: 'tbl_vendas armazena as vendas. col_dt_venda é a data da transação.'",
        value=st.session_state.custom_metadata, height=250, key="metadata_input"
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Salvar Contexto"):
            save_custom_metadata(st.session_state.connection_id, new_metadata)
            st.session_state.custom_metadata = new_metadata
            st.toast("Contexto salvo! A próxima query o utilizará.", icon="🧠")
            st.rerun()
    with col2:
        if st.button("Cancelar"):
            st.rerun()

@st.dialog("Salvar Pergunta como Métrica")
def save_question_dialog(question_to_save: str):
    st.write("Dê um nome para esta métrica e escolha ou crie um dashboard para salvá-la.")
    
    metric_name = st.text_input("**1. Nome da Métrica**", placeholder="Ex: Vendas Mensais")
    st.text_area("Pergunta", value=question_to_save, disabled=True)
    
    st.divider()
    
    st.write("**2. Escolha o Dashboard**")
    
    dashboard_names = get_dashboard_names(st.session_state.connection_id)
    create_new_option = "+ Criar Novo Dashboard"
    
    # Seletor para escolher um dashboard existente ou criar um novo
    selected_dashboard = st.selectbox(
        "Salvar em um dashboard existente",
        options=[create_new_option] + dashboard_names
    )
    
    new_dashboard_name = ""
    if selected_dashboard == create_new_option:
        new_dashboard_name = st.text_input("Nome do Novo Dashboard")

    final_dashboard_name = new_dashboard_name if selected_dashboard == create_new_option else selected_dashboard

    if st.button("Salvar Métrica"):
        if not metric_name:
            st.error("Por favor, dê um nome para a métrica.")
        elif not final_dashboard_name:
            st.error("Por favor, escolha ou crie um nome para o dashboard.")
        else:
            save_metric_to_dashboard(st.session_state.connection_id, final_dashboard_name, metric_name, question_to_save)            
            st.toast(f"Métrica '{metric_name}' salva no dashboard '{final_dashboard_name}'!", icon="🔖")
            st.rerun()
            
# --- Função de Renderização de Resultados ---
def render_metric_result(result_df: pd.DataFrame):
    if result_df.empty:
        st.warning("A consulta não retornou resultados.")
    else:
        # Se o resultado for um único valor (1 linha, 1 coluna), use st.metric
        if len(result_df) == 1 and len(result_df.columns) == 1:
            # Pega o valor e formata se for numérico
            value = result_df.iloc[0, 0]
            if isinstance(value, (int, float)):
                st.metric(label="Resultado", value=f"{value:,.2f}")
            else:
                st.metric(label="Resultado", value=str(value))
        else:
            st.dataframe(result_df, height=210, use_container_width=True)

# --- Formulário de Conexão na Sidebar ---
with st.sidebar:
    
    # Aplica estilo CSS ao bloco que contém a imagem
    st.markdown("""<style>div[data-testid="stImage"] { margin-top: -40px; }</style>""", unsafe_allow_html=True)
    st.image("assets/logo-living.png", width=200)
    
    st.header("🗝️ Chave da API OpenAI")

    # Se uma chave já foi carregada do arquivo, mostra um status
    if st.session_state.openai_api_key:
        st.success("Chave da API carregada do servidor.")
        # Botão para limpar a chave salva no servidor
        if st.button("Esquecer Chave Salva"):
            delete_api_key()
            st.session_state.openai_api_key = ""
            st.rerun()
    else:
        # Campo para inserir uma nova chave
        new_api_key = st.text_input(
            "Insira ou atualize sua chave da API:",
            type="password",
            placeholder="sk-..."
        )
        
        should_save = st.checkbox("Salvar chave no servidor por 24 horas", value=False)

        if st.button("Aplicar Chave"):
            if new_api_key:
                # Aplica a chave à sessão atual
                st.session_state.openai_api_key = new_api_key
                
                # Salva no arquivo JSON se o usuário marcou a caixa
                if should_save:
                    save_api_key(new_api_key)
                    st.toast("Chave salva no servidor por 24h!")
                else:
                    # Garante que qualquer chave antiga seja removida se o usuário desmarcar
                    delete_api_key()

                st.rerun() # Atualiza a UI para refletir o novo estado
            else:
                # Se o usuário clicar em "Aplicar" sem digitar nada, mas uma chave já existe,
                # simplesmente confirma que ela está em uso.
                if st.session_state.openai_api_key:
                    st.toast("Chave da API já está em uso para esta sessão.")
                else:
                    st.warning("Por favor, insira uma chave para aplicar.")

    st.header("🧠 Modelo de IA")
    # Salva a seleção do modelo no estado da sessão
    st.session_state.selected_model = st.selectbox(
        "Escolha o modelo da OpenAI",
        options=OPENAI_MODELS,
        index=OPENAI_MODELS.index(st.session_state.get("selected_model", "gpt-4.1-nano-2025-04-14"))
    )
        
    st.header("📊 Conectar ao Banco de Dados")

    if st.session_state.connection_configured:
        st.success(f"Conectado ao **{st.session_state.db_type}**.")
        with st.expander("Tabelas Disponíveis", expanded=True):
            if st.session_state.table_names:
                for table in st.session_state.table_names:
                    st.markdown(f"- `{table}`")
            else:
                st.markdown("Nenhuma tabela encontrada.")

        st.header("🪄 Contexto de Negócio")
        if st.button("Editar Contexto / Dicionário de Dados"):
            context_editor_dialog()
                    
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
            if not st.session_state.openai_api_key:
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
                        
                        st.session_state.db_uri = uri
                        db = SQLDatabase.from_uri(uri)
                        st.session_state.table_names = db.get_usable_table_names()
                        st.session_state.connection_configured = True
                        st.session_state.messages = [
                            {"role": "assistant", "content": f"Conectado com sucesso! As tabelas `{', '.join(st.session_state.table_names)}` foram encontradas. Faça sua primeira pergunta."}
                        ]
                        
                        connection_id = get_connection_id(
                            db_type=st.session_state.db_type,
                            db_host=st.session_state.get('db_host'),
                            db_port=st.session_state.get('db_port'),
                            db_name=st.session_state.get('db_name'),
                            db_path=st.session_state.get('db_path')
                        )
                        st.session_state.connection_id = connection_id
                        st.session_state.custom_metadata = load_custom_metadata(connection_id)
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"Falha na conexão: {e}")
                    reset_connection()

# --- Lógica Principal com Tabs ---
if not st.session_state.connection_configured:
    st.info("👈 Por favor, configure e conecte-se a um banco de dados na barra lateral para começar.")
    st.stop()

tab_chat, tab_dashboard = st.tabs(["💬 Chat", "📈 Dashboard"])

# --- Aba de Chat ---
with tab_chat:
    # 1. Cria um container para as mensagens com altura fixa e rolagem interna.
    # O 'border=False' remove a borda visual.
    chat_container = st.container(height=620, border=False)

    # 2. Exibe todo o histórico de mensagens DENTRO do container.
    for i, message in enumerate(st.session_state.messages):
        with chat_container:
            with st.chat_message(message["role"]):
                if message["role"] == "user":
                    col1, col2 = st.columns([0.9, 0.1])
                    with col1:
                        st.markdown(message["content"])
                    with col2:
                        # Usamos um ID único para a chave para evitar conflitos no rerun
                        if st.button("🔖", key=f"save_{message['content']}_{i}", help="Salvar esta pergunta"):
                            save_question_dialog(message["content"])
                else:  # Mensagens do assistente
                    # Usamos st.get_option("client.showErrorDetails") para verificar se estamos em modo de depuração
                    if "dataframe" in message and isinstance(message.get("dataframe"), list):
                        try:
                            df_to_show = pd.DataFrame(message["dataframe"])
                            st.dataframe(df_to_show)
                        except Exception:
                            st.write(message["dataframe"]) # Fallback
                    if "content" in message:
                        st.markdown(message["content"])
                    if "query_info" in message:
                        with st.expander("🔍 Ver Query SQL Executada"):
                            st.code(message["query_info"]["query"], language="sql")
                            st.caption(message["query_info"]["explanation"])

    # 3. O chat_input fica FORA do container, renderizado no fluxo principal da página.
    if prompt := st.chat_input("Faça sua pergunta sobre o banco de dados..."):
        # Adiciona a mensagem do usuário ao estado
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Processa a pergunta e gera a resposta do assistente
        #with st.chat_message("assistant"): # Renderiza um placeholder temporário para o assistente
        with st.spinner("🤔 Pensando..."):
            assistant_response = {}
            try:
                # ETAPA 1: Gerar a query SQL
                history = st.session_state.messages[:-1]
                sql_result = generate_sql_query(
                    db_uri=st.session_state.db_uri,
                    openai_api_key=st.session_state.openai_api_key,
                    model_name=st.session_state.get("selected_model", "gpt-4.1-nano-2025-04-14"), # Adicionado fallback
                    question=prompt,
                    custom_metadata=st.session_state.custom_metadata,
                    chat_history=history
                )
                assistant_response["query_info"] = {"query": sql_result.query, "explanation": sql_result.explanation}

                # ETAPA 2: Executar a query
                result_df = execute_sql_query(st.session_state.db_uri, sql_result.query)
                
                # Salva o dataframe no formato correto para re-renderização
                assistant_response["dataframe"] = result_df.to_dict("records")
                assistant_response["content"] = f"Consulta executada com sucesso! {len(result_df)} linha(s) encontrada(s)."

            except Exception as e:
                error_message = f"Ocorreu um problema: {e}"
                assistant_response["content"] = error_message
        
        # Adiciona a resposta completa do assistente ao estado
        st.session_state.messages.append({"role": "assistant", **assistant_response})
        
        # Um único rerun no final para redesenhar a tela com a nova resposta.
        st.rerun()

# --- Aba de Dashboard ---            
with tab_dashboard:
    
    # Garante que temos um connection_id para trabalhar
    if not st.session_state.get("connection_id"):
        st.warning("Aguardando ID da conexão...")
        st.stop()
    
    connection_id = st.session_state.connection_id

    # Carrega apenas os nomes dos dashboards PARA ESTA CONEXÃO >>>
    dashboard_names = get_dashboard_names(connection_id)

    if not dashboard_names:
        st.info("Você ainda não salvou nenhuma métrica. Volte ao chat e clique no ícone 🔖 para criar seu primeiro dashboard!")
        st.stop()

    # Adicionamos um título manual para a seção
    st.markdown("###### Selecione um Dashboard")

    # Injetamos CSS para alinhar verticalmente os itens nas colunas
    st.markdown("""
        <style>
            /* Alvo específico para os contêineres de coluna dentro do app */
            div[data-testid="column"] {
                display: flex;
                align-items: flex-end; /* Alinha os itens na parte inferior */
            }
        </style>
    """, unsafe_allow_html=True)

    # --- Seletor de Dashboard e Controles ---
    col1, col2, col3, col4 = st.columns([0.3, 0.1, 0.1, 0.5])
    
    with col1:
        selected_dashboard_name = st.selectbox(
            "Selecione um Dashboard para visualizar",
            options=dashboard_names,
            key="selected_dashboard",
            label_visibility="collapsed"
        )
    
    with col2:
        if st.button("🔄 Atualizar"):
            if selected_dashboard_name:
                metrics_to_clear = load_dashboard_metrics(connection_id, selected_dashboard_name).keys()
                for metric in metrics_to_clear:
                    # Usamos uma chave composta para o cache de resultados
                    cache_key = f"{connection_id}_{selected_dashboard_name}_{metric}"
                    if cache_key in st.session_state.dashboard_results:
                        del st.session_state.dashboard_results[cache_key]
                st.rerun()
            
    with col3:
        if st.button("🗑️ Deletar", type="primary"):
            st.session_state.confirm_delete = True
            st.rerun()

    # Lógica de confirmação para deleção
    if st.session_state.get("confirm_delete", False):
        st.warning(f"**Você tem certeza que quer deletar o dashboard '{selected_dashboard_name}'?** Esta ação não pode ser desfeita.")
        col_d1, col_d2 = st.columns(2)
        if col_d1.button("Sim, deletar permanentemente"):
            delete_dashboard(connection_id, selected_dashboard_name)
            st.session_state.confirm_delete = False
            st.toast(f"Dashboard '{selected_dashboard_name}' deletado.")
            time.sleep(1)
            st.rerun()
        if col_d2.button("Não, cancelar"):
            st.session_state.confirm_delete = False
            st.rerun()

    #st.divider()
    st.markdown(
        """
        <style>
        .custom-divider {
            border-top: 2px solid #FF4B4B;  /* Cor e espessura da linha */
            margin: 5px 0;  /* Margem acima e abaixo */
        }
        </style>
        <div class="custom-divider"></div>
        """,
        unsafe_allow_html=True
    )
    # --- Renderização dos Cards do Dashboard Selecionado ---
    if selected_dashboard_name:
        st.subheader(f"Métricas de: {selected_dashboard_name}")
        
        # Obtém as métricas do dashboard selecionado
        selected_dashboard_metrics = load_dashboard_metrics(connection_id, selected_dashboard_name)
        
        if not selected_dashboard_metrics:
            st.info("Este dashboard está vazio. Salve algumas métricas nele a partir da aba de Chat!")
        
        # Layout em colunas para os cards
        cols = st.columns(3)
        col_idx = 0
        for metric_name, data in selected_dashboard_metrics.items():
            question = data.get("question", "Pergunta não encontrada.")
            cache_key = f"{connection_id}_{selected_dashboard_name}_{metric_name}"
            with cols[col_idx % len(cols)]:
                with st.container(border=True):
                    st.subheader(metric_name)
                    st.caption(f"Pergunta: *{question}*")
                    result_placeholder = st.empty()
                    
                    # Lógica de Execução e Exibição
                    if cache_key not in st.session_state.dashboard_results:
                        with result_placeholder, st.spinner("Executando..."):
                            try:
                                sql_result = generate_sql_query(
                                    db_uri=st.session_state.db_uri,
                                    openai_api_key=st.session_state.openai_api_key,
                                    model_name=st.session_state.get("selected_model", "gpt-4.1-nano-2025-04-14"),
                                    question=question
                                )
                                result_df = execute_sql_query(st.session_state.db_uri, sql_result.query)
                                st.session_state.dashboard_results[cache_key] = result_df
                                st.rerun()
                            except Exception as e:
                                st.session_state.dashboard_results[cache_key] = pd.DataFrame([{"erro": str(e)}])
                                st.rerun()
                    
                    if cache_key in st.session_state.dashboard_results:
                        result_df = st.session_state.dashboard_results[cache_key]
                        if "erro" in result_df.columns:
                            result_placeholder.error(f"Erro ao calcular: {result_df['erro'][0]}")
                        else:
                            with result_placeholder:
                                render_metric_result(result_df)
                    
                    st.markdown("---")
                    col_b1, col_b2 = st.columns([0.7, 0.3])
                    if col_b1.button("Recalcular", key=f"run_{metric_name}"):
                        if cache_key in st.session_state.dashboard_results:
                            del st.session_state.dashboard_results[cache_key]
                        st.rerun()
                    if col_b2.button("🗑️", key=f"del_{metric_name}", help="Deletar métrica"):
                        delete_metric_from_dashboard(connection_id, selected_dashboard_name, metric_name)
                        if cache_key in st.session_state.dashboard_results:
                            del st.session_state.dashboard_results[cache_key]
                        st.toast(f"Métrica '{metric_name}' deletada.")
                        time.sleep(1)
                        st.rerun()
            col_idx += 1