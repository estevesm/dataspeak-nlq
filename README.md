```markdown
# ✨ DataSpeak - Converse com seu Banco de Dados usando IA

DataSpeak é uma plataforma de Business Intelligence (BI) conversacional que permite a qualquer usuário interagir com bancos de dados complexos usando apenas linguagem natural. Faça perguntas, peça por visualizações e forneça contexto de negócio para obter respostas precisas e insights rápidos, tudo através de uma interface de chat intuitiva.

Este projeto transforma a maneira como os dados são acessados, eliminando a necessidade de conhecimento em SQL e capacitando equipes a tomarem decisões baseadas em dados de forma ágil e segura.

## 🚀 Demo

*[INSERIR UM GIF/VÍDEO CURTO DA APLICAÇÃO AQUI: MOSTRANDO A CONEXÃO, UMA PERGUNTA, A RESPOSTA COM O EXPANDER E A MODAL DE CONTEXTO]*

**Exemplo de fluxo de trabalho:**
1.  **Conecte-se:** Insira suas credenciais para qualquer banco de dados suportado (SQL Server, PostgreSQL, MySQL, SQLite).
2.  **Pergunte:** "Qual foi nosso faturamento total no último trimestre, dividido por categoria de produto?"
3.  **Adicione Contexto:** Se o agente não entender um nome de tabela como `tbl_fat_05`, abra o editor de contexto e adicione: "`tbl_fat_05` representa a tabela de faturamento de maio."
4.  **Visualize:** "Ótimo. Agora me mostre isso em um gráfico de barras."

## ✨ Funcionalidades Principais

*   **Conectividade Multi-DB (BYOD):** Traga seu próprio banco de dados! Suporte nativo para **SQL Server, PostgreSQL, MySQL e SQLite**.
*   **Tradução Inteligente de NL para SQL:** Utiliza modelos de linguagem avançados (GPT-4o) para converter perguntas em português em queries SQL complexas.
*   **Contexto de Negócio Customizável:** Uma interface modal permite que o usuário forneça um "dicionário de dados" para que a IA entenda nomenclaturas específicas da empresa (ex: `cli_id` = "ID do Cliente"), aumentando drasticamente a precisão.
*   **Geração Dinâmica de Gráficos:** Crie visualizações de dados (`barras`, `pizza`) diretamente a partir de suas perguntas.
*   **Memória Conversacional:** Mantenha diálogos fluidos. O agente se lembra do contexto de perguntas anteriores.
*   **Guardrail de Segurança:** Previne a execução de queries perigosas (`DROP`, `DELETE`, `UPDATE`), garantindo a integridade dos dados.
*   **Transparência e Depuração:** Cada resposta inclui um log de execução expansível, mostrando exatamente qual query SQL o agente executou.
*   **Interface Web Moderna:** Construída com Streamlit, oferecendo uma experiência de usuário limpa, interativa e responsiva.

## 🛠️ Tecnologias Utilizadas

*   **Linguagem:** Python 3.10+
*   **Framework de LLM:** 🧠 LangChain
*   **Modelo de Linguagem:** 🤖 OpenAI (GPT-4o ou configurável)
*   **Interface Web:** 📊 Streamlit
*   **Bancos de Dados Suportados:** 🗃️ SQL Server, PostgreSQL, MySQL, SQLite
*   **Drivers de Conexão:** SQLAlchemy, psycopg2, mysql-connector-python, pyodbc
*   **Visualização de Dados:** Matplotlib & Seaborn

## 📂 Estrutura do Projeto

O projeto segue uma arquitetura modular e escalável:

```
dataspeak-nlq/
├── app.py                 # Lógica principal da interface com Streamlit
├── requirements.txt       # Dependências do projeto
├── .env                   # Arquivo para chaves de API (desenvolvimento local)
│
├── pipeline/
│   ├── agent_pipeline.py  # Fábrica de agentes, lógica de prompt e execução
│   └── tools/
│       └── viz_tool.py    # Ferramenta customizada para gerar gráficos
│
├── strategies/
│   └── llms/
│       └── openai_llm.py  # Configuração e inicialização do LLM
│
└── utils/
    ├── formatter.py       # Limpeza de logs (remove códigos ANSI)
    └── security.py        # Módulo do Guardrail de segurança para queries SQL
```

## ⚙️ Instalação e Configuração

Siga estes passos para executar o projeto localmente.

### 1. Pré-requisitos
Para conectar ao **SQL Server**, você precisa instalar o driver ODBC apropriado para seu sistema operacional.
- [Download do Microsoft ODBC Driver for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### 2. Clonar e Configurar o Ambiente
```bash
git clone https://github.com/seu-usuario/dataspeak-nlq.git
cd dataspeak-nlq

# Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # ou .\.venv\Scripts\activate no Windows

# Instale as dependências
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente
Para desenvolvimento local, crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
```ini
# .env
OPENAI_LLM_MODEL="gpt-4o-mini"
OPENAI_TEMPERATURE=0.1
```
A chave da API da OpenAI será solicitada diretamente na interface da aplicação.

## ▶️ Como Executar

Com o ambiente configurado, inicie a aplicação Streamlit:

```bash
streamlit run app.py
```

Seu navegador abrirá automaticamente no endereço `http://localhost:8501`.

### Para Deploy (Streamlit Community Cloud)
1.  Faça o deploy do seu repositório.
2.  Nas configurações do app (`Settings > Secrets`), adicione os segredos para o modelo e a temperatura:
    ```toml
    # secrets.toml
    OPENAI_LLM_MODEL = "gpt-4o-mini"
    OPENAI_TEMPERATURE = 0.1
    ```

### Para Deploy em uma máquina virtual LINUX
1. Siga estes passos: [Linux](linux-install.md) 


## 🗺️ Roadmap e Próximas Melhorias

*   [ ] **Suporte a NoSQL:** Adicionar conectividade para bancos de dados como MongoDB.
*   [ ] **Análise de Múltiplas Tabelas:** Melhorar a capacidade do agente de realizar `JOINs` complexos com base em perguntas que envolvem dados de diferentes tabelas.
*   [ ] **Geração de Relatórios:** Um modo onde o agente executa um plano de múltiplas queries e gera um relatório completo em Markdown.
*   [ ] **Cache de Queries:** Implementar um cache para os resultados de queries SQL, não apenas para as chamadas do LLM, para acelerar consultas repetidas aos dados.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT.
```