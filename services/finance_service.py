from services.database_service import conectar

def adicionar_receita(valor):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO financeiro (
            tipo,
            valor
        )
        VALUES (?, ?)
        """,
        ("receita", valor)
    )

    conn.commit()

    conn.close()

    return f"💰 Receita adicionada: R$ {valor}"

def resumo_financeiro():

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT SUM(valor)
        FROM financeiro
        WHERE tipo='receita'
    """)

    receita = cursor.fetchone()[0]

    receita = receita or 0

    conn.close()

    return (
        "💵 FINANCEIRO\n\n"
        f"Receita total: R$ {receita}"
    )