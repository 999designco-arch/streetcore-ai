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

from services.lead_service import criar_lead, listar_leads, atualizar_lead
from services.pipeline_service import criar_etapa, listar_pipeline
from services.catalog_service import criar_item_catalogo, listar_catalogo
from services.content_batch_service import gerar_pacote_conteudo, gerar_pacote_reels, gerar_pacote_stories

from services.instagram_service import gerar_post_instagram, gerar_story, gerar_reels
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

from services.brain_service import cerebro_operacional
from services.goal_service import criar_meta, listar_metas, atualizar_meta
from services.kpi_service import registrar_kpi, listar_kpis
from services.diagnostic_service import diagnostico_empresa
from services.auto_strategy_service import plano_automatico

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
        "version": "StreetCore OS V20 ULTRA FREE"
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

@app.route("/leads")
def leads_page():
    return f"<pre>{listar_leads()}</pre>"

@app.route("/pipeline")
def pipeline_page():
    return f"<pre>{listar_pipeline()}</pre>"

@app.route("/catalog")
def catalog_page():
    return f"<pre>{listar_catalogo()}</pre>"

@app.route("/goals")
def goals_page():
    return f"<pre>{listar_metas()}</pre>"

@app.route("/kpis")
def kpis_page():
    return f"<pre>{listar_kpis()}</pre>"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V20 ULTRA FREE\n\n"
        "IA ULTRA:\n"
        "/brain analisar operação\n"
        "/diagnostic\n"
        "/autoplan street graff\n"
        "/goal vender_1000 1000\n"
        "/goals\n"
        "/goalstatus 1 concluida\n"
        "/kpi vendas 10\n"
        "/kpis\n\n"
        "CONTEÚDO:\n"
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
        "/batch street graff\n"
        "/batchreels street graff\n"
        "/batchstories street graff\n\n"
        "OPERAÇÃO:\n"
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
        "/report\n\n"
        "COMERCIAL:\n"
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
        "/lead joao instagram\n"
        "/leads\n"
        "/leadstatus 1 convertido\n"
        "/stage orçamento_enviado\n"
        "/pipeline\n"
        "/catalog camiseta 35\n"
        "/cataloglist\n"
        "/backup\n"
        "/backups"
    )

async def brain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pergunta = " ".join(context.args) or "analisar operação"
    await update.message.reply_text(cerebro_operacional(pergunta))

async def diagnostic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(diagnostico_empresa())

async def autoplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    await update.message.reply_text(plano_automatico(tema))

async def goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /goal vender_1000 1000")
        return

    nome = context.args[0]
    valor = " ".join(context.args[1:])
    await update.message.reply_text(criar_meta(nome, valor))

async def goals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_metas())

async def goalstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /goalstatus 1 concluida")
        return

    await update.message.reply_text(atualizar_meta(context.args[0], " ".join(context.args[1:])))

async def kpi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /kpi vendas 10")
        return

    nome = context.args[0]
    valor = " ".join(context.args[1:])
    await update.message.reply_text(registrar_kpi(nome, valor))

async def kpis_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_kpis())

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_post_instagram(" ".join(context.args) or "Street Graff"))

async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_story(" ".join(context.args) or "Street Graff"))

async def reels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_reels(" ".join(context.args) or "Street Graff"))

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_roteiro_video(" ".join(context.args) or "Street Graff"))

async def imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_prompt_imagem(" ".join(context.args) or "Street Graff"))

async def venda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_texto_venda(" ".join(context.args) or "Street Graff"))

async def campanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_campanha(" ".join(context.args) or "Street Graff"))

async def workflow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(executar_workflow(" ".join(context.args) or "Street Graff"))

async def legenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_legenda(" ".join(context.args) or "Street Graff"))

async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_hashtags(" ".join(context.args) or "Street Graff"))

async def grade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_grade_conteudo(" ".join(context.args) or "Street Graff"))

async def batch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_pacote_conteudo(" ".join(context.args) or "Street Graff"))

async def batchreels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_pacote_reels(" ".join(context.args) or "Street Graff"))

async def batchstories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_pacote_stories(" ".join(context.args) or "Street Graff"))

async def produtos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_produtos())

async def agentes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(agentes_conversando(" ".join(context.args) or "campanha Street Graff"))

async def task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    registrar_log("TASK", nome)
    await update.message.reply_text(criar_tarefa(nome))

async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_tarefas())

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_logs())

async def scheduler_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(executar_scheduler())

async def client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(criar_cliente(" ".join(context.args)))

async def clients_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_clientes())

async def event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use:\n/event nome data")
        return

    await update.message.reply_text(criar_evento(context.args[0], " ".join(context.args[1:])))

async def calendar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_eventos())

async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(resumo_financeiro())
        return

    try:
        await update.message.reply_text(adicionar_receita(float(context.args[0].replace(",", "."))))
    except ValueError:
        await update.message.reply_text("Use assim: /finance 100")

async def expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use assim: /expense 50")
        return

    try:
        await update.message.reply_text(adicionar_despesa(float(context.args[0].replace(",", "."))))
    except ValueError:
        await update.message.reply_text("Use assim: /expense 50")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_relatorio())

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    registrar_log("ORDER", nome)
    await update.message.reply_text(criar_pedido(nome))

async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_pedidos())

async def orderstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /orderstatus 1 em_producao")
        return

    await update.message.reply_text(atualizar_status_pedido(context.args[0], " ".join(context.args[1:])))

async def quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(criar_orcamento(" ".join(context.args)))

async def quotes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_orcamentos())

async def stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /stock camiseta 10")
        return

    try:
        await update.message.reply_text(adicionar_estoque(context.args[0], int(context.args[1])))
    except ValueError:
        await update.message.reply_text("A quantidade precisa ser número.")

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
    await update.message.reply_text(criar_fornecedor(" ".join(context.args)))

async def suppliers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_fornecedores())

async def production(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(criar_producao(" ".join(context.args)))

async def productions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_producao())

async def productionstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /productionstatus 1 finalizado")
        return

    await update.message.reply_text(atualizar_producao(context.args[0], " ".join(context.args[1:])))

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(criar_backup())

async def backups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_backups())

async def lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use assim: /lead joao instagram")
        return

    nome = context.args[0]
    origem = " ".join(context.args[1:]) or "manual"
    await update.message.reply_text(criar_lead(nome, origem))

async def leads_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_leads())

async def leadstatus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /leadstatus 1 convertido")
        return

    await update.message.reply_text(atualizar_lead(context.args[0], " ".join(context.args[1:])))

async def stage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(criar_etapa(" ".join(context.args)))

async def pipeline_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_pipeline())

async def catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /catalog camiseta 35")
        return

    try:
        await update.message.reply_text(criar_item_catalogo(context.args[0], float(context.args[1].replace(",", "."))))
    except ValueError:
        await update.message.reply_text("Preço inválido. Use: /catalog camiseta 35")

async def cataloglist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(listar_catalogo())

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = update.message.text
    salvar_memoria(mensagem)
    registrar_evento("mensagem")
    registrar_log("MSG", mensagem)
    await update.message.reply_text(resposta_free_ai(mensagem))

async def telegram_main():
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    comandos = [
        ("start", start),
        ("brain", brain),
        ("diagnostic", diagnostic),
        ("autoplan", autoplan),
        ("goal", goal),
        ("goals", goals_cmd),
        ("goalstatus", goalstatus),
        ("kpi", kpi),
        ("kpis", kpis_cmd),

        ("post", post),
        ("story", story),
        ("reels", reels),
        ("video", video),
        ("imagem", imagem),
        ("venda", venda),
        ("campanha", campanha),
        ("workflow", workflow),
        ("legenda", legenda),
        ("hashtags", hashtags),
        ("grade", grade),
        ("batch", batch),
        ("batchreels", batchreels),
        ("batchstories", batchstories),
        ("produtos", produtos),
        ("agentes", agentes),

        ("task", task),
        ("tasks", tasks_cmd),
        ("logs", logs_cmd),
        ("scheduler", scheduler_cmd),
        ("client", client),
        ("clients", clients_cmd),
        ("event", event),
        ("calendar", calendar_cmd),
        ("finance", finance),
        ("expense", expense),
        ("report", report),

        ("order", order),
        ("orders", orders_cmd),
        ("orderstatus", orderstatus),
        ("quote", quote),
        ("quotes", quotes_cmd),
        ("stock", stock),
        ("stocklist", stocklist),
        ("notify", notify),
        ("notifications", notifications_cmd),
        ("supplier", supplier),
        ("suppliers", suppliers_cmd),
        ("production", production),
        ("productions", productions_cmd),
        ("productionstatus", productionstatus),
        ("backup", backup),
        ("backups", backups),

        ("lead", lead),
        ("leads", leads_cmd),
        ("leadstatus", leadstatus),
        ("stage", stage),
        ("pipeline", pipeline_cmd),
        ("catalog", catalog),
        ("cataloglist", cataloglist),
    ]

    for nome, funcao in comandos:
        telegram_app.add_handler(CommandHandler(nome, funcao))

    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V20 ULTRA FREE...")
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    print("✅ Telegram ONLINE V20 ULTRA FREE")

    await asyncio.Event().wait()

def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())

threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)