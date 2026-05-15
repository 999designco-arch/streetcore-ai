from services.instagram_service import gerar_post_instagram
from services.video_service import gerar_roteiro_video
from services.image_service import gerar_prompt_imagem

def executar_workflow(tema):
    post = gerar_post_instagram(tema)
    video = gerar_roteiro_video(tema)
    imagem = gerar_prompt_imagem(tema)

    return (
        "🚀 WORKFLOW COMPLETO GERADO\n\n"
        f"{post}\n\n"
        "-------------------\n\n"
        f"{video}\n\n"
        "-------------------\n\n"
        f"{imagem}"
    )