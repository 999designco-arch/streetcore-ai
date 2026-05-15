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
from services.admin_service import painel_admin
from services.analytics_service import (
    registrar_evento,
    resumo_analytics
)
from services.memory_service import (
    salvar_memoria
)
from services.free_ai_service import (
    resposta_free_ai
)

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

from services.report_service import (
    gerar_relatorio
)

from services.calendar_service import (
    criar_evento,
    listar_eventos
)

from services.client_service import (
    criar_cliente,
    listar_clientes
)

from services.finance_service import (
    adicionar_receita,
    resumo_financeiro
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
        "version": "StreetCore OS V16 FREE"
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

@app.route("/clients")
def clients():

    return f"<pre>{listar_clientes()}</pre>"

@app.route("/calendar")
def calendar():

    return f"<pre>{listar_eventos()}</pre>"

@app.route("/finance")
def finance():

    return f"<pre>{resumo_financeiro()}</pre>"

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "🔥 STREETCORE OS V16 FREE\n\n"
        "NOVOS COMANDOS:\n"
        "/task criar campanha\n"
        "/tasks\n"
        "/logs\n"
        "/scheduler\n"
        "/client joao\n"
        "/clients\n"
        "/event live_hoje 20h\n"
        "/calendar\n"
        "/finance 100\n"
        "/report\n"
    )

async def task(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    nome = " ".join(
        context.args
    )

    resposta = criar_tarefa(
        nome
    )

    registrar_log(
        "TASK",
        nome
    )

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

async def client(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    nome = " ".join(
        context.args
    )

    resposta = criar_cliente(
        nome
    )

    await update.message.reply_text(
        resposta
    )

async def clients_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        listar_clientes()
    )

async def event(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if len(context.args) < 2:

        await update.message.reply_text(
            "Use:\n/event nome data"
        )

        return

    nome = context.args[0]

    data = " ".join(
        context.args[1:]
    )

    resposta = criar_evento(
        nome,
        data
    )

    await update.message.reply_text(
        resposta
    )

async def calendar_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        listar_eventos()
    )

async def finance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not context.args:

        await update.message.reply_text(
            resumo_financeiro()
        )

        return

    valor = float(
        context.args[0]
    )

    resposta = adicionar_receita(
        valor
    )

    await update.message.reply_text(
        resposta
    )

async def report(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        gerar_relatorio()
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
        CommandHandler(
            "client",
            client
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "clients",
            clients_cmd
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "event",
            event
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "calendar",
            calendar_cmd
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "finance",
            finance
        )
    )

    telegram_app.add_handler(
        CommandHandler(
            "report",
            report
        )
    )

    telegram_app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            responder
        )
    )

    print(
        "🔥 Telegram iniciando V16 FREE..."
    )

    await telegram_app.initialize()

    await telegram_app.start()

    await telegram_app.updater.start_polling()

    print(
        "✅ Telegram ONLINE V16 FREE"
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