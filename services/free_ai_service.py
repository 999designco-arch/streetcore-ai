from services.ai_service import gerar_resposta_ia
from services.instagram_service import gerar_post_instagram
from services.video_service import gerar_roteiro_video
from services.sales_service import gerar_texto_venda
from services.campaign_service import gerar_campanha

def resposta_free_ai(mensagem):
    texto = mensagem.lower()

    if "post" in texto:
        return gerar_post_instagram(mensagem)

    if "vídeo" in texto or "video" in texto:
        return gerar_roteiro_video(mensagem)

    if "venda" in texto or "vender" in texto:
        return gerar_texto_venda(mensagem)

    if "campanha" in texto:
        return gerar_campanha(mensagem)

    return gerar_resposta_ia(mensagem)