# preditor_ofc/pages/interface.py
import streamlit as st
import pandas as pd
import pickle
import json
from datetime import datetime
import plotly.express as px
from core.auth import check_session_expiry, logout_user
from core.chatbot import generate_and_execute_code_gemini, load_data as load_data_for_chatbot
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

    df_chatbot = load_data_for_chatbot()
    if df_chatbot is None:
        st.error("Erro ao carregar o DataFrame para o Chatbot.")
        st.stop()
    
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
user_question = st.text_area(
    "Faça uma pergunta sobre os dados de acidentes:",
    "Quais são os principais fatores de risco para acidentes de trânsito?"
)
if st.button("🤖 Perguntar à LLM"):
    try:
        with st.spinner("Analisando dados e gerando resposta..."):
            # A nova função usa o Gemini para gerar e executar código Pandas no DataFrame pré-processado
            response = generate_and_execute_code_gemini(df_chatbot, user_question)
        
        if response.startswith("Erro ao gerar ou executar o código:"):
            st.error(f"Erro na análise: {response}")
        else:
            st.success("Resposta da LLM:")
            st.write(response)

    except Exception as e:
        st.error(f"Erro ao conectar com Gemini. Certifique-se de que a variável de ambiente GEMINI_API_KEY está configurada. Detalhes: {e}")


