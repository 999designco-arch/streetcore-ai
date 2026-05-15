from services.database_service import conectar

def salvar_memoria(texto):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memorias (texto) VALUES (?)", (texto,))
    conn.commit()
    conn.close()
    return True

def listar_memorias():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT texto, criado_em FROM memorias ORDER BY id DESC LIMIT 20")
    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhuma memória salva ainda."

    return "\n".join([f"- {texto} ({data})" for texto, data in dados])