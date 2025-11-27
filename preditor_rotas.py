# preditor_risco.py
import pandas as pd
import numpy as np
import json
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import joblib

# Nome do arquivo de dados e do arquivo de modelo
ARQUIVO_DADOS = 'datatran_consolidado.json'
ARQUIVO_MODELO = 'modelo_risco_rodoviario.pkl'

def preparar_dados(caminho_arquivo):
    """Carrega, limpa e prepara os dados do DATATRAN para o treinamento do ML."""
    print(f"1. Carregando dados de {caminho_arquivo}...")
    
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
    except FileNotFoundError:
        print(f"ERRO: Arquivo {caminho_arquivo} não encontrado. Por favor, verifique o nome ou caminho.")
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro

    # 1. Limpeza e Conversão de Tipos
    # Substituir vírgula por ponto em coordenadas e converter para float
    for col in ['latitude', 'longitude']:
        df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Combinar data e hora para criar um objeto datetime
    df['datetime'] = pd.to_datetime(
        df['data_inversa'] + ' ' + df['horario'], 
        format='%d/%m/%Y %H:%M:%S', 
        errors='coerce'
    )
    df.dropna(subset=['datetime', 'latitude', 'longitude'], inplace=True)

    # 2. Engenharia de Features
    df['hora_do_dia'] = df['datetime'].dt.hour
    df['mes'] = df['datetime'].dt.month
    
    # Criar a Variável Target (Y): Risco de Alta Gravidade
    # Tipos de acidentes que representam maior risco (proxy)
    tipos_alto_risco = ['Capotamento', 'Colisao transversal', 'Saída de pista', 'Atropelamento de pessoa']
    df['alto_risco'] = df['tipo_acidente'].apply(
        lambda x: 1 if pd.notna(x) and x in tipos_alto_risco else 0
    )
    
    # Criar Feature de Localização (UF_MUNICÍPIO)
    df['localizacao'] = df['uf'].astype(str) + '_' + df['municipio'].astype(str)

    # Filtrar colunas necessárias para o treinamento
    colunas_ml = ['hora_do_dia', 'mes', 'dia_semana', 'condicao_metereologica', 'localizacao', 'alto_risco']
    df_ml = df[colunas_ml].copy()
    
    # Remover dados com valores nulos nas features de interesse
    df_ml.dropna(inplace=True)
    
    # Amostragem para reduzir o consumo de memória no ambiente de sandbox
    # Mantendo a proporção da variável target 'alto_risco'
    df_ml_sample = df_ml.groupby('alto_risco', group_keys=False).apply(lambda x: x.sample(frac=0.1, random_state=42))
    
    print(f"Dados prontos. Total de {len(df_ml)} registros válidos. Usando amostra de {len(df_ml_sample)} para treinamento.")
    return df_ml_sample

def treinar_e_salvar_modelo(df_ml):
    """Treina e salva o modelo de Regressão Logística."""
    
    # Separação de Features (X) e Target (y)
    features = ['hora_do_dia', 'mes', 'dia_semana', 'condicao_metereologica', 'localizacao']
    target = 'alto_risco'
    
    X = df_ml[features]
    y = df_ml[target]

    # Separação em treino e teste
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    
    print("2. Iniciando a criação do Pipeline de Pré-processamento e ML...")

    # 2.1. Criação do Pré-processador
    categorical_features = ['dia_semana', 'condicao_metereologica', 'localizacao']
    numerical_features = ['hora_do_dia', 'mes']

    preprocessor = ColumnTransformer(
        transformers=[
            # Aplica One-Hot Encoding para variáveis categóricas
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features),
            # Aplica Padronização (Scaling) para variáveis numéricas
            ('num', StandardScaler(), numerical_features)
        ],
        remainder='drop'
    )
    
    # 2.2. Criação do Pipeline de ML
    # LogisticRegression com 'class_weight='balanced'' para lidar com a raridade dos acidentes de alto risco
    modelo_risco = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(solver='liblinear', random_state=42, class_weight='balanced', max_iter=1000)) 
    ])
    
    print("3. Treinamento do modelo (Regressão Logística)...")
    modelo_risco.fit(X_train, y_train)
    print("Treinamento concluído.")
    
    # 4. Avaliação e Salvamento
    y_pred = modelo_risco.predict(X_test)
    print("\nRelatório de Classificação (Teste):")
    print(classification_report(y_test, y_pred))
    
    joblib.dump(modelo_risco, ARQUIVO_MODELO)
    print(f"\n4. Modelo de Risco salvo com sucesso como '{ARQUIVO_MODELO}'")
    
    return modelo_risco

if __name__ == '__main__':
    df_dados = preparar_dados(ARQUIVO_DADOS)
    if not df_dados.empty:
        treinar_e_salvar_modelo(df_dados)