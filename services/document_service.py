import os
from pypdf import PdfReader

def extrair_texto_txt(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return arquivo.read()
    except Exception:
        try:
            with open(caminho, "r", encoding="latin-1") as arquivo:
                return arquivo.read()
        except Exception:
            return ""

def extrair_texto_pdf(caminho):
    try:
        reader = PdfReader(caminho)
        textos = []

        for pagina in reader.pages:
            texto = pagina.extract_text()
            if texto:
                textos.append(texto)

        return "\n".join(textos)
    except Exception:
        return ""

def extrair_texto_documento(caminho):
    extensao = os.path.splitext(caminho)[1].lower()

    if extensao == ".txt":
        return extrair_texto_txt(caminho)

    if extensao == ".pdf":
        return extrair_texto_pdf(caminho)

    return ""