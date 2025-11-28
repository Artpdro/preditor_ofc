import pandas as pd
import os
import re
from pandas.core.series import Series
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# --- Configuração ---
GEMINI_MODEL = "gemini-2.5-flash"
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

# Inicializa o cliente Gemini. Ele buscará a chave GEMINI_API_KEY automaticamente.
try:
    client = genai.Client()
except Exception as e:
    print(f"Erro ao inicializar o cliente Gemini: {e}")
    client = None

from pymongo import MongoClient

def load_data():
    """Carrega os dados do MongoDB em um DataFrame do Pandas com pré-processamento."""
    
    if not all([MONGO_URI, DB_NAME, COLLECTION_NAME]):
        print("Erro: Variáveis de ambiente do MongoDB (MONGO_URI, DB_NAME, COLLECTION_NAME) não configuradas.")
        return None

    try:
        # Conecta ao MongoDB
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        # Carrega todos os documentos da coleção para um DataFrame
        data = list(collection.find({}))
        df = pd.DataFrame(data)
        
        # Remove a coluna _id do MongoDB, se existir
        if '_id' in df.columns:
            df = df.drop(columns=['_id'])
        
        # Pré-processamento dos dados
        df['data_inversa'] = pd.to_datetime(df['data_inversa'], format='%d/%m/%Y', errors='coerce')
        df['latitude'] = df['latitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
        df['longitude'] = df['longitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
        
        # Novo pré-processamento para a coluna de horário
        if 'horario' in df.columns:
            df['hora'] = pd.to_datetime(df['horario'], format='%H:%M:%S', errors='coerce').dt.hour
            df.dropna(subset=['hora'], inplace=True)
            df['hora'] = df['hora'].astype(int)
        
        # Pré-processamento de texto: minúsculas e sem acentos
        for col in ['dia_semana', 'uf', 'municipio', 'tipo_acidente', 'condicao_metereologica']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        
        return df
    except Exception as e:
        print(f"Erro ao carregar ou processar os dados do MongoDB: {e}")
        return None

def generate_and_execute_code_gemini(df: pd.DataFrame, query: str):
    """Usa o Gemini para gerar código Python e o executa para obter a resposta."""
    
    if client is None:
        return "Erro: Cliente Gemini não inicializado. Verifique se a variável de ambiente GEMINI_API_KEY está configurada."

    # Define o prompt para o Gemini
    prompt = f"""
    Você é um assistente de análise de dados. Sua tarefa é gerar um código Python que usa a biblioteca 'pandas' para responder a uma pergunta sobre o DataFrame chamado 'df'.
    O DataFrame 'df' já está carregado e contém dados de acidentes de trânsito.
    
    IMPORTANTE: Todas as colunas de texto (dia_semana, uf, municipio, tipo_acidente, condicao_metereologica) foram convertidas para MINÚSCULAS e SEM ACENTOS. Use apenas valores em minúsculas e sem acentos para filtragem.
    
    Para facilitar o mapeamento, use a seguinte tabela de conversão para os dias da semana:
    - Segunda-feira -> segunda-feira
    - Terça-feira -> terca-feira
    - Quarta-feira -> quarta-feira
    - Quinta-feira -> quinta-feira
    - Sexta-feira -> sexta-feira
    - Sábado -> sabado
    - Domingo -> domingo
    
    Para facilitar o entendimento, traduza as UFs(estados) para nomes em extensos como: MG -> Minas Gerais

    Para facilitar o entendimento, traduza os tipos acidentes para o normal da língua portuguesa como: Saida de leito carrocavel -> Saída de leito carroçável

    O seu código DEVE aplicar o filtro usando os valores sem acentos e em minúsculas.
    
    As colunas relevantes são:
    - 'data_inversa' (datetime)
    - 'dia_semana' (string, minúsculas, sem acentos)
    - 'uf' (string, minúsculas, sem acentos)
    - 'municipio' (string, minúsculas, sem acentos)
    - 'tipo_acidente' (string, minúsculas, sem acentos)
    - 'condicao_metereologica' (string, minúsculas, sem acentos)
    - 'hora' (integer, 0-23) - **NOVA COLUNA** com a hora do acidente.
    
    A pergunta é: "{query}"
    
    Gere APENAS o código Python necessário para calcular a resposta. O código deve ser uma única string de código que, quando executada, armazena o resultado final em uma variável chamada 'final_result'.
    
    O valor de 'final_result' DEVE ser uma string formatada em português, respondendo diretamente à pergunta do usuário com o resultado da análise.
    
    Exemplo de código para 'Qual dia da semana tem mais acidentes?':
    ```python
    most_frequent_day = df['dia_semana'].value_counts().idxmax()
    final_result = f"O dia da semana com a maior frequência de acidentes é a {{most_frequent_day}}."
    ```
    
    Gere o código para a pergunta: "{query}"
    """
    
    # Chamada ao Gemini
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                temperature=0.0,
            )
        )
        
        # Extrai o código gerado
        generated_text = response.text
        
        # Usa regex para extrair o bloco de código
        match = re.search(r"```python\n(.*?)```", generated_text, re.DOTALL)
        if match:
            generated_code = match.group(1).strip()
        else:
            # Se não encontrar o bloco, tenta extrair o código de forma mais agressiva
            match_aggressive = re.search(r"```(.*?)```", generated_text, re.DOTALL)
            if match_aggressive:
                generated_code = match_aggressive.group(1).strip()
            else:
                # Se ainda assim não encontrar, assume que o texto gerado é o código
                generated_code = generated_text.strip()
        
        # Executa o código gerado
        local_vars = {'df': df, 'final_result': None, 'pd': pd, 'Series': Series}
        
        exec(generated_code, globals(), local_vars)
        
        # Tratamento de erro após a execução
        if local_vars['final_result'] is None:
            return "Não foi possível gerar a resposta. O código gerado pode ter falhado ou não ter definido 'final_result'."
        
        return local_vars['final_result']
        
    except Exception as e:
        # Se o erro for de sequência vazia, é porque o filtro não encontrou nada
        if "attempt to get argmax of an empty sequence" in str(e):
            return "Não foram encontrados acidentes do tipo solicitado para realizar a análise."
        return f"Erro ao conectar com Gemini: {e}. Verifique se a variável de ambiente GEMINI_API_KEY está configurada corretamente."

if __name__ == "__main__":
    # Teste de funcionalidade
    df = load_data()
    if df is not None:
        example_query = "Qual dia da semana tem mais acidentes de colisao traseira?"
        print(f"\n--- Teste com a pergunta: '{example_query}' ---")
        
        # Nota: Este teste falhará no ambiente sandbox, pois a chave de API não está configurada aqui.
        # Ele serve apenas para validar a estrutura do código.
        response = generate_and_execute_code_gemini(df, example_query)
        print(f"Resposta da IA: {response}")
