from services.database_service import conectar

def criar_item_catalogo(nome, preco):
    if not nome:
        return "Use assim: /catalog camiseta 35"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO catalogo (nome, preco) VALUES (?, ?)",
        (nome, preco)
    )

    conn.commit()
    conn.close()

    return f"🛍️ Item criado no catálogo: {nome} | R$ {preco:.2f}"

def listar_catalogo():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, preco
        FROM catalogo
        ORDER BY id DESC
        LIMIT 50
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Catálogo vazio."

    return "\n".join([
        f"#{id} - {nome} | R$ {preco:.2f}"
        for id, nome, preco in dados
    ])