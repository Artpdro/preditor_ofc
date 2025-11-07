# preditor_ofc/pages/safe_route_interface.py
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from pathlib import Path
import sys
import json

# Adiciona o diretório raiz ao path para importar core.routing
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Importa as funções de geocodificação e roteamento
try:
    from core.routing import geocode_location, calculate_safe_route
except ImportError:
    st.error("Erro ao importar as funções de roteamento. Verifique se 'core/routing.py' existe e se as dependências (osmnx, networkx, geopy) estão instaladas.")
    st.stop()

# --- Carregar Mapeamento de Cidades ---
try:
    with open(PROJECT_ROOT / "uf_municipio_map.json", 'r', encoding='utf-8') as f:
        UF_MUNICIPIO_MAP = json.load(f)
except FileNotFoundError:
    st.error("Erro: Arquivo 'uf_municipio_map.json' não encontrado no diretório raiz.")
    UF_MUNICIPIO_MAP = {}
except Exception as e:
    st.error(f"Erro ao carregar 'uf_municipio_map.json': {e}")
    UF_MUNICIPIO_MAP = {}

# Lista de UFs e Municípios
UFS = sorted(UF_MUNICIPIO_MAP.keys())

# --- Interface Streamlit ---

st.set_page_config(
    page_title="Safeway - Rota Segura",
    layout="wide"
)

st.title('Calculadora de Rota Segura com ML e Dados Reais')
st.write("Calcule a rota otimizada (menor risco de acidentes) usando seu dataset real e lógica geoespacial.")
st.markdown("---")

# --- Inputs: Seleção de Cidade/Município ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Ponto de Partida")
    
    start_uf = st.selectbox("UF de Partida", UFS, key='start_uf')
    
    if start_uf and start_uf in UF_MUNICIPIO_MAP:
        municipios_start = sorted([m.title() for m in UF_MUNICIPIO_MAP[start_uf]])
        start_municipio = st.selectbox("Município de Partida", municipios_start, key='start_municipio')
        
        # O local de partida para geocodificação será o Município, UF
        start_location = f"{start_municipio}, {start_uf}" if start_municipio else ""
        st.caption(f"Local de Partida: {start_location}")
    else:
        start_location = ""
        st.warning("Selecione uma UF para carregar os municípios.")

with col2:
    st.subheader("Destino")
    
    end_uf = st.selectbox("UF de Destino", UFS, key='end_uf')
    
    if end_uf and end_uf in UF_MUNICIPIO_MAP:
        municipios_end = sorted([m.title() for m in UF_MUNICIPIO_MAP[end_uf]])
        end_municipio = st.selectbox("Município de Destino", municipios_end, key='end_municipio')
        
        # O local de destino para geocodificação será o Município, UF
        end_location = f"{end_municipio}, {end_uf}" if end_municipio else ""
        st.caption(f"Local de Destino: {end_location}")
    else:
        end_location = ""
        st.warning("Selecione uma UF para carregar os municípios.")

# --- Botão de Cálculo ---
if st.button("Calcular Rota Segura"):
    if not start_location or not end_location:
        st.error("Por favor, selecione o município de partida e o destino.")
    elif start_location == end_location:
        st.warning("O local de partida e o destino não podem ser os mesmos.")
    else:
        with st.spinner(f"1/3: Geocodificando locais: {start_location} e {end_location}..."):
            start_lat, start_lon = geocode_location(start_location)
            end_lat, end_lon = geocode_location(end_location)

        if not start_lat or not end_lat:
            st.error(f"Não foi possível encontrar as coordenadas para um ou ambos os locais: {start_location}, {end_location}. Tente outro município.")
        else:
            st.success(f"Locais geocodificados: Início ({start_lat:.4f}, {start_lon:.4f}), Fim ({end_lat:.4f}, {end_lon:.4f}).")
            
            with st.spinner("2/3: Calculando rota otimizada (ML + Geoespacial)..."):
                # Chama a função de cálculo de rota real
                route_coords, total_risk = calculate_safe_route(start_lat, start_lon, end_lat, end_lon)
            
            if route_coords:
                st.session_state['route_coords'] = route_coords
                st.session_state['total_risk'] = total_risk
                st.session_state['start_point'] = (start_lat, start_lon)
                st.session_state['end_point'] = (end_lat, end_lon)
                st.session_state['center_point'] = [
                    (start_lat + end_lat) / 2, 
                    (start_lon + end_lon) / 2
                ]
                st.success("3/3: Rota calculada com sucesso!")
            else:
                st.error("Não foi possível encontrar uma rota entre os pontos. Tente locais mais próximos ou verifique a conexão com o OSMnx.")

# --- Visualização do Resultado ---

if 'route_coords' in st.session_state and st.session_state['route_coords']:
    st.markdown("---")
    st.subheader("Resultado da Rota Otimizada")
    
    total_risk = st.session_state['total_risk']
    
    # Normaliza o risco total para uma escala de 0 a 100 para melhor visualização
    # O risco total é a soma dos riscos * comprimento. O valor máximo é desconhecido.
    # Vamos usar uma heurística simples para a cor, baseada no valor bruto.
    risk_color = "red" if total_risk > 0.05 else "orange" if total_risk > 0.01 else "green" 
    
    st.markdown(f"**Score de Risco Total da Rota (Ponderado):** <span style='color:{risk_color}; font-size: 1.2em;'>{total_risk:.4f}</span>", unsafe_allow_html=True)
    
    # 1. Cria o mapa Folium
    m = folium.Map(location=st.session_state['center_point'], zoom_start=9)
    
    # 2. Adiciona a rota (Polyline)
    folium.PolyLine(
        st.session_state['route_coords'], 
        color="blue", 
        weight=5, 
        opacity=0.8
    ).add_to(m)
    
    # 3. Adiciona marcadores de Início e Fim
    folium.Marker(
        location=st.session_state['start_point'], 
        popup=f"Início: {start_location}", 
        icon=folium.Icon(color="green", icon="play")
    ).add_to(m)
    
    folium.Marker(
        location=st.session_state['end_point'], 
        popup=f"Destino: {end_location}", 
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(m)
    
    # 4. Exibe o mapa no Streamlit
    folium_static(m)

    st.markdown("---")
    st.caption("A lógica de ML/Roteamento está implementada em 'core/routing.py' e utiliza o modelo 'preditor.pkl' e o seu dataset de acidentes.")
