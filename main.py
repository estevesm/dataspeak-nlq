from pipeline.agent_pipeline import run_agent
import pandas as pd

def main():

    print("🤖 SQL Agent com Linguagem Natural")
    print("Conectado ao banco 'database.db'. Faça sua pergunta ou digite 'sair'.")
    print("-" * 30)

    while True:
        question = input("Você: ")
        if question.lower() in ['sair', 'exit', 'quit']:
            print("Até logo! 👋")
            break

        if not question.strip():
            continue

        print("\n🤔 Pensando...")
        answer = run_agent(question)

        try:
            # O agente LangChain pode retornar uma string que é uma representação de lista de tuplas
            data = eval(answer)
            if isinstance(data, list) and data:
                df = pd.DataFrame(data)
                # Tenta pegar os nomes das colunas da 'observação' do agente (requereria mais parse)
                # Por simplicidade, vamos deixar sem cabeçalho ou usar genéricos
                print("📊 Resultado:\n")
                print(df.to_string(index=False))
            else:
                print(f"\n✅ Resposta: {answer}")

        except (SyntaxError, NameError, TypeError):
            # Se não for uma lista de tuplas/dicionários, apenas imprime a resposta textual
            print(f"\n✅ Resposta: {answer}")

        print("-" * 30)


if __name__ == "__main__":
    main()