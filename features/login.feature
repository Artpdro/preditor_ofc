# language: pt

Funcionalidade: Autenticação de Usuário
    
    Contexto:
        Como um usuário do sistema
        Eu quero fazer login com minhas credenciais
        Para acessar minhas funcionalidades personalizadas
        Dado que o usuário está logado no sistema
        E que o sistema está rodando

    Cenário: Tentativa de login com campos vazios
        Dado que eu estou na página de login
        Quando tento entrar com email "" e senha ""
        Então o sistema deve exibir a mensagem "Por favor, preencha todos os campos."

    Cenário: Tentativa de login com credenciais inválidas
        Dado que eu estou na página de login
        Quando tento entrar com email "admin@safeway.com" e senha "senhaErrada"
        Então o sistema deve exibir a mensagem "Email ou senha inválidos."

    Cenário: Login bem-sucessido
        Dado que eu estou na página de login
        Quando tento entrar com email "admin@safeway.com" e senha "12345678"
        Então o sistema deve redirecionar para "pages/interface.py"


    