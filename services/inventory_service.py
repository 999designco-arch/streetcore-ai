from services.database_service import conectar

def adicionar_estoque(item, quantidade):
    if not item:
        return "Digite assim: /stock camiseta 10"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO estoque (item, quantidade) VALUES (?, ?)",
        (item, quantidade)
    )

    conn.commit()
    conn.close()

    return f"📦 Estoque adicionado: {item} | Quantidade: {quantidade}"

def listar_estoque():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT item, SUM(quantidade)
        FROM estoque
        GROUP BY item
        ORDER BY item
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhum item no estoque."

    return "\n".join([
        f"{item}: {quantidade}"
        for item, quantidade in dados
    ])