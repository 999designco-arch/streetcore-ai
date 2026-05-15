from services.hashtag_service import gerar_hashtags

def gerar_legenda(tema):
    return (
        f"📝 LEGENDA PRONTA - {tema.upper()}\n\n"
        "Sua marca merece aparecer com identidade.\n\n"
        "Na Street Graff, sua ideia vira produto personalizado com estilo, presença e qualidade.\n\n"
        "📲 Chama no direct e peça seu orçamento.\n"
        "Pagamento via PIX.\n\n"
        f"{gerar_hashtags(tema)}"
    )