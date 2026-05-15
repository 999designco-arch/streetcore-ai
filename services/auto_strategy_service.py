from services.campaign_service import gerar_campanha
from services.content_batch_service import gerar_pacote_conteudo
from services.planner_service import gerar_grade_conteudo
from services.sales_service import gerar_texto_venda
from services.hashtag_service import gerar_hashtags

def plano_automatico(tema):
    if not tema:
        tema = "Street Graff"

    return (
        f"🚀 PLANO AUTOMÁTICO ULTRA - {tema.upper()}\n\n"
        "1. CAMPANHA:\n"
        f"{gerar_campanha(tema)}\n\n"
        "2. PACOTE DE CONTEÚDO:\n"
        f"{gerar_pacote_conteudo(tema)}\n\n"
        "3. GRADE SEMANAL:\n"
        f"{gerar_grade_conteudo(tema)}\n\n"
        "4. COPY DE VENDA:\n"
        f"{gerar_texto_venda(tema)}\n\n"
        "5. HASHTAGS:\n"
        f"{gerar_hashtags(tema)}"
    )