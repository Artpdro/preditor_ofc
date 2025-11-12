import pandas as pd
import ollama

# --------------------------
# 1️⃣ Carrega o CSV
# --------------------------
def carregar_dados(caminho='datatran_consolidado.csv'):
    try:
        df = pd.read_csv(caminho, encoding='latin1', sep=None, engine='python')
        print(f"✅ Dados carregados: {len(df)} registros")
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar CSV: {e}")
        return pd.DataFrame()

# --------------------------
# 2️⃣ Função de análise real
# --------------------------
def responder_com_dados(df, pergunta):
    pergunta = pergunta.lower()

    # Tipos de acidente
    if "tipo" in pergunta or "acidente" in pergunta:
        if "tipo_acidente" not in df.columns:
            return "❌ Coluna 'tipo_acidente' não encontrada no CSV."
        contagem = df["tipo_acidente"].value_counts().head(10)
        resumo = "\n".join([f"{i+1}. {a} — {b} ocorrências" for i, (a,b) in enumerate(contagem.items())])
        prompt = f"""
Os dados abaixo mostram os tipos de acidente mais comuns no Brasil, conforme o CSV analisado:

{resumo}

Explique o que esses dados podem indicar sobre o comportamento no trânsito e as possíveis causas desses tipos de acidente.
"""
        return analisar_com_llama(prompt)

    # Estados
    elif "estado" in pergunta or "uf" in pergunta:
        contagem = df["uf"].value_counts().head(10)
        resumo = "\n".join([f"{i+1}. {a} — {b} ocorrências" for i, (a,b) in enumerate(contagem.items())])
        prompt = f"""
Os dados abaixo mostram os estados com mais acidentes:

{resumo}

Com base nesses dados, quais fatores podem contribuir para essa distribuição geográfica?
"""
        return analisar_com_llama(prompt)

    # Municípios
    elif "município" in pergunta or "municipio" in pergunta:
        contagem = df["municipio"].value_counts().head(10)
        resumo = "\n".join([f"{i+1}. {a} — {b} ocorrências" for i, (a,b) in enumerate(contagem.items())])
        prompt = f"""
Os dados abaixo mostram os municípios com mais acidentes:

{resumo}

Analise o que pode explicar a concentração de acidentes nesses locais.
"""
        return analisar_com_llama(prompt)

    # Clima
    elif "condição" in pergunta or "clima" in pergunta or "tempo" in pergunta:
        contagem = df["condicao_metereologica"].value_counts().head(10)
        resumo = "\n".join([f"{i+1}. {a} — {b} ocorrências" for i, (a,b) in enumerate(contagem.items())])
        prompt = f"""
Os dados abaixo mostram as condições meteorológicas mais registradas em acidentes:

{resumo}

Com base nesses dados, existe alguma relação entre o clima e a frequência de acidentes?
"""
        return analisar_com_llama(prompt)

    else:
        return "❌ Pergunta não reconhecida. Tente algo como:\n- 'Quais são os tipos de acidente mais comuns?'\n- 'Quais estados têm mais acidentes?'\n- 'Qual condição climática aparece mais?'"

# --------------------------
# 3️⃣ Chama o Llama apenas para interpretar o resumo
# --------------------------
def analisar_com_llama(prompt):
    try:
        resposta = ollama.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": "Você é um analista de dados de trânsito no Brasil. Responda sempre com base apenas nos dados fornecidos."},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.0}
        )
        return resposta["message"]["content"]
    except Exception as e:
        return f"❌ Erro ao conectar com o modelo: {e}"

# --------------------------
# 4️⃣ Modo interativo
# --------------------------
def modo_interativo(df):
    print("\n🚦 Faça perguntas sobre os dados (ex: 'Quais são os tipos de acidente mais comuns?')\nDigite 'sair' para encerrar.\n")
    while True:
        pergunta = input("❓ Pergunta: ").strip()
        if pergunta.lower() in ["sair", "exit", "quit"]:
            break
        resposta = responder_com_dados(df, pergunta)
        print("\n💬 Resposta:\n")
        print(resposta)
        print("\n" + "="*80 + "\n")

# --------------------------
# 5️⃣ Execução principal
# --------------------------
if __name__ == "__main__":
    df = carregar_dados("/mnt/data/datatran_consolidado.csv")
    if not df.empty:
        modo_interativo(df)
