import os
import shutil
from datetime import datetime

DB_PATH = "streetcore.db"
BACKUP_FOLDER = "backups"

def criar_backup():
    if not os.path.exists(DB_PATH):
        return "Banco de dados ainda não existe."

    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)

    data = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = os.path.join(BACKUP_FOLDER, f"streetcore_backup_{data}.db")

    shutil.copy(DB_PATH, destino)

    return f"✅ Backup criado: {destino}"

def listar_backups():
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)

    arquivos = os.listdir(BACKUP_FOLDER)

    if not arquivos:
        return "Nenhum backup encontrado."

    return "\n".join(arquivos[-20:])