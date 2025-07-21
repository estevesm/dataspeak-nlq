# pipeline/tools/viz_tool.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from langchain.tools import tool
from pydantic.v1 import BaseModel, Field # Usamos pydantic para definir o schema de entrada
import streamlit as st

# --- INÍCIO DA MODIFICAÇÃO ---

# 1. Definimos um schema de entrada claro usando Pydantic
class PlotInput(BaseModel):
    data: list = Field(description="Lista de listas ou tuplas representando as linhas dos dados.")
    columns: list[str] = Field(description="Lista de strings com os nomes das colunas.")
    chart_type: str = Field(description="Tipo de gráfico a ser gerado. Valores válidos: 'bar', 'pie'.")
    title: str = Field(description="Um título descritivo para o gráfico.")

# 2. Usamos o decorador @tool com o schema de entrada (args_schema)
@tool(args_schema=PlotInput)
def create_chart_from_data(data: list, columns: list, chart_type: str, title: str) -> str:
    """
    Use esta ferramenta SEMPRE que o usuário pedir para gerar um GRÁFICO, PLOT, VISUALIZAÇÃO ou DIAGRAMA.
    Não use para exibir dados em tabelas. Use-a para criar um gráfico de barras ('bar') ou de pizza ('pie').
    Você DEVE ter os dados de uma query SQL ANTES de chamar esta ferramenta.
    """
    try:
        if not data:
            return "Erro: Não há dados para plotar."

        df = pd.DataFrame(data, columns=columns)
        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type.lower() == 'bar':
            if len(df.columns) != 2:
                return "Erro: Gráficos de barra requerem exatamente 2 colunas (categoria e valor)."
            sns.barplot(x=df.columns[0], y=df.columns[1], data=df, ax=ax, palette="viridis")
            plt.xticks(rotation=45, ha='right')
        
        elif chart_type.lower() == 'pie':
            if len(df.columns) != 2:
                return "Erro: Gráficos de pizza requerem exatamente 2 colunas (rótulo e valor)."
            ax.pie(df.iloc[:, 1], labels=df.iloc[:, 0], autopct='%1.1f%%', startangle=90, colors=sns.color_palette("viridis", len(df)))
            ax.axis('equal')

        else:
            return f"Erro: Tipo de gráfico '{chart_type}' não suportado. Use 'bar' ou 'pie'."

        ax.set_title(title, fontsize=16)
        plt.tight_layout()
        
        # O truque para exibir no Streamlit
        st.pyplot(fig)
        
        return f"Sucesso! O gráfico '{title}' foi gerado e exibido na interface."
    
    except Exception as e:
        # Limpa qualquer figura que possa ter ficado em memória
        plt.close('all')
        return f"Ocorreu um erro ao tentar gerar o gráfico: {e}"