from services.database_service import conectar

def criar_fornecedor(nome):
    if not nome:
        return "Use assim: /supplier fornecedor camisetas"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO fornecedores (nome) VALUES (?)",
        (nome,)
    )

    conn.commit()
    conn.close()

    return f"🏭 Fornecedor criado: {nome}"

def listar_fornecedores():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, criado_em
        FROM fornecedores
        ORDER BY id DESC
        LIMIT 30
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhum fornecedor encontrado."

    return "\n".join([
        f"#{id} - {nome} ({data})"
        for id, nome, data in dados
    ])