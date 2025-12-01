import pytest
import sys
import os
from datetime import datetime, timedelta

# Adiciona o diretório pai para conseguir importar módulos se necessário
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 1. Simulação  das classes do sistema
class ValidadorLogin:
    def validar(self, email, senha):
        if not email or not senha:
            return False, "Campos vazios"
        if len(senha) < 8:
            return False, "Senha curta"
        if "@" not in email:
            return False, "Email inválido"
        return True, "OK"

class CalculadoraRota:
    def calcular_risco(self, origem, destino):
        cidades_proibidas = ["Hogwarts", "Narnia"]
        if origem in cidades_proibidas or destino in cidades_proibidas:
            raise ValueError("Cidade inexistente")
        return "Rota calculada com sucesso"

class PreditorAcidentes:
    def prever(self, dados):
        if dados.get("municipio") == "Desconhecido":
            return 0
        return 100

class GerenciadorSessao:
    def verificar_acesso(self, usuario_logado):
        """Retorna True se o usuário tiver permissão, False caso contrário."""
        if not usuario_logado:
            return False, "Acesso negado: Login necessário"
        return True, "Acesso permitido"

    def checar_expiracao(self, ultimo_acesso, limite_minutos=15):
        """Verifica se o tempo de inatividade excedeu o limite."""
        agora = datetime.now()
        tempo_passado = agora - ultimo_acesso
        # timedelta converte minutos para segundos/dias
        if tempo_passado > timedelta(minutes=limite_minutos):
            return True, "Sessão expirada"
        return False, "Sessão ativa"

class ChatbotService:
    def verificar_status_api(self):
        """Simula um 'ping' na API do chatbot"""
        api_online = True 
        if api_online:
            return 200
        return 503

# 2. Casos de testes unitários (PYTEST)

# Teste: LOGIN
def test_01_login_campos_vazios():
    validador = ValidadorLogin()
    sucesso, msg = validador.validar("", "")
    assert sucesso is False
    assert msg == "Campos vazios"

def test_02_login_senha_curta():
    validador = ValidadorLogin()
    sucesso, msg = validador.validar("admin@teste.com", "123")
    assert sucesso is False

def test_03_login_sucesso():
    validador = ValidadorLogin()
    sucesso, msg = validador.validar("admin@teste.com", "12345678")
    assert sucesso is True

# Teste: ROTAS E PREDIÇÃO
def test_04_rota_valida():
    calc = CalculadoraRota()
    resultado = calc.calcular_risco("Recife", "Olinda")
    assert resultado == "Rota calculada com sucesso"

def test_05_rota_cidade_invalida():
    calc = CalculadoraRota()
    with pytest.raises(ValueError, match="Cidade inexistente"):
        calc.calcular_risco("Hogwarts", "Olinda")

def test_06_predicao_valor_padrao():
    preditor = PreditorAcidentes()
    resultado = preditor.prever({"municipio": "Desconhecido"})
    assert resultado == 0

# Teste: SEGURANÇA
def test_07_acesso_negado_sem_login():
    """Testa se o sistema bloqueia acesso direto sem estar logado"""
    seguranca = GerenciadorSessao()
    # Simula usuário não logado
    permitido, msg = seguranca.verificar_acesso(usuario_logado=False)
    assert permitido is False
    assert msg == "Acesso negado: Login necessário"

def test_08_sessao_expirada():
    """Testa a lógica de expiração de tempo"""
    seguranca = GerenciadorSessao()
    # Cria uma data simulada de 20 minutos atrás
    vinte_minutos_atras = datetime.now() - timedelta(minutes=20)
    expirou, msg = seguranca.checar_expiracao(ultimo_acesso=vinte_minutos_atras, limite_minutos=15)
    assert expirou is True
    assert msg == "Sessão expirada"

def test_09_sessao_ativa():
    """Testa se a sessão continua ativa dentro do limite de tempo"""
    seguranca = GerenciadorSessao()
    # Cria uma data simulada de 5 minutos atrás
    cinco_minutos_atras = datetime.now() - timedelta(minutes=5)
    expirou, msg = seguranca.checar_expiracao(ultimo_acesso=cinco_minutos_atras, limite_minutos=15)
    assert expirou is False
    assert msg == "Sessão ativa"

# Teste: CHATBOT
def test_10_chatbot_disponivel():
    """Testa se o serviço do chatbot retorna status 200 (OK)"""
    bot = ChatbotService()
    status = bot.verificar_status_api()
    assert status == 200