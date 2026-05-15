import os
import threading
import asyncio

from flask import Flask, jsonify

from telegram import Update

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from services.database_service import iniciar_banco

from services.analytics_service import (
    registrar_evento,
    resumo_analytics
)

from services.memory_service import (
    salvar_memoria,
    listar_memorias
)

from services.admin_service import painel_admin

from services.free_ai_service import resposta_free_ai

from services.task_service import (
    criar_tarefa,
    listar_tarefas
)

from services.log_service import (
    registrar_log,
    listar_logs
)

from services.scheduler_service import (
    executar_scheduler
)

TELEGRAM_TOKEN = os.getenv(
    "TELEGRAM_TOKEN"
)

if not TELEGRAM_TOKEN:
    raise ValueError(
        "TELEGRAM_TOKEN não encontrado."
    )

app = Flask(__name__)

iniciar_banco()

@app.route("/")
def home():

    return painel_admin()

@app.route("/health")
def health():

    return jsonify({
        "status": "online",
        "version": "StreetCore OS V15 FREE"
    })

@app.route("/analytics")
def analytics():

    return jsonify(
        resumo_analytics()
    )

@app.route("/logs")
def logs():

    return f"<pre>{listar_logs()}</pre>"

@app.route("/tasks")
def tasks():

    return f"<pre>{listar_tarefas()}</pre>"

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    registrar_evento("start")

    await update.message.reply_text(
        "🔥 STREETCORE OS V15 FREE\n\n"
        "NOVOS COMANDOS:\n"
        "/task criar campanha\n"
        "/tasks\n"
        "/logs\n"
        "/scheduler\n"
    )

async def task(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    nome = " ".join(
        context.args
    )

    if not nome:

        await update.message.reply_text(
            "Digite assim:\n"
            "/task criar campanha"
        )

        return

    registrar_evento("task")

    registrar_log(
        "TASK",
        nome
    )

    resposta = criar_tarefa(nome)

    await update.message.reply_text(
        resposta
    )

async def tasks_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        listar_tarefas()
    )

async def logs_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        listar_logs()
    )

async def scheduler_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        executar_scheduler()
    )

async def responder(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mensagem = update.message.text

    salvar_memoria(
        mensagem
    )

    registrar_evento(
        "mensagem"
    )

    registrar_log(
        "MSG",
        mensagem
    )

    resposta = resposta_free_ai(
        mensagem
    )

    await update.message.reply_text(
        resposta
    )

async def telegram_main():

    telegram_app = Application.builder().token(
        TELEGRAM_TOKEN
    ).build()

    telegram_app.add_handler(
        CommandHandler("start", start)
    )

    telegram_app.add_handler(
        CommandHandler("task", task)
    )

    telegram_app.add_handler(
        CommandHandler("tasks", tasks_cmd)
    )

    telegram_app.add_handler(
        CommandHandler("logs", logs_cmd)
    )

    telegram_app.add_handler(
        CommandHandler(
            "scheduler",
            scheduler_cmd
        )
    )

    telegram_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder
        )
    )

    print(
        "🔥 Telegram iniciando V15 FREE..."
    )

    await telegram_app.initialize()

    await telegram_app.start()

    await telegram_app.updater.start_polling()

    print(
        "✅ Telegram ONLINE V15 FREE"
    )

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