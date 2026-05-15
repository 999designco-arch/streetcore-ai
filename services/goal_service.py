from services.database_service import conectar

def criar_meta(nome, valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO metas (nome, valor, status) VALUES (?, ?, ?)",
        (nome, valor, "ativa")
    )

    conn.commit()
    conn.close()

    return f"🎯 Meta criada: {nome} | Valor: {valor}"

def listar_metas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, valor, status, criado_em
        FROM metas
        ORDER BY id DESC
        LIMIT 50
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhuma meta cadastrada."

    return "\n".join([
        f"#{id} - {nome} | {valor} | {status} ({data})"
        for id, nome, valor, status, data in dados
    ])

def atualizar_meta(meta_id, status):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE metas SET status=? WHERE id=?",
        (status, meta_id)
    )

    conn.commit()
    conn.close()

    return f"✅ Meta #{meta_id} atualizada para: {status}"