from services.database_service import conectar

def criar_lead(nome, origem="manual"):
    if not nome:
        return "Use assim: /lead nome_do_cliente"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO leads (nome, origem, status) VALUES (?, ?, ?)",
        (nome, origem, "novo")
    )

    conn.commit()
    conn.close()

    return f"🎯 Lead criado: {nome}"

def listar_leads():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, origem, status, criado_em
        FROM leads
        ORDER BY id DESC
        LIMIT 50
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhum lead encontrado."

    return "\n".join([
        f"#{id} - {nome} | {origem} | {status} ({data})"
        for id, nome, origem, status, data in dados
    ])

def atualizar_lead(lead_id, status):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE leads SET status=? WHERE id=?",
        (status, lead_id)
    )

    conn.commit()
    conn.close()

    return f"✅ Lead #{lead_id} atualizado para: {status}"