# language: pt

Funcionalidade: Predição de acidentes e Rotas

    Contexto:
        Como um usuário do sistema
        Eu quero utilizar a Funcionalidade de Predição de Acidentes e Rotas
        Para melhorar a segurança e eficiência das viagens
        Dado que o usuário está logado no sistema
        E que o sistema está rodando

        Cenário: Tratamento de valores desconhecidos na predição de acidentes
            Quando insiro "Município" chamado "CidadeInexistente"
            E solicito a predição de acidentes
            Então o sistema deve usar o valor padrão 0 para o cálculo
            E o sistema deve retornar uma predição válida

        Cenário: Validar codificação de dados existentes na predição de acidentes
            Quando insiro um "tipo_acidente" chamado "Colisao frontal"
            E solicito a predição
            Então o sistema deve encontrar o índice correto no mapeamento
            E o sistema deve retornar uma predição válida

        Cenário: Cálcular rota entre cidades válidas
            Quando configuro a cidade de origem para "Recife, PE"
            E configuro a cidade de destino para "Olinda, PE"
            E solicito o cálculo da rota
            Então o sistema deve exibir "MELHOR ROTA" com o curso da viagem ajustado
            E o sistema deve retornar uma rota otimizada entre "Recife, PE" e "Olinda, PE"

        Cenário: Falha ao geocodificar cidade inválida
            Quando configuro a origem para "Hogwarts"
            E solicito o cálculo da rota
            Então o sistema deve exibir "Erro! Não foi possível geocodificar a cidade de origem."
            E o sistema não deve tentar calcular a rota

