import streamlit as st
import folium
from streamlit_folium import st_folium
import requests

# URL base para geocodificação Nominatim
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Função para converter nome de cidade em coordenadas (lat, lon)
def geocodificar_cidade(cidade):
    """Converte o nome de uma cidade em coordenadas (latitude, longitude) usando Nominatim."""
    headers = {
        "User-Agent": "CalculadoraDeRotasStreamlit/1.0 (contato@exemplo.com)"
    }
    params = {
        "q": cidade,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
    }
    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            # Retorna (latitude, longitude)
            return float(data[0]["lat"]), float(data[0]["lon"])
        else:
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao geocodificar '{cidade}': {e}")
        return None

st.title("Calculadora de Rotas de Trânsito")

# Inicialização do session_state para evitar KeyError
if "ufA" not in st.session_state:
    st.session_state["ufA"] = "PE"
if "municipioA" not in st.session_state:
    st.session_state["municipioA"] = "Recife"
if "ufB" not in st.session_state:
    st.session_state["ufB"] = "PE"
if "municipioB" not in st.session_state:
    st.session_state["municipioB"] = "Porto de Galinhas"
if "rota_coords" not in st.session_state:
    st.session_state["rota_coords"] = None
if "distancia" not in st.session_state:
    st.session_state["distancia"] = None
if "duracao" not in st.session_state:
    st.session_state["duracao"] = None

# Função para calcular rota
def calcular_rota():
    # Constrói a string de busca para geocodificação
    cidadeA_busca = f"{st.session_state['municipioA']}, {st.session_state['ufA']}"
    cidadeB_busca = f"{st.session_state['municipioB']}, {st.session_state['ufB']}"

    # 1. Geocodificar as cidades
    coordsA = geocodificar_cidade(cidadeA_busca)
    coordsB = geocodificar_cidade(cidadeB_busca)

    if not coordsA:
        st.error(f"Não foi possível encontrar as coordenadas para '{cidadeA_busca}'.")
        st.session_state["rota_coords"] = None
        return
    if not coordsB:
        st.error(f"Não foi possível encontrar as coordenadas para '{cidadeB_busca}'.")
        st.session_state["rota_coords"] = None
        return

    latA, lonA = coordsA
    latB, lonB = coordsB

    # 2. Calcular a rota usando as coordenadas
    url = (
        f"https://routing.openstreetmap.de/routed-car/route/v1/driving/"
        f"{lonA},{latA};"  # OSRM espera (lon, lat)
        f"{lonB},{latB}"   # OSRM espera (lon, lat)
        f"?overview=full&geometries=geojson"
    )
    
    try:
        res = requests.get(url, timeout=10).json()
        if res.get("routes"):
            route = res["routes"][0]
            coords = route["geometry"]["coordinates"]
            # Converte para (lat, lon) para Folium
            st.session_state["rota_coords"] = [(lat, lon) for lon, lat in coords]
            st.session_state["distancia"] = route["distance"] / 1000  # km
            st.session_state["duracao"] = route["duration"] / 60      # min
            st.session_state["latA"] = latA
            st.session_state["lonA"] = lonA
            st.session_state["latB"] = latB
            st.session_state["lonB"] = lonB
        else:
            st.error("Não foi possível calcular a rota entre as cidades fornecidas.")
            st.session_state["rota_coords"] = None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao calcular a rota: {e}")
        st.session_state["rota_coords"] = None


# Entrada de UF e Município
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Ponto de Origem (A)")
    st.session_state["ufA"] = st.text_input("UF (A)", value=st.session_state["ufA"], max_chars=2, key="ufA_input")
    st.session_state["municipioA"] = st.text_input("Município (A)", value=st.session_state["municipioA"], key="municipioA_input")

with col2:
    st.markdown("### Ponto de Destino (B)")
    st.session_state["ufB"] = st.text_input("UF (B)", value=st.session_state["ufB"], max_chars=2, key="ufB_input")
    st.session_state["municipioB"] = st.text_input("Município (B)", value=st.session_state["municipioB"], key="municipioB_input")

st.button("Calcular Rota", on_click=calcular_rota)

# Exibir mapa se houver rota salva
if st.session_state["rota_coords"]:
    st.markdown(f"**Distância:** {st.session_state['distancia']:.2f} km | "
                f"**Tempo estimado:** {st.session_state['duracao']:.1f} min")

    # Coordenadas geocodificadas são salvas em session_state["latA/lonA"] dentro de calcular_rota
    centro = [
        (st.session_state["latA"] + st.session_state["latB"]) / 2,
        (st.session_state["lonA"] + st.session_state["lonB"]) / 2,
    ]
    m = folium.Map(location=centro, zoom_start=9)
    folium.Marker(
        [st.session_state["latA"], st.session_state["lonA"]],
        popup=f"Origem: {st.session_state['municipioA']} - {st.session_state['ufA']}", icon=folium.Icon(color="green")
    ).add_to(m)
    folium.Marker(
        [st.session_state["latB"], st.session_state["lonB"]],
        popup=f"Destino: {st.session_state['municipioB']} - {st.session_state['ufB']}", icon=folium.Icon(color="red")
    ).add_to(m)
    folium.PolyLine(st.session_state["rota_coords"], color="blue", weight=5).add_to(m)
    st_folium(m, width=700, height=500)
