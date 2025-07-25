# ✨ DataSpeak - Converse com seu Banco de Dados usando IA

DataSpeak é uma plataforma de Business Intelligence (BI) segura e conversacional que permite a qualquer usuário interagir com bancos de dados complexos usando apenas linguagem natural. Faça perguntas, peça por visualizações, forneça contexto de negócio para obter respostas precisas e transforme suas perguntas recorrentes em dashboards dinâmicos de KPIs.

O principal diferencial arquitetural do DataSpeak é a **separação entre a geração de código e a execução**, garantindo que nenhum dado do seu banco de dados seja enviado para a IA, proporcionando uma camada fundamental de segurança e conformidade com a LGPD.

## 🚀 Demo

![Demo do Multimodal Assistant](assets/demo-dataspeak.gif) 

**Exemplo de fluxo de trabalho:**
1.  **Conecte-se com Segurança:** Insira suas credenciais para qualquer banco de dados suportado. Apenas o *schema* (a estrutura) do banco é usado pela IA, nunca os seus dados.
2.  **Pergunte:** "Qual o faturamento total no último trimestre, dividido por categoria de produto?"
3.  **Salve a Métrica:** Clique no ícone 🔖 ao lado da sua pergunta, crie um novo dashboard ou adicione a um existente, e nomeie a métrica como "Faturamento Trimestral por Categoria".
4.  **Visualize no Dashboard:** Navegue para a aba "Dashboard", selecione seu dashboard e veja seu novo card. Clique em "Atualizar" para obter os dados mais recentes a qualquer momento.
5.  **Adicione Contexto:** Se a IA não entender uma nomenclatura como `tbl_fat_05`, abra a modal "Editar Contexto" e adicione: "`tbl_fat_05` representa a tabela de faturamento de maio."

## ✨ Funcionalidades Principais

*   **Arquitetura Segura e Pronta para LGPD:** A IA **apenas gera a query SQL**. A execução é feita por um módulo separado e seguro, garantindo que os dados do seu banco de dados **nunca saem da sua infraestrutura**.
*   **Conectividade Multi-DB (BYOD):** Suporte nativo para **SQL Server, PostgreSQL, MySQL e SQLite**, permitindo que os usuários conectem suas próprias bases de dados.
*   **Dashboards Múltiplos e Personalizados:** Crie e gerencie múltiplos dashboards. Salve perguntas frequentes como "Métricas Chave" (KPIs) que aparecem como cards.
*   **Contexto de Negócio por Conexão:** Cada conexão de banco de dados possui seu próprio dicionário de dados e conjunto de dashboards, garantindo isolamento e relevância.
*   **IA Ciente do Dialeto SQL:** O sistema informa o dialeto do banco (ex: `sqlite`, `mssql`) para a IA, que gera queries sintaticamente corretas e compatíveis, evitando erros de função (como `TO_CHAR` vs. `printf`).
*   **Renderização de Cards Adaptativa:** O dashboard exibe os resultados de forma inteligente, mostrando métricas, tabelas interativas (`st.dataframe`) e gráficos.
*   **Guardrail de Segurança Robusto:** Um guardrail aprimorado valida cada query gerada, permitindo operações de leitura complexas (com `WITH`, CTEs) e bloqueando firmemente qualquer tentativa de modificação de dados (`DROP`, `DELETE`, etc.).
*   **Interface Unificada com Abas:** Uma experiência de usuário limpa com seções de "Chat" e "Dashboard" organizadas em abas (`st.tabs`).

## 🧠 Arquitetura de Segurança (LGPD)

O fluxo de dados foi projetado para máxima segurança e privacidade:

1.  **Usuário Pergunta:** A pergunta é enviada para o backend.
2.  **IA Recebe Metadados:** A IA recebe **apenas** o *schema* do banco de dados (nomes de tabelas/colunas), o contexto de negócio fornecido e a pergunta do usuário.
3.  **IA Gera SQL:** O LLM retorna uma string contendo a query SQL. **Nenhum dado do banco foi trafegado.**
4.  **Guardrail Valida:** O backend valida a query gerada para garantir que ela é segura.
5.  **Executor Local Executa:** O módulo `db_executor.py` se conecta diretamente ao banco de dados do usuário e executa a query segura.
6.  **Resultado para o Usuário:** Os dados retornados pelo banco são enviados diretamente para a interface do usuário, sem nunca passarem pela IA.

## 🛠️ Tecnologias Utilizadas

*   **Linguagem:** Python 3.10+
*   **Framework de LLM:** 🧠 LangChain (para orquestração de prompts e parsing)
*   **Modelo de Linguagem:** 🤖 OpenAI (GPT-4o, GPT-4 Turbo, etc.)
*   **Interface Web:** 📊 Streamlit
*   **Bancos de Dados Suportados:** 🗃️ SQL Server, PostgreSQL, MySQL, SQLite
*   **Drivers de Conexão:** SQLAlchemy, psycopg2, mysql-connector-python, pyodbc
*   **Armazenamento de Métricas:** JSON com Criptografia (para a chave da API)

## 📂 Estrutura do Projeto

O projeto segue uma arquitetura modular e escalável:

```
dataspeak-nlq/
├── app.py # Aplicação principal com Streamlit (UI e orquestração)
├── requirements.txt # Dependências do projeto
├── .env # Arquivo para configurações (desenvolvimento local)
│
├── pipeline/
│ ├── agent_pipeline.py # Apenas GERA a query SQL
│ └── db_executor.py # APENAS EXECUTA a query SQL
│
├── strategies/
│ └── llms/
│   └── openai_llm.py # Configuração e inicialização do LLM
│
├── data/
│ └── storage.json # Armazena dashboards e chave API criptografada
│
├── utils/
│ ├── connection.py # Gera IDs únicos para cada conexão de DB
│ ├── security.py # Módulo do Guardrail de segurança
│ └── storage.py # Funções para ler/escrever no storage.json
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
### 3. Gerar a Chave de Criptografia

O DataSpeak usa criptografia para armazenar de forma segura a chave da API da OpenAI. Você precisa gerar uma chave única para a sua instância da aplicação.

a. Crie um pequeno script Python chamado `generate_key.py` na raiz do seu projeto com o seguinte conteúdo:

```python
# generate_key.py
from cryptography.fernet import Fernet

key = Fernet.generate_key()
print("Sua chave de criptografia (copie para o .env):")
print(key.decode())
```

b. Execute o script a partir do seu terminal (com o ambiente virtual ativado):
```bash
pip install cryptography
python generate_key.py
```

c. O script irá gerar e imprimir uma chave única. Copie essa chave.

### 4. Configurar Variáveis de Ambiente
Para desenvolvimento local, crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
```ini
# .env
# Cole a chave gerada pelo script generate_key.py aqui
ENCRYPTION_KEY="sua-chave-de-criptografia-unica-aqui"

# Configurações do modelo da OpenAI
OPENAI_TEMPERATURE=0.1
```
A chave da API da OpenAI será solicitada diretamente na interface da aplicação.

## ▶️ Como Executar

Com o ambiente configurado, inicie a aplicação Streamlit:

```bash
streamlit run app.py
```

Seu navegador abrirá automaticamente no endereço `http://localhost:8501`.

### Para Deploy em uma máquina virtual LINUX
1. Siga estes passos: [Linux](assets/install-linux.md) 

### Para Deploy em uma máquina virtual WINDOWS
1. Siga estes passos: [Windows](assets/install-windows.md) 


## 🗺️ Roadmap e Próximas Melhorias

*   [ ] **Suporte a NoSQL:** Adicionar conectividade para bancos de dados como MongoDB.
*   [ ] **Cache de Resultados do Dashboard:** Implementar um cache mais robusto (ex: st.cache_data) para os resultados do dashboard, evitando recálculos desnecessários.
*   [ ] **Geração de Relatórios Agendados:** Permitir que o usuário agende a atualização de um dashboard e receba o resultado por e-mail.
*   [ ] **Autenticação de Usuários:** Adicionar um sistema de login para que diferentes usuários tenham seus próprios dashboards salvos.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT.