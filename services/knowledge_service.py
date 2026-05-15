base_conhecimento = []

def adicionar_conhecimento(texto):

    base_conhecimento.append(texto)

def buscar_conhecimento():

    if not base_conhecimento:
        return "Nenhum conhecimento salvo."

    return "\n\n".join(
        base_conhecimento[-10:]
    )