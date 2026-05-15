from services.instagram_service import gerar_post_instagram, gerar_story, gerar_reels
from services.video_service import gerar_roteiro_video
from services.image_service import gerar_prompt_imagem
from services.sales_service import gerar_texto_venda

def executar_workflow(tema):
    return (
        f"🚀 WORKFLOW V11 - {tema.upper()}\n\n"
        "✅ POST GERADO:\n"
        f"{gerar_post_instagram(tema)}\n\n"
        "-------------------\n\n"
        "✅ STORY GERADO:\n"
        f"{gerar_story(tema)}\n\n"
        "-------------------\n\n"
        "✅ REELS GERADO:\n"
        f"{gerar_reels(tema)}\n\n"
        "-------------------\n\n"
        "✅ ROTEIRO DE VÍDEO:\n"
        f"{gerar_roteiro_video(tema)}\n\n"
        "-------------------\n\n"
        "✅ PROMPT DE IMAGEM:\n"
        f"{gerar_prompt_imagem(tema)}\n\n"
        "-------------------\n\n"
        "✅ TEXTO DE VENDA:\n"
        f"{gerar_texto_venda(tema)}"
    )