# rotas.py
import streamlit as st
import folium
from streamlit_folium import st_folium
import requests
import joblib
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÕES E CARREGAMENTO DO MODELO ---
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# URL do OSRM para obter rotas alternativas (geometria e tempo)
ROUTING_URL = "https://router.project-osrm.org/route/v1/driving/"
ARQUIVO_MODELO = 'modelo_risco_rodoviario.pkl'

# Carregar o modelo de risco uma única vez
try:
    MODELO_RISCO = joblib.load(ARQUIVO_MODELO)
    st.sidebar.success("Modelo de Risco de Acidente carregado com sucesso.")
except FileNotFoundError:
    MODELO_RISCO = None
    st.sidebar.error(f"Modelo '{ARQUIVO_MODELO}' não encontrado. Execute preditor_risco.py primeiro.")

# --- FUNÇÕES AUXILIARES DE ML ---

def _preparar_dados_para_modelo(localizacao, condicao_metereologica):
    """Prepara o input de dados de viagem para o modelo ML."""
    
    # Mapeamento do dia da semana para o formato usado no treinamento do ML
    dia_semana_map = {0: 'segunda-feira', 1: 'terça-feira', 2: 'quarta-feira', 3: 'quinta-feira', 4: 'sexta-feira', 5: 'sábado', 6: 'domingo'}
    now = datetime.now()
    
    dados_viagem = {
        'hora_do_dia': now.hour,
        'mes': now.month,
        'dia_semana': dia_semana_map.get(now.weekday()), 
        'condicao_metereologica': condicao_metereologica, 
        'localizacao': localizacao # Ex: SP_SAO PAULO
    }
    
    return pd.DataFrame([dados_viagem])


def calcular_risco_segmento(uf, municipio, condicao_metereologica):
    """Calcula o risco de alta gravidade (probabilidade) para um local."""
    if MODELO_RISCO is None or not uf or not municipio:
        return 0.0
        
    localizacao = f"{uf}_{municipio}"
    dados_input = _preparar_dados_para_modelo(localizacao, condicao_metereologica)
    
    # Prever a probabilidade de alta risco (Classe 1)
    try:
        risco_prob = MODELO_RISCO.predict_proba(dados_input)[0][1]
        return risco_prob
    except Exception as e:
        # st.warning(f"Erro na predição ML para {localizacao}: {e}")
        return 0.0 # Retorna 0 em caso de erro de predição

# --- FUNÇÕES DE GEOLOCALIZAÇÃO E ROTA ---

def geocodificar_cidade(cidade):
    """Converte o nome de uma cidade em coordenadas (lat, lon) e extrai UF/Município."""
    headers = {
        "User-Agent": "CalculadoraDeRotasStreamlit/1.0"
    }
    params = {
        "q": cidade,
        "format": "json",
        "limit": 1,
        "addressdetails": 1, # Capturar detalhes de endereço
    }
    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            
            address = data[0].get('address', {})
            # Tenta encontrar o município com diferentes chaves
            municipio = address.get('city') or address.get('town') or address.get('village') or address.get('county')
            uf = address.get('state') # Estado/UF
            
            return lat, lon, municipio.upper() if municipio else None, uf.upper() if uf else None
        else:
            return None, None, None, None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao geocodificar '{cidade}': {e}")
        return None, None, None, None


def calcular_rota(latA, lonA, latB, lonB, municipioA, ufA, municipioB, ufB, condicao_metereologica, peso_risco=50):
    """
    Calcula rotas alternativas usando OSRM e ajusta o custo usando o Modelo de Risco.
    """
    # 1. Obter rotas alternativas do OSRM
    osrm_url = f"{ROUTING_URL}{lonA},{latA};{lonB},{latB}"
    params = {"alternatives": "true", "steps": "false", "geometries": "geojson"}
    
    try:
        response = requests.get(osrm_url, params=params)
        response.raise_for_status()
        dados = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao calcular a rota: {e}")
        return None

    rotas_alternativas = []
    
    # 2. Processamento e Ajuste de Custo com ML
    for rota in dados.get("routes", []):
        
        tempo_total = rota["duration"] / 60.0 # Tempo em minutos
        distancia_total = rota["distance"] / 1000.0 # Distância em km
        
        # Simulação: Risco calculado nos pontos de origem e destino (Proxy para o risco médio da rota)
        risco_origem = calcular_risco_segmento(ufA, municipioA, condicao_metereologica)
        risco_destino = calcular_risco_segmento(ufB, municipioB, condicao_metereologica)
        
        risco_medio_rota = (risco_origem + risco_destino) / 2.0
        
        # Custo Ajustado: Tempo (minutos) + (Risco_médio * Ponderação do Risco)
        # O peso_risco permite que o usuário defina o quanto ele valoriza a segurança.
        custo_ajustado = tempo_total + (risco_medio_rota * peso_risco)
        
        # O valor do risco é exibido para o usuário
        rotas_alternativas.append({
            "coordenadas": rota["geometry"]["coordinates"], # Formato [lon, lat]
            "tempo_min": tempo_total,
            "distancia_km": distancia_total,
            "risco_medio": risco_medio_rota,
            "custo_ajustado": custo_ajustado,
            "resumo": rota.get("summary", f"Rota {len(rotas_alternativas) + 1}")
        })

    # Ordenar as rotas pelo NOVO CUSTO AJUSTADO (A Rota "Melhor")
    rotas_alternativas.sort(key=lambda x: x["custo_ajustado"])
    
    return rotas_alternativas

# --- LAYOUT STREAMLIT ---

st.title("Calculadora de Rotas com Otimização de Risco 🚧")
st.markdown("Otimiza a rota buscando o menor custo, combinando o tempo de viagem com o risco de acidentes previsto pelo ML (dados DATATRAN).")

# Inicialização do session_state
if "ufA" not in st.session_state:
    st.session_state["ufA"] = ""
    st.session_state["municipioA"] = ""
    st.session_state["ufB"] = ""
    st.session_state["municipioB"] = ""
    st.session_state["rotas"] = []
    st.session_state["latA"] = None
    st.session_state["lonA"] = None
    st.session_state["latB"] = None
    st.session_state["lonB"] = None

# Formulário de Input
with st.form("form_rota"):
    st.header("1. Origem e Destino")
    col1, col2 = st.columns(2)
    
    origem_cidade = col1.text_input("Cidade de Origem (Ex: Campinas, SP)", key="origem_input")
    destino_cidade = col2.text_input("Cidade de Destino (Ex: Rio de Janeiro, RJ)", key="destino_input")

    st.header("2. Condições e Prioridade")
    col3, col4 = st.columns(2)
    condicao_metereologica = col3.selectbox(
        "Condição Meteorológica Atual (para o ML)",
        options=['Sol', 'Chuva', 'Nublado', 'Nevoeiro', 'Ignorada'],
        key="condicao_metereologica"
    )
    # O campo 'Peso do Risco' foi removido conforme solicitado.
    # Definindo um peso fixo para o risco (ex: 50) para manter a otimização de risco.
    peso_risco = 50 # Valor fixo para ponderação do risco na otimização
    
    submitted = st.form_submit_button("Calcular Rota Otimizada")


# Lógica de Geocodificação e Cálculo
if submitted:
    
    latA, lonA, municipioA, ufA = geocodificar_cidade(origem_cidade)
    latB, lonB, municipioB, ufB = geocodificar_cidade(destino_cidade)

    if latA and latB and ufA and ufB:
        # Atualiza o estado da sessão com os dados geocodificados
        st.session_state["latA"], st.session_state["lonA"] = latA, lonA
        st.session_state["latB"], st.session_state["lonB"] = latB, lonB
        st.session_state["municipioA"], st.session_state["ufA"] = municipioA, ufA
        st.session_state["municipioB"], st.session_state["ufB"] = municipioB, ufB
        
        st.success(f"Origem: {origem_cidade} ({ufA}) | Destino: {destino_cidade} ({ufB})")

        # 2. Cálculo da Rota Otimizada
        st.session_state["rotas"] = calcular_rota(
            latA, lonA, latB, lonB, 
            municipioA, ufA, municipioB, ufB,
            condicao_metereologica
        )
        
    else:
        st.error("Não foi possível geocodificar as cidades ou obter o UF/Município (essencial para o ML). Tente um formato mais específico.")


# Exibir mapa
if st.session_state["rotas"]:
    
    st.markdown("### 3. Resultado da Otimização")

    centro = [
        (st.session_state["latA"] + st.session_state["latB"]) / 2,
        (st.session_state["lonA"] + st.session_state["lonB"]) / 2,
    ]
    m = folium.Map(location=centro, zoom_start=6)
    
    # Marcadores de Origem/Destino
    folium.Marker(
        [st.session_state["latA"], st.session_state["lonA"]],
        popup=f"Origem: {st.session_state['municipioA']} - {st.session_state['ufA']}", icon=folium.Icon(color="green")
    ).add_to(m)
    folium.Marker(
        [st.session_state["latB"], st.session_state["lonB"]],
        popup=f"Destino: {st.session_state['municipioB']} - {st.session_state['ufB']}", icon=folium.Icon(color="red")
    ).add_to(m)
    
    cores = ["blue", "purple", "orange", "gray"]
    
    for i, rota in enumerate(st.session_state["rotas"]):
        
        # Inverter coordenadas para o folium [lon, lat] -> [lat, lon]
        pontos_rota = [[p[1], p[0]] for p in rota["coordenadas"]]
        
        # Destaque para a Rota Otimizada (primeira da lista)
        is_best_route = i == 0
        
        st.markdown(
            f"**{'🥇 MELHOR ROTA' if is_best_route else f'Rota {i+1}'}** ({rota['resumo']}): "
            f"**{rota['distancia_km']:.0f} km** | "
            f"**{rota['tempo_min']:.0f} min** | "
            f"**Risco Previsto:** {rota['risco_medio']:.4f} | "
            f"**Custo Ajustado:** {rota['custo_ajustado']:.2f}",
            help=f"O Custo Ajustado é a métrica usada para classificar as rotas: Tempo + ({rota['risco_medio']:.4f} * {peso_risco}). O peso do risco é fixo em {peso_risco}."
        )
        
        folium.PolyLine(
            pontos_rota,
            color=cores[i % len(cores)],
            weight=5 if is_best_route else 3,
            opacity=0.9 if is_best_route else 0.5
        ).add_to(m)
        
    st_folium(m, width=700, height=500)