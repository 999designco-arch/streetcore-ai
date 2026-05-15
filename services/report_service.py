from services.analytics_service import resumo_analytics
from services.task_service import listar_tarefas

def gerar_relatorio():

    analytics = resumo_analytics()

    tarefas = listar_tarefas()

    return (
        "📊 RELATÓRIO OPERACIONAL\n\n"
        f"Analytics:\n{analytics}\n\n"
        f"Tarefas:\n{tarefas}\n\n"
        "Sistema operacional funcionando."
    )