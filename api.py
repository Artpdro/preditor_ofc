import pandas as pd
import pickle
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional

# Inicialização do FastAPI
app = FastAPI(
    title="API de Predição de Acidentes",
    description="API REST para prever a quantidade de acidentes com base em dados de entrada."
)

# Middleware CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    # Adicione outros domínios se necessário
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # permite requisições dessas origens
    allow_credentials=True,
    allow_methods=["*"],         # permite GET, POST, PUT, DELETE, etc
    allow_headers=["*"],         # permite headers personalizados
)

# Caminhos dos arquivos
MODEL_PATH = "preditor.pkl"
MAPPINGS_PATH = "label_encoder_mappings.json"

# Carregar o modelo e os mappings
try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    with open(MAPPINGS_PATH, "r") as f:
        label_encoder_mappings = json.load(f)
except FileNotFoundError as e:
    print(f"Erro ao carregar arquivo: {e}")
    model = None
    label_encoder_mappings = {}
except Exception as e:
    print(f"Erro inesperado ao carregar arquivos: {e}")
    model = None
    label_encoder_mappings = {}

# Função para codificar as entradas do usuário
def encode_input(feature: str, value: str) -> int:
    """
    Codifica um valor categórico usando os mappings carregados.
    Retorna o índice do valor ou 0 se não encontrado.
    """
    if feature in label_encoder_mappings:
        try:
            return label_encoder_mappings[feature].index(value)
        except ValueError:
            return 0 
    return 0

# Definição do esquema de dados de entrada
class PredictionInput(BaseModel):
    uf: str = Field(..., description="Unidade Federativa (UF). Ex: 'MG'")
    municipio: str = Field(..., description="Município. Ex: 'BELO HORIZONTE'")
    tipo_acidente: str = Field(..., description="Tipo de Acidente. Ex: 'Colisão'")
    condicao_metereologica: str = Field(..., description="Condição Meteorológica. Ex: 'Céu Claro'")
    hora_media: int = Field(..., ge=0, le=23, description="Hora Média (0-23). Ex: 12")
    data_acidente: str = Field(..., description="Data do Acidente no formato YYYY-MM-DD. Ex: '2023-10-27'")

# Endpoint de saúde
@app.get("/health", tags=["Monitoramento"])
async def health_check():
    if model is None:
        return {"status": "error", "message": "Modelo não carregado"}
    return {"status": "ok", "message": "API e modelo carregados com sucesso"}

# Endpoint de predição
@app.post("/predict", tags=["Predição"])
async def predict_accidents(data: PredictionInput):
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo de predição não está disponível.")

    try:
        # Processar a data
        try:
            data_input = datetime.strptime(data.data_acidente, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD.")

        dia_semana_num = data_input.weekday()
        mes = data_input.month
        ano = data_input.year
        dia_do_ano = data_input.timetuple().tm_yday
        dia_do_mes = data_input.day

        # Codificar inputs categóricos
        uf_encoded = encode_input("uf", data.uf)
        municipio_encoded = encode_input("municipio", data.municipio)
        tipo_acidente_encoded = encode_input("tipo_acidente", data.tipo_acidente)
        condicao_metereologica_encoded = encode_input("condicao_metereologica", data.condicao_metereologica)

        # Criar DataFrame para o modelo
        input_df = pd.DataFrame([[ 
            uf_encoded, municipio_encoded, tipo_acidente_encoded, 
            condicao_metereologica_encoded, data.hora_media, dia_semana_num, 
            mes, ano, dia_do_ano, dia_do_mes
        ]],
        columns=[
            "uf", "municipio", "tipo_acidente", "condicao_metereologica", 
            "hora_media", "dia_semana_num", "mes", "ano", "dia_do_ano", "dia_do_mes"
        ])

        # Fazer a predição
        prediction = model.predict(input_df)[0]

        return {
            "status": "success",
            "prediction": round(prediction),
            "raw_prediction": float(prediction),
            "input_data": data.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno ao processar a predição: {e}")

# Endpoint para listar os valores possíveis para as features categóricas
@app.get("/mappings", tags=["Informação"])
async def get_mappings():
    return label_encoder_mappings

# Para rodar localmente
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
