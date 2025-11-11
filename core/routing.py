# preditor_ofc/core/routing.py

import json
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import osmnx as ox
import networkx as nx
import numpy as np
from pathlib import Path
import joblib
from datetime import datetime

# --- Configuração ---
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "datatran_consolidado.json"
MODEL_PATH = PROJECT_ROOT / "preditor.pkl"
MAPPINGS_PATH = PROJECT_ROOT / "label_encoder_mappings.json"
ox.settings.log_console = False
ox.settings.use_cache = True

# Inicializa o geocodificador
geolocator = Nominatim(user_agent="safeway_app_geocoder")

# --- 1. Funções de Carregamento de Recursos ---

def load_resources():
    """Carrega o modelo, os mapeamentos e os dados de risco."""
    resources = {}
    
    # Função auxiliar para carregar JSON
    def load_json(path, key):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Erro: Arquivo {key} não encontrado em {path}")
            return {}
        except Exception as e:
            print(f"Erro ao carregar {key}: {e}")
            return {}

    # Carregar o modelo
    try:
        resources['model'] = joblib.load(MODEL_PATH)
    except FileNotFoundError:
        print(f"Erro: Arquivo do modelo não encontrado em {MODEL_PATH}")
        resources['model'] = None
    except Exception as e:
        print(f"Erro ao carregar o modelo: {e}")
        resources['model'] = None

    # Carregar os mapeamentos
    resources['mappings'] = load_json(MAPPINGS_PATH, 'mapeamentos')

    # Carregar e processar dados de risco
    data = load_json(DATA_PATH, 'dados de risco')
    if data:
        try:
            df = pd.DataFrame(data)
            df['latitude'] = df['latitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
            df['longitude'] = df['longitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
            
            # Agrupar acidentes por localização para obter um "score de risco"
            risk_points = df.groupby(['latitude', 'longitude']).size().reset_index(name='risk_count')
            max_count = risk_points['risk_count'].max()
            risk_points['risk_score'] = risk_points['risk_count'] / max_count
            resources['risk_df'] = risk_points
        except Exception as e:
            print(f"Erro ao processar dados de risco: {e}")
            resources['risk_df'] = pd.DataFrame()
    else:
        resources['risk_df'] = pd.DataFrame()
        
    return resources

RESOURCES = load_resources()
MODEL = RESOURCES['model']
MAPPINGS = RESOURCES['mappings']
RISK_DF = RESOURCES['risk_df']

# --- 2. Funções de Geocodificação ---

def geocode_location(location_name):
    """Converte um nome de local em coordenadas (latitude, longitude)."""
    try:
        location = geolocator.geocode(location_name, timeout=10)
        return (location.latitude, location.longitude) if location else (None, None)
    except GeocoderTimedOut:
        return None, None
    except Exception as e:
        print(f"Erro de geocodificação para {location_name}: {e}")
        return None, None

# --- 3. Funções de Otimização de Rota Geoespacial ---

def calculate_edge_risk(u, v, G, risk_df, model, mappings):
    """Calcula o peso de risco para uma aresta."""
    mid_lat = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
    mid_lon = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
    
    heuristic_risk = 0.0
    if not risk_df.empty:
        distances = np.sqrt((risk_df['latitude'] - mid_lat)**2 + (risk_df['longitude'] - mid_lon)**2)
        nearest_risk_index = distances.argmin()
        risk_score = risk_df.loc[nearest_risk_index, 'risk_score']
        # Fator de decaimento: 0.001 é aproximadamente 111 metros (em graus)
        heuristic_risk = risk_score * np.exp(-distances.min() / 0.001)
        
    ml_risk_weight = heuristic_risk
    if model is not None:
        try:
            # Simulação de features para o modelo (usando valores médios/padrão)
            road_type = 'FEDERAL' # Simplificação
            now = datetime.now()
            hour_of_day = now.hour
            day_of_week = now.weekday()
            
            road_type_encoded = mappings.get('tipo_via', {}).get(road_type, 0)
            
            # Criação das 10 features (3 reais + 7 dummies) - Palpite baseado no código original
            data_row = [hour_of_day, day_of_week, road_type_encoded] + [0] * 7
            column_names = ['hour_of_day', 'day_of_week', 'tipo_via_encoded', 
                            'dummy_1', 'dummy_2', 'dummy_3', 'dummy_4', 'dummy_5', 'dummy_6', 'dummy_7']
                            
            input_data = pd.DataFrame([data_row], columns=column_names)
            
            ml_risk = model.predict(input_data)[0]
            ml_risk_weight = (ml_risk * 0.7) + (heuristic_risk * 0.3)
            
        except Exception as e:
            print(f"Aviso: Erro ao usar o modelo de ML: {e}. Usando apenas risco heurístico.")
            ml_risk_weight = heuristic_risk
            
    return ml_risk_weight

def calculate_safe_route(start_lat, start_lon, end_lat, end_lon, risk_df=RISK_DF, model=MODEL, mappings=MAPPINGS):
    """Calcula a rota otimizada (mais segura) entre dois pontos."""
    
    if model is None:
        print("Modelo de ML não carregado. Usando apenas a heurística de risco de acidentes.")
    
    # 1. Obter o grafo da rede viária
    try:
        G = ox.graph_from_point((start_lat, start_lon), dist=5000, network_type="drive")
    except Exception as e:
        print(f"Erro ao baixar o grafo da rede viária: {e}")
        return None, 0.0

    # 2. Encontrar os nós mais próximos
    try:
        orig_node, _ = ox.nearest_nodes(G, start_lon, start_lat, return_dist=True)
        dest_node, _ = ox.nearest_nodes(G, end_lon, end_lat, return_dist=True)
    except Exception as e:
        print(f"Erro ao encontrar nós mais próximos: {e}")
        return None, 0.0

    if orig_node is None or dest_node is None:
        print("Nó de origem ou destino não encontrado no grafo.")
        return None, 0.0

    # 3. Calcular o custo de cada aresta (Distância + Risco)
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    
    for u, v, k, data in G.edges(keys=True, data=True):
        try:
            risk = calculate_edge_risk(u, v, G, risk_df, model, mappings)
            travel_time = data.get('travel_time', data.get('length', 1) / 30 * 3.6)
            cost = travel_time + (risk * 1000) # Peso arbitrário para o risco
            
            G.edges[u, v, k]['cost'] = cost
            G.edges[u, v, k]['risk'] = risk
            
        except Exception as e:
            # Fallback: usa apenas o tempo de viagem como custo
            travel_time = data.get('travel_time', data.get('length', 1) / 30 * 3.6)
            G.edges[u, v, k]['cost'] = travel_time
            G.edges[u, v, k]['risk'] = 0.0
            print(f"Aviso: Erro ao calcular risco para a aresta ({u}, {v}, {k}): {e}. Usando apenas travel_time.")

    # 4. Encontrar o caminho com o menor custo total
    try:
        route = nx.shortest_path(G, orig_node, dest_node, weight='cost')
    except nx.NetworkXNoPath:
        print("Não foi possível encontrar um caminho entre os pontos.")
        return None, 0.0

    # Processar a rota para obter as coordenadas e o risco total
    route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
    
    total_risk = 0
    for i in range(len(route) - 1):
        u = route[i]
        v = route[i+1]
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            # Pega o risco da primeira aresta (chave 0) e multiplica pelo comprimento
            total_risk += edge_data[0].get('risk', 0) * edge_data[0].get('length', 1) 
    
    return route_coords, total_risk

# --- Exemplo de Uso (apenas para teste) ---
if __name__ == '__main__':
    start_loc = "Av. Paulista, São Paulo"
    end_loc = "Praça da Sé, São Paulo"
    
    start_lat, start_lon = geocode_location(start_loc)
    end_lat, end_lon = geocode_location(end_loc)
    
    if start_lat and end_lat:
        print(f"Início: ({start_lat:.4f}, {start_lon:.4f}), Fim: ({end_lat:.4f}, {end_lon:.4f})")
        print("Iniciando cálculo de rota...")
        route, risk = calculate_safe_route(start_lat, start_lon, end_lat, end_lon)
        
        if route:
            print(f"Rota encontrada com {len(route)} pontos.")
            print(f"Risco total da rota (ponderado pelo comprimento): {risk:.4f}")
        else:
            print("Falha ao calcular a rota.")
    else:
        print("Falha na geocodificação.")
