prompts = {

    "instagram":
    "Crie post viral para Instagram.",

    "reels":
    "Crie reels curto viral.",

    "story":
    "Crie sequência de stories.",

    "venda":
    "Crie copy agressiva."
}

def listar_prompts():

    resultado = []

    for nome, texto in prompts.items():

        resultado.append(
            f"{nome}: {texto}"
        )

    return "\n\n".join(resultado)