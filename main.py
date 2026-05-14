import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

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

Responda sempre em português, com clareza e execução prática.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "StreetCore AI online com cérebro Groq. Pronto para executar suas ideias."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7,
        max_tokens=1200
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("StreetCore AI com Groq iniciado...")
app.run_polling()
