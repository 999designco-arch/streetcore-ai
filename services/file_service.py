import os

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def salvar_arquivo(nome, conteudo):

    caminho = os.path.join(
        UPLOAD_FOLDER,
        nome
    )

    with open(
        caminho,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(conteudo)

    return f"✅ Arquivo salvo em {caminho}"

def listar_arquivos():

    arquivos = os.listdir(
        UPLOAD_FOLDER
    )

    if not arquivos:
        return "Nenhum arquivo encontrado."

    return "\n".join(arquivos)