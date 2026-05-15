import os
import threading
import asyncio

from flask import Flask, jsonify, request

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from services.database_service import iniciar_banco
from services.analytics_service import registrar_evento, resumo_analytics
from services.memory_service import salvar_memoria, listar_memorias

from services.instagram_service import (
    gerar_post_instagram,
    gerar_story,
    gerar_reels
)

from services.video_service import gerar_roteiro_video
from services.image_service import gerar_prompt_imagem
from services.sales_service import gerar_texto_venda
from services.campaign_service import gerar_campanha
from services.workflow_service import executar_workflow

from services.caption_service import gerar_legenda
from services.hashtag_service import gerar_hashtags
from services.planner_service import gerar_grade_conteudo

from services.product_service import listar_produtos
from services.agent_service import agentes_conversando
from services.admin_service import painel_admin

from services.free_ai_service import resposta_free_ai

from services.file_service import (
    salvar_arquivo,
    listar_arquivos
)

from services.knowledge_service import (
    adicionar_conhecimento,
    buscar_conhecimento
)

from services.ceo_service import modo_ceo
from services.copilot_service import copiloto_operacional
from services.prompt_service import listar_prompts

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)

iniciar_banco()

@app.route("/")
def home():
    return painel_admin()

@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "version": "StreetCore OS V13 FREE",
        "modo": "100% gratuito"
    })

@app.route("/analytics")
def analytics():
    return jsonify(resumo_analytics())

@app.route("/memory")
def memory():
    return jsonify({
        "memorias": listar_memorias()
    })

@app.route("/knowledge")
def knowledge():
    return jsonify({
        "knowledge": buscar_conhecimento()
    })

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🔥 STREETCORE OS V13 FREE\n\n"
        "NOVOS COMANDOS:\n"
        "/ceo\n"
        "/copilot\n"
        "/prompts\n"
        "/knowledge\n"
        "/files\n"
    )

async def ceo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    pergunta = " ".join(context.args)

    resposta = modo_ceo(pergunta)

    await update.message.reply_text(resposta)

async def copilot(update: Update, context: ContextTypes.DEFAULT_TYPE):

    comando = " ".join(context.args)

    resposta = copiloto_operacional(comando)

    await update.message.reply_text(resposta)

async def prompts(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        listar_prompts()
    )

async def knowledge(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = " ".join(context.args)

    adicionar_conhecimento(texto)

    await update.message.reply_text(
        "✅ Conhecimento salvo."
    )

async def files(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        listar_arquivos()
    )

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensagem = update.message.text

    salvar_memoria(mensagem)

    resposta = resposta_free_ai(mensagem)

    await update.message.reply_text(resposta)

async def telegram_main():

    telegram_app = Application.builder().token(
        TELEGRAM_TOKEN
    ).build()

    telegram_app.add_handler(
        CommandHandler("start", start)
    )

    telegram_app.add_handler(
        CommandHandler("ceo", ceo)
    )

    telegram_app.add_handler(
        CommandHandler("copilot", copilot)
    )

    telegram_app.add_handler(
        CommandHandler("prompts", prompts)
    )

    telegram_app.add_handler(
        CommandHandler("knowledge", knowledge)
    )

    telegram_app.add_handler(
        CommandHandler("files", files)
    )

    telegram_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder
        )
    )

    print("🔥 Telegram iniciando V13 FREE...")

    await telegram_app.initialize()

    await telegram_app.start()

    await telegram_app.updater.start_polling()

    print("✅ Telegram ONLINE V13 FREE")

    await asyncio.Event().wait()

def run_telegram():

    loop = asyncio.new_event_loop()

    asyncio.set_event_loop(loop)

    loop.run_until_complete(
        telegram_main()
    )

threading.Thread(
    target=run_telegram,
    daemon=True
).start()

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", 8080)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )