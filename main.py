import os
import threading
import asyncio

from flask import Flask, jsonify

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from services.database_service import iniciar_banco
from services.admin_service import painel_admin
from services.analytics_service import registrar_evento, resumo_analytics
from services.memory_service import salvar_memoria
from services.free_ai_service import resposta_free_ai

from services.task_service import criar_tarefa, listar_tarefas
from services.log_service import registrar_log, listar_logs
from services.scheduler_service import executar_scheduler

from services.report_service import gerar_relatorio
from services.calendar_service import criar_evento, listar_eventos
from services.client_service import criar_cliente, listar_clientes
from services.finance_service import adicionar_receita, adicionar_despesa, resumo_financeiro

from services.order_service import criar_pedido, listar_pedidos, atualizar_status_pedido
from services.quote_service import criar_orcamento, listar_orcamentos
from services.inventory_service import adicionar_estoque, listar_estoque
from services.notification_service import criar_notificacao, listar_notificacoes

from services.supplier_service import criar_fornecedor, listar_fornecedores
from services.production_service import criar_producao, listar_producao, atualizar_producao
from services.backup_service import criar_backup, listar_backups

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
        "version": "StreetCore OS V18 FREE"
    })

@app.route("/analytics")
def analytics():
    return jsonify(resumo_analytics())

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
def finance_page():
    return f"<pre>{resumo_financeiro()}</pre>"

@app.route("/orders")
def orders():
    return f"<pre>{listar_pedidos()}</pre>"

@app.route("/quotes")
def quotes():
    return f"<pre>{listar_orcamentos()}</pre>"

@app.route("/stock")
def stock_page():
    return f"<pre>{listar_estoque()}</pre>"

@app.route("/notifications")
def notifications():
    return f"<pre>{listar_notificacoes()}</pre>"

@app.route("/suppliers")
def suppliers():
    return f"<pre>{listar_fornecedores()}</pre>"

@app.route("/production")
def production_page():
    return f"<pre>{listar_producao()}</pre>"

@app.route("/backups")
def backups_page():
    return f"<pre>{listar_backups()}</pre>"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V18 FREE\n\n"
        "COMANDOS:\n"
        "/task criar campanha\n"
        "/tasks\n"
        "/logs\n"
        "/scheduler\n"
        "/client joao\n"
        "/clients\n"
        "/event live_hoje 20h\n"
        "/calendar\n"
        "/finance 100\n"
        "/expense 50\n"
        "/report\n"
        "/order pedido de camiseta\n"
        "/orders\n"
        "/orderstatus 1 em_producao\n"
        "/quote 10 camisetas personalizadas\n"
        "/quotes\n"
        "/stock camiseta 10\n"
        "/stocklist\n"
        "/notify novo pedido recebido\n"
        "/notifications\n"
        "/supplier fornecedor camisetas\n"
        "/suppliers\n"
        "/production camiseta cliente joao\n"
        "/productions\n"
        "/productionstatus 1 finalizado\n"
        "/backup\n"
        "/backups"
    )

async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    resposta = criar_tarefa(nome)
    registrar_log("TASK", nome)
    await update.message.reply_text(resposta)

async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_tarefas())

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_logs())

async def scheduler_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(executar_scheduler())

async def client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    await update.message.reply_text(criar_cliente(nome))

async def clients_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_clientes())

async def event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use:\n/event nome data")
        return

    nome = context.args[0]
    data = " ".join(context.args[1:])
    await update.message.reply_text(criar_evento(nome, data))

async def calendar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_eventos())

async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(resumo_financeiro())
        return

    try:
        valor = float(context.args[0].replace(",", "."))
        await update.message.reply_text(adicionar_receita(valor))
    except ValueError:
        await update.message.reply_text("Use assim: /finance 100")

async def expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use assim: /expense 50")
        return

    try:
        valor = float(context.args[0].replace(",", "."))
        await update.message.reply_text(adicionar_despesa(valor))
    except ValueError:
        await update.message.reply_text("Use assim: /expense 50")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_relatorio())

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    resposta = criar_pedido(nome)
    registrar_log("ORDER", nome)
    await update.message.reply_text(resposta)

async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_pedidos())

async def orderstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /orderstatus 1 em_producao")
        return

    pedido_id = context.args[0]
    status = " ".join(context.args[1:])
    await update.message.reply_text(atualizar_status_pedido(pedido_id, status))

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = " ".join(context.args)
    await update.message.reply_text(criar_orcamento(descricao))

async def quotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_orcamentos())

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /stock camiseta 10")
        return

    item = context.args[0]

    try:
        quantidade = int(context.args[1])
    except ValueError:
        await update.message.reply_text("A quantidade precisa ser número. Exemplo: /stock camiseta 10")
        return

    await update.message.reply_text(adicionar_estoque(item, quantidade))

async def stocklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_estoque())

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = " ".join(context.args)

    if not mensagem:
        await update.message.reply_text("Use assim: /notify novo pedido recebido")
        return

    await update.message.reply_text(criar_notificacao(mensagem))

async def notifications_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_notificacoes())

async def supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    await update.message.reply_text(criar_fornecedor(nome))

async def suppliers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_fornecedores())

async def production(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    await update.message.reply_text(criar_producao(nome))

async def productions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_producao())

async def productionstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /productionstatus 1 finalizado")
        return

    producao_id = context.args[0]
    status = " ".join(context.args[1:])
    await update.message.reply_text(atualizar_producao(producao_id, status))

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(criar_backup())

async def backups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_backups())

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = update.message.text
    salvar_memoria(mensagem)
    registrar_evento("mensagem")
    registrar_log("MSG", mensagem)
    resposta = resposta_free_ai(mensagem)
    await update.message.reply_text(resposta)

async def telegram_main():
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("task", task))
    telegram_app.add_handler(CommandHandler("tasks", tasks_cmd))
    telegram_app.add_handler(CommandHandler("logs", logs_cmd))
    telegram_app.add_handler(CommandHandler("scheduler", scheduler_cmd))
    telegram_app.add_handler(CommandHandler("client", client))
    telegram_app.add_handler(CommandHandler("clients", clients_cmd))
    telegram_app.add_handler(CommandHandler("event", event))
    telegram_app.add_handler(CommandHandler("calendar", calendar_cmd))
    telegram_app.add_handler(CommandHandler("finance", finance))
    telegram_app.add_handler(CommandHandler("expense", expense))
    telegram_app.add_handler(CommandHandler("report", report))
    telegram_app.add_handler(CommandHandler("order", order))
    telegram_app.add_handler(CommandHandler("orders", orders_cmd))
    telegram_app.add_handler(CommandHandler("orderstatus", orderstatus))
    telegram_app.add_handler(CommandHandler("quote", quote))
    telegram_app.add_handler(CommandHandler("quotes", quotes_cmd))
    telegram_app.add_handler(CommandHandler("stock", stock))
    telegram_app.add_handler(CommandHandler("stocklist", stocklist))
    telegram_app.add_handler(CommandHandler("notify", notify))
    telegram_app.add_handler(CommandHandler("notifications", notifications_cmd))
    telegram_app.add_handler(CommandHandler("supplier", supplier))
    telegram_app.add_handler(CommandHandler("suppliers", suppliers_cmd))
    telegram_app.add_handler(CommandHandler("production", production))
    telegram_app.add_handler(CommandHandler("productions", productions_cmd))
    telegram_app.add_handler(CommandHandler("productionstatus", productionstatus))
    telegram_app.add_handler(CommandHandler("backup", backup))
    telegram_app.add_handler(CommandHandler("backups", backups))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V18 FREE...")
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    print("✅ Telegram ONLINE V18 FREE")

    await asyncio.Event().wait()

def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())

threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)