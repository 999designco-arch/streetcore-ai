from services.database_service import conectar

def registrar_evento(nome):
    conn = conectar()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO analytics (evento) VALUES (?)", (nome,))
    conn.commit()
    conn.close()
    return True

def resumo_analytics():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM analytics")
    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT evento, COUNT(*)
        FROM analytics
        GROUP BY evento
        ORDER BY COUNT(*) DESC
    """)
    eventos = cursor.fetchall()

    conn.close()

    return {
        "versao": "V14 FREE",
        "total_eventos": total,
        "eventos": {nome: quantidade for nome, quantidade in eventos},
        "status": "analytics persistente ativo"
    }