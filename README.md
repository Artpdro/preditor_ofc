# Preditor de Acidentes (Adaptado com Rota Segura ML)

Este repositório foi adaptado para incluir uma nova funcionalidade de **Cálculo de Rota Segura** que utiliza a lógica de Machine Learning (ML) e dados geoespaciais para otimizar o trajeto com menor risco de acidentes.

A funcionalidade foi implementada como uma nova página no Streamlit (`pages/safe_route_interface.py`), seguindo a arquitetura recomendada de manter a lógica de ML/Otimização no Backend (simulada aqui) e a visualização no Frontend (Streamlit).

## Alterações Realizadas

1.  **Nova Página Streamlit:** Adicionada a página `pages/safe_route_interface.py` que permite ao usuário inserir coordenadas de início e fim e simula o cálculo da rota mais segura.
2.  **Lógica de ML/Roteamento (Simulada):** A lógica de predição de risco e otimização de rota foi integrada diretamente no `safe_route_interface.py` como funções de simulação (`predict_risk` e `calculate_safe_route`).
3.  **Atualização da Interface Principal:** O arquivo `pages/interface.py` foi atualizado para incluir um botão de navegação para a nova funcionalidade de Rota Segura.

## Como Executar a Nova Funcionalidade

### 1. Pré-requisitos

Certifique-se de ter o Python instalado e as dependências do projeto original.

```bash
# Certifique-se de estar no diretório raiz do projeto
cd preditor_ofc

# Instale as dependências (assumindo que as dependências originais e pandas/streamlit são necessárias)
pip install -r requirements.txt
pip install streamlit pandas
```

### 2. Execução

Execute o aplicativo Streamlit a partir do diretório raiz do projeto:

```bash
streamlit run login.py
```

### 3. Navegação

1.  Faça o **Login** (ou crie uma conta).
2.  Você será redirecionado para a página principal (`interface.py`).
3.  Clique no botão **"Acessar Calculadora de Rota Segura"** para ir para a nova funcionalidade.
4.  Na nova página, insira as coordenadas de início e fim (ou use as coordenadas de exemplo) e clique em **"Calcular Rota Segura"**.

### 4. Implementação Real do ML/Roteamento

As funções `predict_risk` e `calculate_safe_route` em `pages/safe_route_interface.py` são atualmente simulações. Para uma implementação real, você deve:

1.  **Substituir `predict_risk`:** Carregue seu modelo de ML (`preditor.pkl` ou um novo modelo treinado para risco) e use-o para inferir o score de risco de uma coordenada.
2.  **Substituir `calculate_safe_route`:** Utilize bibliotecas geoespaciais (como `osmnx` e `networkx`) para:
    *   Obter o grafo da rede viária.
    *   Ponderar as arestas (trechos de rua) com um custo que combine a distância/tempo e o risco predito pelo seu modelo.
    *   Executar um algoritmo de caminho mais curto (Dijkstra/A*) para encontrar a rota de menor custo total (mais segura).

**Observação:** A visualização da Polyline (a linha da rota) no Streamlit nativo (`st.map`) é limitada. Para desenhar a rota como uma linha, você pode precisar instalar e usar uma biblioteca de terceiros como `streamlit-folium`.

### 5. Chatbot

Faça perguntas ao chatbot como:

1. `"Quais estados com mais acidentes?"`
2. `Quais os tipos de acidente mais comuns?"`
3. `"Qual hora do dia ocorre mais acidentes?"`
4. `"Qual dia da semana ocorre mais acidentes?"`


