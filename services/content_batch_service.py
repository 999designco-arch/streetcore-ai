from services.instagram_service import gerar_post_instagram, gerar_story, gerar_reels
from services.caption_service import gerar_legenda
from services.hashtag_service import gerar_hashtags

def gerar_pacote_conteudo(tema):
    if not tema:
        tema = "Street Graff"

    conteudos = []

    for i in range(1, 8):
        conteudos.append(
            f"🔥 CONTEÚDO {i}\n\n"
            f"{gerar_post_instagram(tema)}\n\n"
            f"{gerar_legenda(tema)}\n\n"
            f"{gerar_hashtags(tema)}"
        )

    return "\n\n====================\n\n".join(conteudos)

def gerar_pacote_reels(tema):
    if not tema:
        tema = "Street Graff"

    reels = []

    for i in range(1, 6):
        reels.append(
            f"🎬 REELS {i}\n\n"
            f"{gerar_reels(tema)}"
        )

    return "\n\n====================\n\n".join(reels)

def gerar_pacote_stories(tema):
    if not tema:
        tema = "Street Graff"

    stories = []

    for i in range(1, 6):
        stories.append(
            f"📲 STORY {i}\n\n"
            f"{gerar_story(tema)}"
        )

    return "\n\n====================\n\n".join(stories)