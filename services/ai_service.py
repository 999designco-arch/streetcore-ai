def gerar_resposta_ia(mensagem):
    texto = mensagem.lower()

    if "post" in texto:
        return "Use /post seguido do tema. Exemplo: /post camisetas personalizadas"

    if "video" in texto or "vídeo" in texto:
        return "Use /video seguido do tema. Exemplo: /video anúncio de canecas"

    if "vender" in texto or "venda" in texto:
        return "Use /venda seguido do produto. Exemplo: /venda adesivos personalizados"

    if "campanha" in texto:
        return "Use /campanha seguido do tema. Exemplo: /campanha brindes para empresas"

    return (
        "🤖 STREETCORE IA V11\n\n"
        f"Recebi: {mensagem}\n\n"
        "Posso te ajudar com:\n"
        "✅ posts\n"
        "✅ stories\n"
        "✅ reels\n"
        "✅ vendas\n"
        "✅ campanhas\n"
        "✅ imagens\n"
        "✅ vídeos\n"
        "✅ workflows\n\n"
        "Digite /start para ver os comandos."
    )