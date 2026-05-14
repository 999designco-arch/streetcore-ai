import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MEMORY_FILE = "memory.json"

MASTER_PROMPT = """
Você é StreetCore AI, um agente executivo, criativo e operacional.

Você atua como:
- CEO estratégico;
- diretor criativo premium;
- engenheiro de automação;
- programador;
- especialista em IA;
- growth hacker;
- operador pessoal do usuário.

Você sempre responde em português.

Regras:
- seja prático;
- explique passo a passo;
- aja como se estivesse pegando na mão do usuário;
- memorize preferências importantes;
- transforme ideias em execução;
- sugira automações;
- pense em escala, dinheiro, marca e produtividade.
"""

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "StreetCore AI online com memória inicial. Pronto para evoluir com você."
    )

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    if not memory:
        await update.message.reply_text("Ainda não tenho memórias salvas.")
        return

    text = "Minhas memórias atuais:\n\n"
    for key, value in memory.items():
        text += f"- {key}: {value}\n"

    await update.message.reply_text(text)

async def lembrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)

    if "=" not in text:
        await update.message.reply_text(
            "Use assim:\n/lembrar nome = Street Graff"
        )
        return

    key, value = text.split("=", 1)
    key = key.strip()
    value = value.strip()

    memory = load_memory()
    memory[key] = value
    save_memory(memory)

    await update.message.reply_text(f"Memória salva: {key} = {value}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    memory = load_memory()

    memory_text = json.dumps(memory, ensure_ascii=False, indent=2)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": MASTER_PROMPT + f"\n\nMemórias salvas do usuário:\n{memory_text}"
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.7,
        max_tokens=1500
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("memoria", memoria))
app.add_handler(CommandHandler("lembrar", lembrar))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("StreetCore AI com memória iniciado...")
app.run_polling()
