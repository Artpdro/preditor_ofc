import streamlit as st
import pandas as pd
import pickle
import json
from datetime import datetime

with open("preditor.pkl", "rb") as f:
    model = pickle.load(f)

with open("label_encoder_mappings.json", "r") as f:
    label_encoder_mappings = json.load(f)

# Função para codificar as entradas do usuário
def encode_input(feature, value):
    if feature in label_encoder_mappings:
        try:
            return label_encoder_mappings[feature].index(value)
        except ValueError:
            st.warning(f"Valor '{value}' para '{feature}' não encontrado nos dados de treinamento. Usando 0 como padrão.")
            return 0 
    return value


st.title('previsão de quantidade de acidentes')

st.write("insira os dados para prever a quantidade de acidentes.")

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

