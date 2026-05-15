from services.database_service import conectar

def criar_evento(nome, data):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO calendario (nome, data)
        VALUES (?, ?)
        """,
        (nome, data)
    )

    conn.commit()

    conn.close()

    return f"📅 Evento criado: {nome}"

def listar_eventos():

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, data
        FROM calendario
        ORDER BY id DESC
    """)

    eventos = cursor.fetchall()

    conn.close()

    if not eventos:
        return "Nenhum evento encontrado."

    resultado = []

    for evento in eventos:

        resultado.append(
            f"{evento[0]} - {evento[1]}"
        )

    return "\n".join(resultado)