from services.database_service import conectar

def criar_producao(nome):
    if not nome:
        return "Use assim: /production camiseta cliente joao"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO producao (nome, status) VALUES (?, ?)",
        (nome, "aguardando")
    )

    conn.commit()
    conn.close()

    return f"🏗️ Produção criada: {nome}"

def listar_producao():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, status, criado_em
        FROM producao
        ORDER BY id DESC
        LIMIT 30
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhuma produção encontrada."

    return "\n".join([
        f"#{id} - {nome} [{status}] ({data})"
        for id, nome, status, data in dados
    ])

def atualizar_producao(producao_id, status):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE producao SET status=? WHERE id=?",
        (status, producao_id)
    )

    conn.commit()
    conn.close()

    return f"✅ Produção #{producao_id} atualizada para: {status}"