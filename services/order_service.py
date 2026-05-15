from services.database_service import conectar

def criar_pedido(nome):
    if not nome:
        return "Digite assim: /order pedido de camiseta"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO pedidos (nome, status) VALUES (?, ?)",
        (nome, "novo")
    )

    conn.commit()
    conn.close()

    return f"📦 Pedido criado: {nome}"

def listar_pedidos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, status, criado_em
        FROM pedidos
        ORDER BY id DESC
        LIMIT 30
    """)

    pedidos = cursor.fetchall()
    conn.close()

    if not pedidos:
        return "Nenhum pedido encontrado."

    return "\n".join([
        f"#{id} - {nome} [{status}] ({data})"
        for id, nome, status, data in pedidos
    ])

def atualizar_status_pedido(pedido_id, status):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE pedidos SET status=? WHERE id=?",
        (status, pedido_id)
    )

    conn.commit()
    conn.close()

    return f"✅ Pedido #{pedido_id} atualizado para: {status}"