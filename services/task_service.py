from services.database_service import conectar

def criar_tarefa(nome):

    conn = conectar()

    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tarefas (nome, status) VALUES (?, ?)",
        (nome, "pendente")
    )

    conn.commit()
    conn.close()

    return f"✅ Tarefa criada: {nome}"

def listar_tarefas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, nome, status
        FROM tarefas
        ORDER BY id DESC
    """)

    tarefas = cursor.fetchall()

    conn.close()

    if not tarefas:
        return "Nenhuma tarefa encontrada."

    resultado = []

    for tarefa in tarefas:

        resultado.append(
            f"#{tarefa[0]} - {tarefa[1]} [{tarefa[2]}]"
        )

    return "\n".join(resultado)