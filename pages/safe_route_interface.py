# preditor_ofc/pages/safe_route_interface.py
import streamlit as st
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
    st.error("Erro ao importar as funções de roteamento. Verifique se 'core/routing.py' existe e se as dependências estão instaladas.")
    st.stop()

# --- Carregar Mapeamento de Cidades ---
@st.cache_data
def load_city_map():
    """Carrega o mapeamento de UF para Municípios."""
    try:
        with open(PROJECT_ROOT / "uf_municipio_map.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Erro ao carregar 'uf_municipio_map.json': {e}")
        return {}

UF_MUNICIPIO_MAP = load_city_map()
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
def location_selector(col, prefix):
    """Componente de seleção de UF e Município."""
    with col:
        st.subheader(f"Ponto de {prefix.title()}")
        
        uf = st.selectbox(f"UF de {prefix.title()}", UFS, key=f'{prefix}_uf')
        location = ""
        
        if uf and uf in UF_MUNICIPIO_MAP:
            municipios = sorted([m.title() for m in UF_MUNICIPIO_MAP[uf]])
            municipio = st.selectbox(f"Município de {prefix.title()}", municipios, key=f'{prefix}_municipio')
            
            if municipio:
                location = f"{municipio}, {uf}"
                st.caption(f"Local de {prefix.title()}: {location}")
            else:
                st.warning(f"Selecione um Município para {prefix.title()}.")
        else:
            st.warning(f"Selecione uma UF para carregar os municípios de {prefix.title()}.")
            
        return location

col1, col2 = st.columns(2)
start_location = location_selector(col1, "partida")
end_location = location_selector(col2, "destino")

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
            st.error(f"Não foi possível encontrar as coordenadas para um ou ambos os locais. Tente outro município.")
        else:
            st.success(f"Locais geocodificados: Início ({start_lat:.4f}, {start_lon:.4f}), Fim ({end_lat:.4f}, {end_lon:.4f}).")
            
            with st.spinner("2/3: Calculando rota otimizada (ML + Geoespacial)..."):
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
    
    # Heurística simples para a cor do risco
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
