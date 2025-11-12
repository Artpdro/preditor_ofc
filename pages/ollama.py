import pandas as pd
import ollama
import json

# --------------------------
# 1️⃣ Carrega JSON corretamente
# --------------------------
def carregar_dados_json(caminho='datatran_consolidado.json'):
    try:
        with open(caminho, 'r', encoding='latin1') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        print(f"✅ Dados carregados do JSON: {len(df)} registros")
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar JSON: {e}")
        return pd.DataFrame()

# --------------------------
# 2️⃣ Gera resumo conforme a pergunta
# --------------------------
def gerar_resumo_por_pergunta(pergunta, df):
    pergunta_lower = pergunta.lower()
    resumo_texto = ""
    titulo = ""

    # Estados
    if "estado" in pergunta_lower or "uf" in pergunta_lower:
        if "uf" in df.columns:
            dados = df["uf"].value_counts().head(10)
            titulo = "Estados com mais acidentes"
            resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])

    # Horários
    elif "hora" in pergunta_lower or "horário" in pergunta_lower or "turno" in pergunta_lower:
        if "horario" in df.columns:
            df["hora"] = pd.to_datetime(df["horario"], errors="coerce").dt.hour
            dados = df["hora"].value_counts().sort_index()
            titulo = "Distribuição de acidentes por hora do dia"
            resumo_texto = "\n".join([f"- {int(a)}h: {b}" for a, b in dados.items()])

    # Dia da semana
    elif "dia" in pergunta_lower and "semana" in pergunta_lower:
        if "dia_semana" in df.columns:
            dados = df["dia_semana"].value_counts()
            titulo = "Distribuição de acidentes por dia da semana"
            resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])

    # Clima
    elif "clima" in pergunta_lower or "condi" in pergunta_lower or "meteo" in pergunta_lower or "tempo" in pergunta_lower:
        if "condicao_metereologica" in df.columns:
            dados = df["condicao_metereologica"].value_counts().head(10)
            titulo = "Condições meteorológicas mais registradas"
            resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])

    # Tipos de acidente
    elif "tipo" in pergunta_lower:
        if "tipo_acidente" in df.columns:
            dados = df["tipo_acidente"].value_counts().head(10)
            titulo = "Tipos de acidente mais comuns"
            resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])

    # Fallback
    if not resumo_texto:
        resumo_texto = (
            "Não encontrei dados diretamente relacionados à pergunta. "
            "As colunas disponíveis são: "
            + ", ".join(df.columns)
        )
        titulo = "Resumo geral"

    return titulo, resumo_texto

# --------------------------
# 3️⃣ Chama o modelo
# --------------------------
def analisar_com_llama(titulo, resumo_texto, pergunta):
    prompt = f"""
Você é um analista de segurança viária. Baseie-se apenas nos dados a seguir:

{titulo}
{resumo_texto}

Pergunta do usuário: {pergunta}

Explique o que esses dados mostram, destacando padrões, horários críticos e possíveis causas.
"""
    try:
        response = ollama.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": "Você é um analista de trânsito brasileiro, e deve responder com base nos dados fornecidos."},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.0}
        )
        return response["message"]["content"]
    except Exception as e:
        return f"❌ Erro ao conectar com Ollama: {e}"

# --------------------------
# 4️⃣ Modo interativo
# --------------------------
def modo_interativo(df):
    print("\n🚦 Faça perguntas sobre os dados (ex: 'Quais são os tipos de acidente mais comuns?')\nDigite 'sair' para encerrar.\n")
    while True:
        pergunta = input("❓ Pergunta: ").strip()
        if pergunta.lower() in ["sair", "exit", "quit"]:
            print("👋 Encerrando.")
            break

        titulo, resumo_texto = gerar_resumo_por_pergunta(pergunta, df)
        print("\n📊 Resumo dos dados encontrados:\n")
        print(resumo_texto)
        print("\n🤖 Resposta da LLM:\n")
        resposta = analisar_com_llama(titulo, resumo_texto, pergunta)
        print(resposta)
        print("\n" + "="*80 + "\n")

# --------------------------
# 5️⃣ Execução principal
# --------------------------
if __name__ == "__main__":
    df = carregar_dados_json("datatran_consolidado.json")
    if not df.empty:
        modo_interativo(df)
