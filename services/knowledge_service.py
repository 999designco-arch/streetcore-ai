from services.database_service import conectar

def adicionar_conhecimento(texto):
    if not texto:
        return False

    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO conhecimento (texto) VALUES (?)", (texto,))
    conn.commit()
    conn.close()
    return True

def listar_conhecimento():
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("SELECT texto, criado_em FROM conhecimento ORDER BY id DESC LIMIT 10")
    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhum conhecimento salvo."

    return "\n\n".join([f"- {texto[:1000]}\n({data})" for texto, data in dados])

def buscar_conhecimento(termo):
    conn = conectar()
    cursor = conn.cursor()

    busca = f"%{termo}%"

    cursor.execute("""
        SELECT texto, criado_em
        FROM conhecimento
        WHERE texto LIKE ?
        ORDER BY id DESC
        LIMIT 10
    """, (busca,))

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return f"Nenhum resultado encontrado para: {termo}"

    return "\n\n".join([f"🔎 {texto[:1000]}\n({data})" for texto, data in dados])