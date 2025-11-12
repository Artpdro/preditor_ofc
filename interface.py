# preditor_ofc/pages/interface.py
import streamlit as st
import pandas as pd
import pickle
import json
from datetime import datetime
import plotly.express as px
from core.auth import check_session_expiry, logout_user
import ollama
from pathlib import Path # Adicionado para manipulação de caminhos

# --- Autenticação e Configuração Inicial ---
if not st.session_state.get('auth', False) or check_session_expiry():
    st.switch_page("login.py")

st.sidebar.title("Navegação")
if st.sidebar.button("Sair"):
    logout_user()
    st.switch_page("login.py")

try:
    with open("preditor.pkl", "rb") as f:
        model = pickle.load(f)
    
    with open("label_encoder_mappings.json", "r") as f:
        label_encoder_mappings = json.load(f)
        
    with open("datatran_consolidado.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    
except FileNotFoundError:
    st.error("Arquivos de modelo, mapeamento ou dados não encontrados. Certifique-se de que 'preditor.pkl', 'label_encoder_mappings.json' e 'datatran_consolidado.json' estão na pasta raiz.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao carregar recursos: {e}")
    st.stop()

# Função para codificar as entradas do usuário
def encode_input(feature, value):
    if feature in label_encoder_mappings:
        try:
            return label_encoder_mappings[feature].index(value)
        except ValueError:
            st.warning(f"Valor '{value}' para '{feature}' não encontrado nos dados de treinamento. Usando 0 como padrão.")
            return 0 
    return value


st.title('Previsão de quantidade de acidentes')

st.write("Insira os dados para prever a quantidade de acidentes.")
st.markdown("---")

# --- Interface Antiga de Predição de Acidentes ---
uf = st.selectbox("UF", label_encoder_mappings["uf"])
municipio = st.selectbox("Município", label_encoder_mappings["municipio"])
tipo_acidente = st.selectbox("Tipo de Acidente", label_encoder_mappings["tipo_acidente"])
condicao_metereologica = st.selectbox("Condição Meteorológica", label_encoder_mappings["condicao_metereologica"])
hora_media = st.slider("Hora Média (0-23)", 0, 23, 12)
data_input = st.date_input("Data do Acidente", datetime.now())

dia_semana_num = data_input.weekday()
mes = data_input.month
ano = data_input.year
dia_do_ano = data_input.timetuple().tm_yday
dia_do_mes = data_input.day

# Botão de previsão
if st.button("Fazer Previsão"):
    try:
        uf_encoded = encode_input("uf", uf)
        municipio_encoded = encode_input("municipio", municipio)
        tipo_acidente_encoded = encode_input("tipo_acidente", tipo_acidente)
        condicao_metereologica_encoded = encode_input("condicao_metereologica", condicao_metereologica)

        # Criar DataFrame com os inputs
        input_df = pd.DataFrame([[
            uf_encoded, municipio_encoded, tipo_acidente_encoded, 
            condicao_metereologica_encoded, hora_media, dia_semana_num, 
            mes, ano, dia_do_ano, dia_do_mes
        ]],
        columns=[
            "uf", "municipio", "tipo_acidente", "condicao_metereologica", 
            "hora_media", "dia_semana_num", "mes", "ano", "dia_do_ano", "dia_do_mes"
        ])

        prediction = model.predict(input_df)[0]
        st.success(f"A quantidade prevista de acidentes é: {prediction:.0f}")
    except Exception as e:
        st.error(f"Ocorreu um erro ao fazer a previsão: {e}")
        
st.markdown("---")

# --- Novo Link para a Interface de Rota Segura ---
st.subheader("Funcionalidade Adicional")
st.info("Para calcular a rota mais segura baseada em ML, acesse:")
if st.button("Acessar Calculadora de Rota Segura"):
    st.switch_page("pages/safe_route_interface.py")
    
st.markdown("---")
st.header("🧠 Pergunte ao chat")
st.info("Para usar integração com Ollama, instale e inicie o serviço, etc.")
user_question = st.text_area(
    "Faça uma pergunta sobre os dados de acidentes:",
    "Quais são os principais fatores de risco para acidentes de trânsito?"
)
if st.button("🤖 Perguntar à LLM"):
    try:
        pergunta_lower = user_question.lower()
        resumo_texto = ""
        titulo = ""

        # 🔍 Detecta o tema da pergunta
        if "estado" in pergunta_lower or "uf" in pergunta_lower:
            if "uf" in df.columns:
                dados = df["uf"].value_counts().head(10)
                titulo = "Estados com mais acidentes"
                resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])

        elif "hora" in pergunta_lower or "horário" in pergunta_lower or "turno" in pergunta_lower:
            if "horario" in df.columns:
                df["hora"] = pd.to_datetime(df["horario"], errors="coerce").dt.hour
                dados = df["hora"].value_counts().sort_index()
                titulo = "Distribuição de acidentes por hora do dia"
                resumo_texto = "\n".join([f"- {int(a)}h: {b}" for a, b in dados.items()])

        elif "dia" in pergunta_lower and "semana" in pergunta_lower:
            if "dia_semana" in df.columns:
                dados = df["dia_semana"].value_counts()
                titulo = "Distribuição de acidentes por dia da semana"
                resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])

        elif "clima" in pergunta_lower or "condi" in pergunta_lower or "meteo" in pergunta_lower:
            if "condicao_metereologica" in df.columns:
                dados = df["condicao_metereologica"].value_counts().head(10)
                titulo = "Condições meteorológicas mais registradas"
                resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])

        elif "tipo" in pergunta_lower:
            if "tipo_acidente" in df.columns:
                dados = df["tipo_acidente"].value_counts().head(10)
                titulo = "Tipos de acidente mais comuns"
                resumo_texto = "\n".join([f"- {a}: {b}" for a, b in dados.items()])


        # 🔹 Fallback
        if not resumo_texto:
            resumo_texto = (
                "Não encontrei dados diretamente relacionados à pergunta. "
                "As colunas disponíveis são: "
                + ", ".join(df.columns)
            )

        # 🔸 Monta prompt com resumo real
        prompt = f"""
Você é um analista de trânsito. Baseie-se exclusivamente nos dados abaixo.

{titulo}
{resumo_texto}

Pergunta do usuário: {user_question}

Explique o que esses dados mostram. Cite tendências, horários críticos ou fatores que podem explicar os padrões.
"""

        response = ollama.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": "Você é um analista de trânsito brasileiro."},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.0}
        )

        st.success("Resposta da LLM:")
        st.write(response["message"]["content"])

    except Exception as e:
        st.error(f"Erro ao conectar com Ollama: {e}")



