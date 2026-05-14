import os
import json
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from groq import Groq

# =========================================
# CONFIG
# =========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MEMORY_FILE = "memory.json"

# =========================================
# MASTER PROMPT
# =========================================

MASTER_PROMPT = """
Você é StreetCore AI.

Um agente de inteligência artificial executivo,
criativo, operacional e estratégico.

Você atua como:
- CEO;
- estrategista;
- diretor criativo premium;
- especialista em IA;
- engenheiro de automação;
- programador;
- growth hacker;
- operador pessoal.

Seu objetivo:
transformar qualquer ideia do usuário
em execução prática, inteligente,
automatizada e escalável.

REGRAS:
- sempre responda em português;
- explique passo a passo;
- aja como parceiro operacional;
- seja extremamente inteligente;
- pense em branding, dinheiro,
escala, automação e crescimento;
- use linguagem clara;
- dê soluções práticas;
- mantenha contexto do usuário;
- memorize informações importantes.

ESTILO:
- premium;
- futurista;
- executivo;
- criativo;
- cinematográfico;
- street luxury;
- cyberpunk minimalista.
"""

# =========================================
# MEMORY SYSTEM
# =========================================

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)

def auto_memory(user_message, memory):

    text = user_message.lower()

    # nome
    if "meu nome é" in text:
        try:
            nome = text.split("meu nome é")[1].strip()
            memory["nome"] = nome
        except:
            pass

    # objetivo
    if "quero criar" in text:
        try:
            objetivo = text.split("quero criar")[1].strip()
            memory["objetivo"] = objetivo
        except:
            pass

    # marca
    if "minha marca" in text:
        try:
            marca = text.split("minha marca")[1].strip()
            memory["marca"] = marca
        except:
            pass

    # nicho
    if "meu nicho é" in text:
        try:
            nicho = text.split("meu nicho é")[1].strip()
            memory["nicho"] = nicho
        except:
            pass

    memory["ultima_interacao"] = str(datetime.now())

    save_memory(memory)

# =========================================
# COMMANDS
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    welcome = """
🔥 StreetCore AI ONLINE

Seu agente executivo agora está ativo.

Capacidades:
✅ Estratégia
✅ Branding
✅ IA
✅ Automação
✅ Negócios
✅ Conteúdo
✅ Growth
✅ Programação
✅ Memória Inteligente

Comandos:

/memoria
/limparmemoria
/status
"""

    await update.message.reply_text(welcome)

# =========================================

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):

    memory = load_memory()

    if not memory:
        await update.message.reply_text(
            "Ainda não existem memórias salvas."
        )
        return

    text = "🧠 MEMÓRIAS ATUAIS:\n\n"

    for key, value in memory.items():
        text += f"• {key}: {value}\n"

    await update.message.reply_text(text)

# =========================================

async def limpar_memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):

    save_memory({})

    await update.message.reply_text(
        "Memória apagada com sucesso."
    )

# =========================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    memory = load_memory()

    status_text = f"""
🚀 STREETCORE AI STATUS

Sistema: ONLINE
IA: Groq
Memória: ATIVA
Perfil carregado: {len(memory)} itens
Modo: CEO EXECUTIVO
"""

    await update.message.reply_text(status_text)

# =========================================
# CHAT
# =========================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    memory = load_memory()

    # AUTO MEMORY
    auto_memory(user_message, memory)

    memory_text = json.dumps(
        memory,
        ensure_ascii=False,
        indent=2
    )

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content":
                MASTER_PROMPT +
                f"\n\nMEMÓRIA DO USUÁRIO:\n{memory_text}"
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.8,
        max_tokens=2000
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

# =========================================
# APP
# =========================================

app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("memoria", memoria))
app.add_handler(CommandHandler("limparmemoria", limpar_memoria))
app.add_handler(CommandHandler("status", status))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("🔥 StreetCore AI ONLINE")

app.run_polling()
