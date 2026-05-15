from services.database_service import conectar

def registrar_kpi(nome, valor):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO kpis (nome, valor) VALUES (?, ?)",
        (nome, valor)
    )

    conn.commit()
    conn.close()

    return f"📈 KPI registrado: {nome} = {valor}"

def listar_kpis():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT nome, valor, criado_em
        FROM kpis
        ORDER BY id DESC
        LIMIT 50
    """)

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return "Nenhum KPI registrado."

    return "\n".join([
        f"{nome}: {valor} ({data})"
        for nome, valor, data in dados
    ])