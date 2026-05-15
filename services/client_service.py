from services.database_service import conectar

def criar_cliente(nome):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO clientes (nome)
        VALUES (?)
        """,
        (nome,)
    )

    conn.commit()

    conn.close()

    return f"👤 Cliente criado: {nome}"

def listar_clientes():

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome
        FROM clientes
        ORDER BY id DESC
    """)

    clientes = cursor.fetchall()

    conn.close()

    if not clientes:
        return "Nenhum cliente encontrado."

    return "\n".join([
        cliente[0]
        for cliente in clientes
    ])