from services.database_service import conectar

def criar_etapa(nome):
    if not nome:
        return "Use assim: /stage orçamento_enviado"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO pipeline (nome) VALUES (?)",
        (nome,)
    )

    conn.commit()
    conn.close()

    return f"🧩 Etapa criada: {nome}"

def listar_pipeline():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, criado_em
        FROM pipeline
        ORDER BY id DESC
        LIMIT 50
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhuma etapa de pipeline encontrada."

    return "\n".join([
        f"#{id} - {nome} ({data})"
        for id, nome, data in dados
    ])