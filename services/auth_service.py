import os
import secrets

API_KEY = os.getenv(
    "STREETCORE_API_KEY",
    secrets.token_hex(16)
)

usuarios = {
    "admin": {
        "senha": "streetcore",
        "nivel": "admin"
    }
}

def autenticar(usuario, senha):

    dados = usuarios.get(usuario)

    if not dados:
        return False

    return dados["senha"] == senha

def validar_api_key(chave):

    return chave == API_KEY

def obter_api_key():

    return API_KEY