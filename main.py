import os
import json
import urllib.parse
from datetime import datetime

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MEMORY_FILE = "memory.json"

MASTER_PROMPT = """
Você é StreetCore AI, um agente executivo, criativo e operacional.
Responda sempre em português.
Use apenas ferramentas gratuitas ou com plano grátis como padrão.
Aja como CEO, estrategista, diretor criativo, programador, automação e growth hacker.
Explique passo a passo, como se estivesse pegando na mão do usuário.
"""

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

    if "meu nome é" in text:
        memory["nome"] = text.split("meu nome é")[1].strip()

    if "quero criar" in text:
        memory["objetivo"] = text.split("quero criar")[1].strip()

    if "minha marca é" in text:
        memory["marca"] = text.split("minha marca é")[1].strip()

    memory["ultima_interacao"] = str(datetime.now())
    save_memory(memory)

def gerar_url_imagem(prompt):
    prompt_premium = f"""
    ultra realistic cinematic image, street luxury, futuristic premium design,
    cyberpunk executive aesthetic, dramatic lighting, 8k, highly detailed,
    global luxury brand campaign style. Theme: {prompt}
    """

    encoded_prompt = urllib.parse.quote(prompt_premium)
    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed=777"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 StreetCore AI ONLINE

Funções:
✅ IA com Groq grátis
✅ Memória
✅ Geração de imagem grátis
✅ Modo CEO
✅ Branding
✅ Estratégia

Comandos:
/status
/memoria
/imagem descrição
/limparmemoria
""")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🚀 STATUS

Sistema: ONLINE
IA: Groq
Imagem: Pollinations grátis
Memória: ATIVA
Modo: CEO EXECUTIVO
""")

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()

    if not memory:
        await update.message.reply_text("Nenhuma memória salva ainda.")
        return

    text = "🧠 MEMÓRIAS:\n\n"
    for key, value in memory.items():
        text += f"• {key}: {value}\n"

    await update.message.reply_text(text)

async def limpar_memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_memory({})
    await update.message.reply_text("Memória apagada com sucesso.")

async def imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text("Use assim:\n/imagem carro futurista neon")
        return

    await update.message.reply_text("🎨 Gerando imagem gratuita...")

    image_url = gerar_url_imagem(prompt)

    await update.message.reply_photo(photo=image_url)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    memory = load_memory()
    auto_memory(user_message, memory)

    memory_text = json.dumps(memory, ensure_ascii=False, indent=2)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": MASTER_PROMPT + f"\n\nMEMÓRIA DO USUÁRIO:\n{memory_text}"
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

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("memoria", memoria))
app.add_handler(CommandHandler("limparmemoria", limpar_memoria))
app.add_handler(CommandHandler("imagem", imagem))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 StreetCore AI com imagem grátis ONLINE")
app.run_polling()
