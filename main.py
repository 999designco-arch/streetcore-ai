import os
import threading
import asyncio
from flask import Flask, jsonify, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from services.database_service import iniciar_banco
from services.ai_service import gerar_resposta_ia
from services.instagram_service import gerar_post_instagram, gerar_story, gerar_reels
from services.image_service import gerar_prompt_imagem
from services.video_service import gerar_roteiro_video
from services.memory_service import salvar_memoria, listar_memorias
from services.analytics_service import registrar_evento, resumo_analytics
from services.workflow_service import executar_workflow
from services.sales_service import gerar_texto_venda
from services.campaign_service import gerar_campanha
from services.product_service import listar_produtos
from services.admin_service import painel_admin
from services.agent_service import agentes_conversando
from services.planner_service import gerar_grade_conteudo
from services.hashtag_service import gerar_hashtags
from services.caption_service import gerar_legenda
from services.free_ai_service import resposta_free_ai

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
        "version": "StreetCore OS V12 FREE",
        "telegram": "ativo",
        "flask": "ativo",
        "railway": "ativo",
        "modo": "100% gratuito"
    })

@app.route("/analytics")
def analytics():
    return jsonify(resumo_analytics())

@app.route("/memory")
def memory():
    return jsonify({"memorias": listar_memorias()})

@app.route("/api/workflow", methods=["POST"])
def api_workflow():
    data = request.json or {}
    tema = data.get("tema", "Street Graff")
    return jsonify({"resultado": executar_workflow(tema)})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registrar_evento("start")
    await update.message.reply_text(
        "🔥 STREETCORE OS V12 FREE ONLINE\n\n"
        "Comandos:\n"
        "/status\n"
        "/post camisetas\n"
        "/story adesivos\n"
        "/reels canecas\n"
        "/video street graff\n"
        "/imagem camiseta personalizada\n"
        "/venda adesivos\n"
        "/campanha street graff\n"
        "/workflow street graff\n"
        "/legenda canecas\n"
        "/hashtags camisetas\n"
        "/grade street graff\n"
        "/produtos\n"
        "/agentes campanha\n"
        "/memoria\n"
        "/analytics\n\n"
        "Modo: 100% grátis."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ STREETCORE OS V12 FREE ATIVO\n"
        "✅ Telegram online\n"
        "✅ Flask online\n"
        "✅ Railway online\n"
        "✅ Banco SQLite grátis ativo\n"
        "✅ Memória persistente simples ativa\n"
        "✅ Analytics persistente ativo\n"
        "✅ Gerador de conteúdo ativo"
    )

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("post")
    await update.message.reply_text(gerar_post_instagram(tema))

async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("story")
    await update.message.reply_text(gerar_story(tema))

async def reels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("reels")
    await update.message.reply_text(gerar_reels(tema))

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("video")
    await update.message.reply_text(gerar_roteiro_video(tema))

async def imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("imagem")
    await update.message.reply_text(gerar_prompt_imagem(tema))

async def venda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("venda")
    await update.message.reply_text(gerar_texto_venda(tema))

async def campanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("campanha")
    await update.message.reply_text(gerar_campanha(tema))

async def workflow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("workflow")
    await update.message.reply_text(executar_workflow(tema))

async def legenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("legenda")
    await update.message.reply_text(gerar_legenda(tema))

async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("hashtags")
    await update.message.reply_text(gerar_hashtags(tema))

async def grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("grade")
    await update.message.reply_text(gerar_grade_conteudo(tema))

async def produtos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registrar_evento("produtos")
    await update.message.reply_text(listar_produtos())

async def agentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "campanha Street Graff"
    registrar_evento("agentes")
    await update.message.reply_text(agentes_conversando(tema))

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🧠 MEMÓRIA:\n\n{listar_memorias()}")

async def analytics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 ANALYTICS:\n\n{resumo_analytics()}")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = update.message.text
    salvar_memoria(mensagem)
    registrar_evento("mensagem")
    resposta = resposta_free_ai(mensagem)
    await update.message.reply_text(resposta)

async def telegram_main():
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("status", status))
    telegram_app.add_handler(CommandHandler("post", post))
    telegram_app.add_handler(CommandHandler("story", story))
    telegram_app.add_handler(CommandHandler("reels", reels))
    telegram_app.add_handler(CommandHandler("video", video))
    telegram_app.add_handler(CommandHandler("imagem", imagem))
    telegram_app.add_handler(CommandHandler("venda", venda))
    telegram_app.add_handler(CommandHandler("campanha", campanha))
    telegram_app.add_handler(CommandHandler("workflow", workflow))
    telegram_app.add_handler(CommandHandler("legenda", legenda))
    telegram_app.add_handler(CommandHandler("hashtags", hashtags))
    telegram_app.add_handler(CommandHandler("grade", grade))
    telegram_app.add_handler(CommandHandler("produtos", produtos))
    telegram_app.add_handler(CommandHandler("agentes", agentes))
    telegram_app.add_handler(CommandHandler("memoria", memoria))
    telegram_app.add_handler(CommandHandler("analytics", analytics_cmd))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V12 FREE...")
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    print("✅ Telegram ONLINE V12 FREE")
    await asyncio.Event().wait()

def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())

threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)