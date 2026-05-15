from services.database_service import conectar

def registrar_log(tipo, mensagem):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO logs (tipo, mensagem) VALUES (?, ?)",
        (tipo, mensagem)
    )

    conn.commit()

    conn.close()

def listar_logs():

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT tipo, mensagem, criado_em
        FROM logs
        ORDER BY id DESC
        LIMIT 50
    """)

    logs = cursor.fetchall()

    conn.close()

    if not logs:
        return "Nenhum log."

    resultado = []

    for log in logs:

        resultado.append(
            f"[{log[0]}] {log[1]} ({log[2]})"
        )

    return "\n".join(resultado)