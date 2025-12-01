# language: pt

Funcionalidade: Segurança e disponibilidade do sistema
    
    Contexto:
        Como um usuário do sistema
        Eu quero garantir a segurança e disponibilidade do sistema
        para proteger meus dados e assegurar o acesso contínuo
        Dado que o usuário está logado no sistema
        E que o sistema está rodando

    Cenário: Verificar sessão expirada após período de inatividade
        Dado que o sistema está rodando
        E eu estou logado no sistema
        Quando eu fico inativo por 15 minutos
        Então minha sessão deve expirar
        E eu devo ser redirecionado para a página de login
        E eu devo ver a mensagem: "Sua sessão expirou. Por favor, faça login novamente."

    Cenário: Bloquear acesso direto sem autenticação
        Dado que o sistema está rodando
        Quando eu tento acessar a interface principal sem estar autenticado
        Então o acesso deve ser negado e eu devo ser redirecionado para a página de login
        E eu devo ver a mensagem: "Por favor, faça login para continuar."

    Cenário: Verificar disponibilidade do chatbot
        Dado que o sistema está rodando
        Quando verifico a disponibilidade do chatbot
        Então o serviço deve responder com status code 200
        E eu devo ver a mensagem: "Serviço de chatbot está disponível"