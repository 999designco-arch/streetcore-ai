eventos = {}

def registrar_evento(nome):
    eventos[nome] = eventos.get(nome, 0) + 1

def resumo_analytics():
    return {
        "versao": "V11",
        "eventos": eventos,
        "total_eventos": sum(eventos.values()),
        "status": "analytics ativo"
    }