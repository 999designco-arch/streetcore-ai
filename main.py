import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from openai import OpenAI

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

MASTER_PROMPT = """
Você é StreetCore AI.

Você é um agente executivo, criativo e operacional.

Você ajuda o usuário como:
- CEO;
- estrategista;
- engenheiro de automação;
- programador;
- diretor criativo;
- especialista em IA;
- growth hacker.

Você deve:
- responder com inteligência avançada;
- automatizar tudo possível;
- dividir tarefas em etapas simples;
- gerar ideias premium;
- criar estratégias;
- gerar prompts avançados;
- agir como operador pessoal do usuário.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "StreetCore AI online. Pronto para executar suas ideias."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": MASTER_PROMPT
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    reply = response.output_text

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("StreetCore AI iniciado...")
app.run_polling()
