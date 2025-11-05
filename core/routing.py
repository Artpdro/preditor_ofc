# preditor_ofc/core/routing.py

import json
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import osmnx as ox
import networkx as nx
import numpy as np
from pathlib import Path
import joblib # Importar para carregar o modelo

# --- Configuração ---
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "datatran_consolidado.json"
MODEL_PATH = PROJECT_ROOT / "preditor.pkl" # Caminho para o modelo
MAPPINGS_PATH = PROJECT_ROOT / "label_encoder_mappings.json" # Caminho para os mapeamentos
ox.settings.log_console = True
ox.settings.use_cache = True

# Inicializa o geocodificador
geolocator = Nominatim(user_agent="safeway_app_geocoder")

# --- 1. Funções de Carregamento de Recursos ---

def load_resources():
    """Carrega o modelo, os mapeamentos e os dados de risco."""
    resources = {}
    
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
    try:
        with open(MAPPINGS_PATH, 'r', encoding='utf-8') as f:
            resources['mappings'] = json.load(f)
    except FileNotFoundError:
        print(f"Erro: Arquivo de mapeamentos não encontrado em {MAPPINGS_PATH}")
        resources['mappings'] = {}
    except Exception as e:
        print(f"Erro ao carregar os mapeamentos: {e}")
        resources['mappings'] = {}

    # Carregar e processar dados de risco (mantido para compatibilidade do grafo)
    try:
        with open(DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        
        # Limpeza e conversão das colunas de Lat/Lon
        df['latitude'] = df['latitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
        df['longitude'] = df['longitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
        
        # Agrupar acidentes por localização para obter um "score de risco"
        risk_points = df.groupby(['latitude', 'longitude']).size().reset_index(name='risk_count')
        max_count = risk_points['risk_count'].max()
        risk_points['risk_score'] = risk_points['risk_count'] / max_count
        
        resources['risk_df'] = risk_points
        
    except FileNotFoundError:
        print(f"Erro: Arquivo de dados de risco não encontrado em {DATA_PATH}")
        resources['risk_df'] = pd.DataFrame()
    except Exception as e:
        print(f"Erro ao processar dados de risco: {e}")
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
        # Tenta geocodificar o local
        location = geolocator.geocode(location_name, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except GeocoderTimedOut:
        return None, None
    except Exception as e:
        print(f"Erro de geocodificação para {location_name}: {e}")
        return None, None

# --- 3. Funções de Otimização de Rota Geoespacial ---

def calculate_safe_route(start_lat, start_lon, end_lat, end_lon, risk_df=RISK_DF, model=MODEL, mappings=MAPPINGS):
    """
    Calcula a rota otimizada (mais segura) entre dois pontos.
    
    A lógica é:
    1. Obter o grafo da rede viária (OSMnx).
    2. Encontrar os nós mais próximos de início e fim.
    3. Para cada aresta (trecho) do grafo, calcular um custo que inclua a distância e o risco.
    4. Usar o algoritmo de Dijkstra (networkx) para encontrar o caminho com o menor custo total.
    """
    
    if model is None:
        print("Modelo de ML não carregado. Usando apenas a heurística de risco de acidentes.")
    
    # 1. Obter o grafo da rede viária
    try:
        # Tentamos baixar o grafo de uma área de 5km ao redor do ponto inicial
        G = ox.graph_from_point((start_lat, start_lon), dist=5000, network_type="drive")
    except Exception as e:
        print(f"Erro ao baixar o grafo da rede viária: {e}")
        return None, 0.0

    # 2. Encontrar os nós mais próximos
    # 2. Encontrar os nós mais próximos
    # Usar 'return_dist=True' para garantir que a busca seja bem-sucedida e que os nós estejam dentro do grafo.
    # O OSMnx espera (longitude, latitude)
    try:
        orig_node, dist_orig = ox.nearest_nodes(G, start_lon, start_lat, return_dist=True)
        dest_node, dist_dest = ox.nearest_nodes(G, end_lon, end_lat, return_dist=True)
    except Exception as e:
        print(f"Erro ao encontrar nós mais próximos: {e}")
        return None, 0.0

    # Adicionar uma verificação de sanidade para garantir que os nós foram encontrados
    if orig_node is None or dest_node is None:
        print("Nó de origem ou destino não encontrado no grafo.")
        return None, 0.0

    # 3. Calcular o custo de cada aresta (Distância + Risco)
    
    # Adiciona o atributo 'length' (distância) se não existir
    G = ox.add_edge_speeds(G)
    G = ox.add_edge_travel_times(G)
    
    # Função para calcular o score de risco de um trecho (aresta)
    def calculate_edge_risk(u, v, data):
        # O risco é calculado com base no modelo de ML (se disponível) ou heurística
        
        # 3.1. Usamos o ponto médio da aresta para simplificar
        mid_lat = (G.nodes[u]['y'] + G.nodes[v]['y']) / 2
        mid_lon = (G.nodes[u]['x'] + G.nodes[v]['x']) / 2
        
        # 3.2. Heurística de proximidade de acidentes (Fallback)
        # Encontra o ponto de risco mais próximo no RISK_DF
        if risk_df.empty:
            heuristic_risk = 0.0
        else:
            # Calcula a distância euclidiana (aproximada) até os pontos de risco
            distances = np.sqrt((risk_df['latitude'] - mid_lat)**2 + (risk_df['longitude'] - mid_lon)**2)
            nearest_risk_index = distances.argmin()
            
            # O risco é inversamente proporcional à distância e diretamente proporcional ao score
            risk_score = risk_df.loc[nearest_risk_index, 'risk_score']
            heuristic_risk = risk_score * np.exp(-distances.min() / 0.001)
            
        # 3.3. Risco do Modelo de ML (Prioridade)
        if model is not None:
            # Para usar o modelo, precisamos de features.
            # Como não temos o dataset completo para engenharia de features, 
            # vamos simular features simples para demonstração:
            # - hour_of_day (ex: 12)
            # - day_of_week (ex: 3 - Quarta-feira)
            # - road_type (ex: 'FEDERAL') - Simulamos com base na lat/lon
            
            # **NOTA:** Esta é uma SIMULAÇÃO de features. Em um projeto real,
            # você precisaria de mais dados contextuais (velocidade, tipo de via, clima, etc.)
            
            # Simulação de features para o modelo (usando valores médios/padrão)
            # Assumimos que o modelo usa features codificadas (Label Encoding)
            
            # Simulação de tipo de via (ex: 'FEDERAL' para rodovias, 'MUNICIPAL' para urbanas)
            # Isso é extremamente simplificado e deve ser melhorado com dados reais do OSMnx
            road_type = 'FEDERAL' # Simplificação
            
            # Simulação de hora do dia e dia da semana (ex: agora)
            from datetime import datetime
            now = datetime.now()
            hour_of_day = now.hour
            day_of_week = now.weekday() # 0=Segunda, 6=Domingo
            
            # Codificação das features
            try:
                # Exemplo: Se o modelo espera 'tipo_via_encoded'
                road_type_encoded = mappings.get('tipo_via', {}).get(road_type, 0)
                
                # Criar o DataFrame de entrada (ajustar colunas conforme o modelo.pkl)
                # O modelo espera 10 features. Como não sabemos quais são as 10 features, 
                # vamos criar 7 features de preenchimento (dummy) com valor 0, além das 3 existentes.
                # **AVISO:** Este é um PALPITE. O correto seria obter a lista exata de features do modelo.
                # Assumindo que o modelo foi treinado com: 
                # [hour_of_day, day_of_week, tipo_via_encoded, dummy_1, dummy_2, dummy_3, dummy_4, dummy_5, dummy_6, dummy_7]
                
                # Criação das 10 features (3 reais + 7 dummies)
                data_row = [hour_of_day, day_of_week, road_type_encoded] + [0] * 7
                column_names = ['hour_of_day', 'day_of_week', 'tipo_via_encoded', 
                                'dummy_1', 'dummy_2', 'dummy_3', 'dummy_4', 'dummy_5', 'dummy_6', 'dummy_7']
                                
                input_data = pd.DataFrame([data_row], columns=column_names)
                
                # Previsão de risco (probabilidade de acidente)
                # Assumindo que o modelo retorna a probabilidade da classe positiva (acidente)
                ml_risk = model.predict(input_data)[0]
                
                # Usamos uma média ponderada entre o risco ML e o risco heurístico
                # O risco ML é mais preciso, então damos mais peso
                risk_weight = (ml_risk * 0.7) + (heuristic_risk * 0.3)
                
            except Exception as e:
                print(f"Erro ao usar o modelo de ML: {e}. Usando apenas risco heurístico.")
                risk_weight = heuristic_risk
        else:
            risk_weight = heuristic_risk
            
        return risk_weight

    # 3. Calcular o custo de cada aresta (Distância + Risco)
    
    # Adiciona o atributo 'risk_weight' a todas as arestas.
    # Usamos ox.utils_graph.add_edge_attribute para garantir que todas as arestas recebam o atributo,
    # mesmo que calculate_edge_risk falhe para algumas (o que não deve acontecer se for bem implementado).
    
    # Cria uma lista de custos para cada aresta
    edge_costs = {}
    total_risk_sum = 0.0
    
    for u, v, k, data in G.edges(keys=True, data=True):
        try:
            risk = calculate_edge_risk(u, v, data)
            # O custo total é uma combinação do tempo de viagem e o risco
            # O fator 1000 é um peso arbitrário para o risco, para que ele influencie a rota
            travel_time = data.get('travel_time', data.get('length', 1) / 30 * 3.6) # Fallback para tempo de viagem
            cost = travel_time + (risk * 1000)
            
            edge_costs[(u, v, k)] = {'cost': cost, 'risk': risk}
            total_risk_sum += risk # Acumula o risco para uma métrica de debug
            
        except Exception as e:
            # Se a função de risco falhar, usa apenas o tempo de viagem como custo
            print(f"Aviso: Erro ao calcular risco para a aresta ({u}, {v}, {k}): {e}. Usando apenas travel_time.")
            travel_time = data.get('travel_time', data.get('length', 1) / 30 * 3.6) # Fallback
            edge_costs[(u, v, k)] = {'cost': travel_time, 'risk': 0.0}
            
    # Aplica os novos atributos de volta ao grafo
    for (u, v, k), attrs in edge_costs.items():
        G.edges[u, v, k]['cost'] = attrs['cost']
        G.edges[u, v, k]['risk'] = attrs['risk']

    # 4. Encontrar o caminho com o menor custo total
    try:
        route = nx.shortest_path(G, orig_node, dest_node, weight='cost')
    except nx.NetworkXNoPath:
        print("Não foi possível encontrar um caminho entre os pontos.")
        return None, 0.0

    # Processar a rota para obter as coordenadas e o risco total
    route_coords = [(G.nodes[node]['y'], G.nodes[node]['x']) for node in route]
    
    # Calcular o risco total da rota
    total_risk = 0
    for i in range(len(route) - 1):
        u = route[i]
        v = route[i+1]
        # Encontra a aresta entre u e v (pode haver múltiplas chaves, pegamos a primeira)
        edge_data = G.get_edge_data(u, v)
        if edge_data:
            # Pega o risco da primeira aresta (chave 0)
            # Multiplicamos pelo comprimento da aresta para ter um risco total mais realista
            total_risk += edge_data[0].get('risk', 0) * edge_data[0].get('length', 1) 
    
    return route_coords, total_risk

# --- Exemplo de Uso (apenas para teste) ---
if __name__ == '__main__':
    # Exemplo: Av. Paulista (SP) para Praça da Sé (SP)
    # Primeiro, geocodificamos
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
