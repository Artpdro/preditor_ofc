import pandas as pd
import os
import json
import ollama
import re
from pandas.core.series import Series

# --- Configuração ---
OLLAMA_MODEL = "llama3.1" # Modelo recomendado para o Ollama
JSON_FILE_PATH = "datatran_consolidado.json"

def load_data():
    """Carrega o arquivo JSON em um DataFrame do Pandas com pré-processamento."""
    # Garante que o caminho seja relativo ao diretório do projeto
    # O arquivo está na raiz do projeto, mas o script está em core/
    full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", JSON_FILE_PATH)

    if not os.path.exists(full_path):
        print(f"Erro: Arquivo de dados não encontrado em {full_path}")
        return None

    try:
        # Carrega o JSON
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        
        # Pré-processamento dos dados: minúsculas e sem acentos para facilitar a consulta do LLM
        df['data_inversa'] = pd.to_datetime(df['data_inversa'], format='%d/%m/%Y', errors='coerce')
        df['latitude'] = df['latitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
        df['longitude'] = df['longitude'].astype(str).str.replace(',', '.', regex=False).astype(float)
        
        # Novo pré-processamento para a coluna de horário
        if 'horario' in df.columns:
            # Converte para datetime, extrai a hora e armazena em uma nova coluna 'hora'
            df['hora'] = pd.to_datetime(df['horario'], format='%H:%M:%S', errors='coerce').dt.hour
            # Remove linhas onde a conversão falhou
            df.dropna(subset=['hora'], inplace=True)
            df['hora'] = df['hora'].astype(int)
        
        for col in ['dia_semana', 'uf', 'municipio', 'tipo_acidente', 'condicao_metereologica']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.lower().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
        
        return df
    except Exception as e:
        print(f"Erro ao carregar ou processar o JSON: {e}")
        return None

def generate_and_execute_code_ollama(df: pd.DataFrame, query: str):
    """Usa o Ollama para gerar código Python e o executa para obter a resposta."""
    
    # Define o prompt para o Ollama
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
    
    Para o tipo de acidente 'Saida de leito carrocavel', use 'saida de leito carrocavel', utilize para todos os outros tipos.

    Para as UF(estados) como 'PE', use o nome por extenso como 'Pernambuco', utilize para todos os outros tipos.

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
    
    # Chamada ao Ollama
    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Gere o código Python para a pergunta."}
            ],
            options={"temperature": 0.0}
        )
        
        # Extrai o código gerado
        generated_text = response["message"]["content"]
        
        # Usa regex para extrair o bloco de código
        match = re.search(r"```python\n(.*?)```", generated_text, re.DOTALL)
        if match:
            generated_code = match.group(1).strip()
        else:
            # Se não encontrar o bloco, assume que o texto gerado é o código
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
        return f"Erro ao gerar ou executar o código: {e}. Certifique-se de que o Ollama está rodando e o modelo '{OLLAMA_MODEL}' está instalado."

if __name__ == "__main__":
    # Teste de funcionalidade
    df = load_data()
    if df is not None:
        example_query = "Qual dia da semana tem mais acidentes de colisao traseira?"
        print(f"\n--- Teste com a pergunta: '{example_query}' ---")
        
        # Nota: Este teste falhará no ambiente sandbox, pois o Ollama não está rodando aqui.
        # Ele serve apenas para validar a estrutura do código.
        response = generate_and_execute_code_ollama(df, example_query)
        print(f"Resposta da IA: {response}")
