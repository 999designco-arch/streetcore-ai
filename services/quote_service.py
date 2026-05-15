from services.database_service import conectar

def criar_orcamento(descricao):
    if not descricao:
        return "Digite assim: /quote 10 camisetas personalizadas"

    conn = conectar()
    cursor = conn.cursor()

    valor_estimado = calcular_valor_simples(descricao)

    cursor.execute(
        "INSERT INTO orcamentos (descricao, valor_estimado) VALUES (?, ?)",
        (descricao, valor_estimado)
    )

    conn.commit()
    conn.close()

    return (
        f"🧾 Orçamento criado\n\n"
        f"Descrição: {descricao}\n"
        f"Valor estimado: R$ {valor_estimado:.2f}\n\n"
        "Esse valor é uma estimativa simples."
    )

def calcular_valor_simples(descricao):
    texto = descricao.lower()

    base = 35.0

    if "caneca" in texto:
        base = 30.0

    if "adesivo" in texto:
        base = 8.0

    if "panfleto" in texto:
        base = 80.0

    if "brinde" in texto:
        base = 20.0

    quantidade = 1

    for palavra in texto.split():
        if palavra.isdigit():
            quantidade = int(palavra)
            break

    return base * quantidade

def listar_orcamentos():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, descricao, valor_estimado, criado_em
        FROM orcamentos
        ORDER BY id DESC
        LIMIT 30
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhum orçamento encontrado."

    return "\n".join([
        f"#{id} - {descricao} | R$ {valor:.2f} ({data})"
        for id, descricao, valor, data in dados
    ])