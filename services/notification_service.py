from services.database_service import conectar

def criar_notificacao(mensagem):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO notificacoes (mensagem) VALUES (?)",
        (mensagem,)
    )

    conn.commit()
    conn.close()

    return f"🔔 Notificação criada: {mensagem}"

def listar_notificacoes():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT mensagem, criado_em
        FROM notificacoes
        ORDER BY id DESC
        LIMIT 20
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhuma notificação."

    return "\n".join([
        f"🔔 {mensagem} ({data})"
        for mensagem, data in dados
    ])