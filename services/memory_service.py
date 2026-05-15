memorias = []

def salvar_memoria(texto):
    memorias.append(texto)
    return True

def listar_memorias():
    if not memorias:
        return "Nenhuma memória salva ainda."
    return "\n".join(f"- {m}" for m in memorias[-10:])