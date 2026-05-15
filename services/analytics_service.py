eventos = {}

def registrar_evento(nome):
    eventos[nome] = eventos.get(nome, 0) + 1

def resumo_analytics():
    return {
        "eventos": eventos,
        "status": "analytics ativo"
    }