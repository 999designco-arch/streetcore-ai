import os
import re

UPLOAD_FOLDER = "uploads"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def limpar_nome(nome):
    nome = nome.replace(" ", "_")
    nome = re.sub(r"[^a-zA-Z0-9_.-]", "", nome)
    return nome or "arquivo"

async def salvar_arquivo_telegram(telegram_file, nome):
    nome_limpo = limpar_nome(nome)
    caminho = os.path.join(UPLOAD_FOLDER, nome_limpo)

    await telegram_file.download_to_drive(caminho)

    return caminho

def listar_arquivos():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    arquivos = os.listdir(UPLOAD_FOLDER)

    if not arquivos:
        return "Nenhum arquivo encontrado."

    return "\n".join(arquivos)