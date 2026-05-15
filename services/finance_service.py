from services.database_service import conectar

def adicionar_receita(valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO financeiro (tipo, valor) VALUES (?, ?)",
        ("receita", valor)
    )

    conn.commit()
    conn.close()

    return f"💰 Receita adicionada: R$ {valor:.2f}"

def adicionar_despesa(valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO financeiro (tipo, valor) VALUES (?, ?)",
        ("despesa", valor)
    )

    conn.commit()
    conn.close()

    return f"💸 Despesa adicionada: R$ {valor:.2f}"

def resumo_financeiro():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'")
    receita = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'")
    despesa = cursor.fetchone()[0] or 0

    lucro = receita - despesa

    conn.close()

    return (
        "💵 FINANCEIRO V18\n\n"
        f"Receita total: R$ {receita:.2f}\n"
        f"Despesa total: R$ {despesa:.2f}\n"
        f"Lucro estimado: R$ {lucro:.2f}"
    )