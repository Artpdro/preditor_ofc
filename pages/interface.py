import streamlit as st
import pandas as pd
import pickle
import json
from datetime import datetime
import plotly.express as px

# Carregar o modelo
with open("preditor.pkl", "rb") as f:
    model = pickle.load(f)

# Carregar os mapeamentos do Label Encoder
with open("label_encoder_mappings.json", "r") as f:
    label_encoder_mappings = json.load(f)

# Carregar o mapa de UF para Municípios
with open("uf_municipio_map.json", "r") as f:
    uf_municipio_map = json.load(f)

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

# Seleção de UF
uf_options = sorted(uf_municipio_map.keys())
uf = st.selectbox("UF", uf_options)

# Seleção de Município (dependente da UF)
if uf:
    municipio_options = uf_municipio_map.get(uf, [])
    municipio = st.selectbox("Município", municipio_options)
else:
    municipio = st.selectbox("Município", ["Selecione uma UF primeiro"])

# Outros campos
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
    if uf and municipio and municipio != "Selecione uma UF primeiro":
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
    else:
        st.error("Por favor, selecione a UF e o Município.")

st.markdown("---")
