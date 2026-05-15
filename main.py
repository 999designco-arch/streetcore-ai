import os
import threading
from flask import Flask, jsonify, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from services.ai_service import gerar_resposta_ia
from services.instagram_service import gerar_post_instagram, gerar_story, gerar_reels
from services.image_service import gerar_prompt_imagem
from services.video_service import gerar_roteiro_video
from services.memory_service import salvar_memoria, listar_memorias
from services.analytics_service import registrar_evento, resumo_analytics
from services.automation_service import criar_automacao
from services.workflow_service import executar_workflow
from services.database_service import iniciar_banco
from services.sales_service import gerar_texto_venda
from services.campaign_service import gerar_campanha
from services.product_service import listar_produtos
from services.admin_service import painel_admin
from services.agent_service import agentes_conversando

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

web = Flask(__name__)

iniciar_banco()

@web.route("/")
def home():
    return painel_admin()

@web.route("/health")
def health():
    return jsonify({
        "status": "online",
        "version": "V11",
        "telegram": "ativo",
        "flask": "ativo",
        "services": "ativos"
    })

@web.route("/analytics")
def analytics():
    return jsonify(resumo_analytics())

@web.route("/memory")
def memory():
    return jsonify({"memorias": listar_memorias()})

@web.route("/api/workflow", methods=["POST"])
def api_workflow():
    data = request.json or {}
    tema = data.get("tema", "Street Graff")
    return jsonify({"resultado": executar_workflow(tema)})

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registrar_evento("start")
    await update.message.reply_text(
        "🔥 STREETCORE OS V11 ONLINE\n\n"
        "Comandos:\n"
        "/post - criar post\n"
        "/story - criar story\n"
        "/reels - criar reels\n"
        "/video - roteiro de vídeo\n"
        "/imagem - prompt de imagem\n"
        "/venda - texto de venda\n"
        "/campanha - campanha completa\n"
        "/produtos - lista produtos\n"
        "/agentes - agentes IA conversando\n"
        "/workflow - workflow completo\n"
        "/memoria - ver memória\n"
        "/analytics - ver analytics\n"
        "/status - status"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ STREETCORE OS V11 ATIVO\n"
        "✅ Telegram online\n"
        "✅ Flask online\n"
        "✅ Services conectados\n"
        "✅ IA operacional\n"
        "✅ Workflow ativo\n"
        "✅ Analytics ativo\n"
        "✅ Memória simples ativa"
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

async def produtos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    registrar_evento("produtos")
    await update.message.reply_text(listar_produtos())

async def agentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "campanha Street Graff"
    registrar_evento("agentes")
    await update.message.reply_text(agentes_conversando(tema))

async def workflow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    registrar_evento("workflow")
    await update.message.reply_text(executar_workflow(tema))

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🧠 MEMÓRIA:\n\n{listar_memorias()}")

async def analytics_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 ANALYTICS:\n\n{resumo_analytics()}")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = update.message.text
    salvar_memoria(mensagem)
    registrar_evento("mensagem")
    await update.message.reply_text(gerar_resposta_ia(mensagem))

def run_flask():
    port = int(os.getenv("PORT", 8080))
    web.run(host="0.0.0.0", port=port)

def run_telegram():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("post", post))
    app.add_handler(CommandHandler("story", story))
    app.add_handler(CommandHandler("reels", reels))
    app.add_handler(CommandHandler("video", video))
    app.add_handler(CommandHandler("imagem", imagem))
    app.add_handler(CommandHandler("venda", venda))
    app.add_handler(CommandHandler("campanha", campanha))
    app.add_handler(CommandHandler("produtos", produtos))
    app.add_handler(CommandHandler("agentes", agentes))
    app.add_handler(CommandHandler("workflow", workflow))
    app.add_handler(CommandHandler("memoria", memoria))
    app.add_handler(CommandHandler("analytics", analytics_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    app.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_telegram, daemon=True).start()
    run_flask()