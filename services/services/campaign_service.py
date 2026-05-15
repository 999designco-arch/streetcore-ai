from services.instagram_service import gerar_post_instagram, gerar_story, gerar_reels
from services.video_service import gerar_roteiro_video
from services.sales_service import gerar_texto_venda

def gerar_campanha(tema):
    return (
        f"🚀 CAMPANHA COMPLETA - {tema.upper()}\n\n"
        "1. POST:\n"
        f"{gerar_post_instagram(tema)}\n\n"
        "2. STORY:\n"
        f"{gerar_story(tema)}\n\n"
        "3. REELS:\n"
        f"{gerar_reels(tema)}\n\n"
        "4. ROTEIRO:\n"
        f"{gerar_roteiro_video(tema)}\n\n"
        "5. TEXTO DE VENDA:\n"
        f"{gerar_texto_venda(tema)}"
    )