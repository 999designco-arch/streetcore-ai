import os
import re
import json
import shutil
import sqlite3
import asyncio
import threading
from datetime import datetime
from flask import Flask, jsonify

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DB_PATH = "streetcore_master.db"
UPLOAD_FOLDER = "uploads"
BACKUP_FOLDER = "backups"

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)


def db():
    return sqlite3.connect(DB_PATH)


def iniciar_banco():
    conn = db()
    cur = conn.cursor()

    tabelas = [
        "CREATE TABLE IF NOT EXISTS memorias (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, mensagem TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS analytics (id INTEGER PRIMARY KEY AUTOINCREMENT, evento TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS tarefas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, status TEXT DEFAULT 'pendente', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, origem TEXT, status TEXT DEFAULT 'novo', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, status TEXT DEFAULT 'novo', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, valor REAL, descricao TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, quantidade INTEGER, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS producao (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, status TEXT DEFAULT 'aguardando', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS fornecedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS orcamentos (id INTEGER PRIMARY KEY AUTOINCREMENT, descricao TEXT, valor REAL, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS catalogo (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS calendario (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, data TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS conhecimento (id INTEGER PRIMARY KEY AUTOINCREMENT, texto TEXT, origem TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, valor TEXT, status TEXT DEFAULT 'ativa', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS kpis (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, valor TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS notificacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, mensagem TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
        "CREATE TABLE IF NOT EXISTS automacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, acao TEXT, status TEXT DEFAULT 'ativa', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
    ]

    for t in tabelas:
        cur.execute(t)

    conn.commit()
    conn.close()
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(BACKUP_FOLDER, exist_ok=True)
    print("✅ STREETCORE OS V21 MASTER FREE iniciado.")


def salvar(tabela, campos, valores):
    conn = db()
    cur = conn.cursor()
    q = ",".join(["?"] * len(valores))
    cur.execute(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)
    conn.commit()
    conn.close()


def listar(tabela, campos="*", limite=30):
    conn = db()
    cur = conn.cursor()
    cur.execute(f"SELECT {campos} FROM {tabela} ORDER BY id DESC LIMIT {limite}")
    dados = cur.fetchall()
    conn.close()
    return dados


def log(tipo, msg):
    salvar("logs", "tipo,mensagem", (tipo, msg))


def evento(nome):
    salvar("analytics", "evento", (nome,))


def texto_lista(titulo, dados):
    if not dados:
        return f"{titulo}\n\nNada encontrado."
    return titulo + "\n\n" + "\n".join([" | ".join(map(str, d)) for d in dados])


def conteudo_base(tema):
    return (
        f"🔥 {tema.upper()}\n\n"
        "Sua marca precisa aparecer com presença.\n"
        "A Street Graff cria camisetas, adesivos, canecas, panfletos e brindes personalizados.\n\n"
        "📲 Chama no direct e peça seu orçamento.\n"
        "Pagamento via PIX."
    )


def hashtags(tema):
    return (
        "#streetgraff #personalizados #camisetaspersonalizadas "
        "#adesivospersonalizados #canecaspersonalizadas #brindespersonalizados "
        "#empreendedorismo #marketingdigital #negociolocal #designpersonalizado"
    )


def resposta_ia(msg):
    t = msg.lower()
    if "venda" in t:
        return venda_texto(msg)
    if "post" in t:
        return post_texto(msg)
    if "video" in t or "vídeo" in t:
        return video_texto(msg)
    return (
        "🤖 STREETCORE IA MASTER\n\n"
        "Posso operar conteúdo, vendas, pedidos, clientes, financeiro, estoque, produção, metas, KPIs, documentos e relatórios.\n\n"
        "Digite /start para ver tudo."
    )


def post_texto(tema):
    return f"📸 POST PRONTO\n\n{conteudo_base(tema)}\n\n{hashtags(tema)}"


def story_texto(tema):
    return (
        f"📲 STORY - {tema.upper()}\n\n"
        "Tela 1: Sua marca ainda está invisível?\n"
        "Tela 2: Personalizados com identidade.\n"
        "Tela 3: Camisetas, adesivos, canecas, panfletos e brindes.\n"
        "Tela 4: Chama no direct e peça seu orçamento."
    )


def reels_texto(tema):
    return (
        f"🎬 REELS - {tema.upper()}\n\n"
        "Gancho: Sua marca precisa aparecer mais?\n"
        "Cena 1: Mostre o produto.\n"
        "Cena 2: Mostre bastidor.\n"
        "Cena 3: Mostre resultado final.\n"
        "CTA: Chama no direct."
    )


def video_texto(tema):
    return (
        f"🎥 ROTEIRO DE VÍDEO - {tema.upper()}\n\n"
        "0-3s: Gancho forte\n"
        "4-10s: Produto em destaque\n"
        "11-20s: Benefício + prova visual\n"
        "21-30s: CTA para orçamento"
    )


def venda_texto(tema):
    return (
        f"💰 COPY DE VENDA - {tema.upper()}\n\n"
        "Quer transformar sua ideia em produto real?\n"
        "A Street Graff cria personalizados com estilo, presença e qualidade.\n\n"
        "✅ Camisetas\n✅ Adesivos\n✅ Canecas\n✅ Panfletos\n✅ Brindes\n\n"
        "📲 Chama no direct e peça seu orçamento via PIX."
    )


def campanha_texto(tema):
    return f"{post_texto(tema)}\n\n---\n\n{story_texto(tema)}\n\n---\n\n{reels_texto(tema)}\n\n---\n\n{venda_texto(tema)}"


def batch_texto(tema):
    return "\n\n================\n\n".join([post_texto(f"{tema} ideia {i}") for i in range(1, 8)])


def grade_texto(tema):
    return (
        f"📅 GRADE SEMANAL - {tema.upper()}\n\n"
        "Segunda: post de produto\n"
        "Terça: reels de bastidor\n"
        "Quarta: story com enquete\n"
        "Quinta: post de venda\n"
        "Sexta: reels com CTA\n"
        "Sábado: promoção\n"
        "Domingo: prova social\n\n"
        "Horários: 12h, 18h, 20h30."
    )


def prompt_imagem(tema):
    return (
        f"🎨 PROMPT DE IMAGEM\n\n"
        f"Arte publicitária para {tema}, estilo streetwear, preto e branco, urbano, alto contraste, produto em destaque, qualidade 4K."
    )


def financeiro_resumo():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'")
    receita = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'")
    despesa = cur.fetchone()[0] or 0
    conn.close()
    lucro = receita - despesa
    return f"💵 FINANCEIRO\n\nReceita: R$ {receita:.2f}\nDespesa: R$ {despesa:.2f}\nLucro: R$ {lucro:.2f}"


def analytics_resumo():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT evento, COUNT(*) FROM analytics GROUP BY evento ORDER BY COUNT(*) DESC")
    dados = cur.fetchall()
    conn.close()
    return {e: q for e, q in dados}


def calcular_orcamento(desc):
    t = desc.lower()
    base = 35
    if "caneca" in t:
        base = 30
    if "adesivo" in t:
        base = 8
    if "panfleto" in t:
        base = 80
    qtd = 1
    for p in t.split():
        if p.isdigit():
            qtd = int(p)
            break
    return base * qtd


def diagnostico():
    return (
        "🩺 DIAGNÓSTICO MASTER\n\n"
        f"{financeiro_resumo()}\n\n"
        f"Leads:\n{texto_lista('', listar('leads', 'id,nome,origem,status', 10))}\n\n"
        f"Pedidos:\n{texto_lista('', listar('pedidos', 'id,nome,status', 10))}\n\n"
        "Ações recomendadas:\n"
        "✅ Criar campanha com /autoplan\n"
        "✅ Gerar conteúdo com /batch\n"
        "✅ Atualizar pedidos\n"
        "✅ Controlar despesas\n"
        "✅ Fazer backup"
    )


def autoplan(tema):
    return (
        f"🚀 PLANO MASTER - {tema.upper()}\n\n"
        f"{campanha_texto(tema)}\n\n"
        f"{grade_texto(tema)}\n\n"
        f"{batch_texto(tema)}"
    )


def backup_db():
    if not os.path.exists(DB_PATH):
        return "Banco ainda não existe."
    nome = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    destino = os.path.join(BACKUP_FOLDER, nome)
    shutil.copy(DB_PATH, destino)
    return f"✅ Backup criado: {destino}"


def extrair_txt(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        try:
            with open(caminho, "r", encoding="latin-1") as f:
                return f.read()
        except Exception:
            return ""


def extrair_pdf(caminho):
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(caminho)
        return "\n".join([p.extract_text() or "" for p in reader.pages])
    except Exception:
        return ""


def limpar_nome(nome):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", nome or "arquivo")


@app.route("/")
def home():
    return """
    <html>
    <head>
    <title>StreetCore OS V21 MASTER FREE</title>
    <style>
    body{background:#050505;color:white;font-family:Arial;padding:30px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:15px}
    .card{background:#111;padding:20px;border-radius:14px;border:1px solid #333}
    .ok{color:#00ff88;font-weight:bold}
    a{color:#00ff88}
    </style>
    </head>
    <body>
    <h1>🔥 STREETCORE OS V21 MASTER FREE</h1>
    <p class="ok">Sistema máximo gratuito online.</p>
    <div class="grid">
    <div class="card"><h2>IA</h2><p>Cérebro, diagnóstico, plano, conteúdo, campanhas.</p></div>
    <div class="card"><h2>Operação</h2><p>Pedidos, produção, estoque, fornecedores.</p></div>
    <div class="card"><h2>Comercial</h2><p>Leads, clientes, pipeline, orçamentos, catálogo.</p></div>
    <div class="card"><h2>Gestão</h2><p>Financeiro, metas, KPIs, tarefas, logs, backups.</p></div>
    <div class="card"><h2>Links</h2>
    <p><a href="/health">Health</a></p>
    <p><a href="/analytics">Analytics</a></p>
    <p><a href="/finance">Financeiro</a></p>
    <p><a href="/orders">Pedidos</a></p>
    <p><a href="/leads">Leads</a></p>
    </div>
    </div>
    </body>
    </html>
    """


@app.route("/health")
def health():
    return jsonify({"status": "online", "version": "StreetCore OS V21 MASTER FREE"})


@app.route("/analytics")
def analytics():
    return jsonify(analytics_resumo())


@app.route("/finance")
def finance_page():
    return f"<pre>{financeiro_resumo()}</pre>"


@app.route("/orders")
def orders_page():
    return f"<pre>{texto_lista('PEDIDOS', listar('pedidos','id,nome,status,criado_em'))}</pre>"


@app.route("/leads")
def leads_page():
    return f"<pre>{texto_lista('LEADS', listar('leads','id,nome,origem,status,criado_em'))}</pre>"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V21 MASTER FREE\n\n"
        "IA MASTER:\n"
        "/brain analisar operação\n/diagnostic\n/autoplan street graff\n"
        "/goal vender_1000 1000\n/goals\n/kpi vendas 10\n/kpis\n\n"
        "CONTEÚDO:\n"
        "/post tema\n/story tema\n/reels tema\n/video tema\n/imagem tema\n"
        "/venda tema\n/campanha tema\n/batch tema\n/grade tema\n\n"
        "OPERAÇÃO:\n"
        "/task nome\n/tasks\n/order pedido\n/orders\n/orderstatus 1 pronto\n"
        "/production item\n/productions\n/stock camiseta 10\n/stocklist\n\n"
        "COMERCIAL:\n"
        "/lead joao instagram\n/leads\n/client joao\n/clients\n/quote 10 camisetas\n/quotes\n/catalog camiseta 35\n/cataloglist\n\n"
        "GESTÃO:\n"
        "/finance 100\n/expense 50\n/report\n/backup\n/logs\n/memory\n\n"
        "📎 Envie PDF ou TXT para salvar conhecimento."
    )


async def cmd_post(update, context): await update.message.reply_text(post_texto(" ".join(context.args) or "Street Graff"))
async def cmd_story(update, context): await update.message.reply_text(story_texto(" ".join(context.args) or "Street Graff"))
async def cmd_reels(update, context): await update.message.reply_text(reels_texto(" ".join(context.args) or "Street Graff"))
async def cmd_video(update, context): await update.message.reply_text(video_texto(" ".join(context.args) or "Street Graff"))
async def cmd_imagem(update, context): await update.message.reply_text(prompt_imagem(" ".join(context.args) or "Street Graff"))
async def cmd_venda(update, context): await update.message.reply_text(venda_texto(" ".join(context.args) or "Street Graff"))
async def cmd_campanha(update, context): await update.message.reply_text(campanha_texto(" ".join(context.args) or "Street Graff"))
async def cmd_batch(update, context): await update.message.reply_text(batch_texto(" ".join(context.args) or "Street Graff"))
async def cmd_grade(update, context): await update.message.reply_text(grade_texto(" ".join(context.args) or "Street Graff"))
async def cmd_diagnostic(update, context): await update.message.reply_text(diagnostico())
async def cmd_autoplan(update, context): await update.message.reply_text(autoplan(" ".join(context.args) or "Street Graff"))
async def cmd_brain(update, context): await update.message.reply_text(diagnostico() + "\n\n🧠 Decisão: gerar conteúdo, captar leads e controlar produção.")


async def cmd_task(update, context):
    nome = " ".join(context.args)
    salvar("tarefas", "nome,status", (nome, "pendente"))
    await update.message.reply_text(f"✅ Tarefa criada: {nome}")


async def cmd_tasks(update, context): await update.message.reply_text(texto_lista("TAREFAS", listar("tarefas", "id,nome,status,criado_em")))


async def cmd_order(update, context):
    nome = " ".join(context.args)
    salvar("pedidos", "nome,status", (nome, "novo"))
    await update.message.reply_text(f"📦 Pedido criado: {nome}")


async def cmd_orders(update, context): await update.message.reply_text(texto_lista("PEDIDOS", listar("pedidos", "id,nome,status,criado_em")))


async def cmd_orderstatus(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /orderstatus 1 pronto")
        return
    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET status=? WHERE id=?", (" ".join(context.args[1:]), context.args[0]))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Pedido atualizado.")


async def cmd_lead(update, context):
    if not context.args:
        await update.message.reply_text("Use: /lead joao instagram")
        return
    nome = context.args[0]
    origem = " ".join(context.args[1:]) or "manual"
    salvar("leads", "nome,origem,status", (nome, origem, "novo"))
    await update.message.reply_text(f"🎯 Lead criado: {nome}")


async def cmd_leads(update, context): await update.message.reply_text(texto_lista("LEADS", listar("leads", "id,nome,origem,status,criado_em")))


async def cmd_client(update, context):
    nome = " ".join(context.args)
    salvar("clientes", "nome", (nome,))
    await update.message.reply_text(f"👤 Cliente criado: {nome}")


async def cmd_clients(update, context): await update.message.reply_text(texto_lista("CLIENTES", listar("clientes", "id,nome,criado_em")))


async def cmd_finance(update, context):
    if not context.args:
        await update.message.reply_text(financeiro_resumo())
        return
    valor = float(context.args[0].replace(",", "."))
    salvar("financeiro", "tipo,valor,descricao", ("receita", valor, "manual"))
    await update.message.reply_text(f"💰 Receita adicionada: R$ {valor:.2f}")


async def cmd_expense(update, context):
    if not context.args:
        await update.message.reply_text("Use: /expense 50")
        return
    valor = float(context.args[0].replace(",", "."))
    salvar("financeiro", "tipo,valor,descricao", ("despesa", valor, "manual"))
    await update.message.reply_text(f"💸 Despesa adicionada: R$ {valor:.2f}")


async def cmd_quote(update, context):
    desc = " ".join(context.args)
    valor = calcular_orcamento(desc)
    salvar("orcamentos", "descricao,valor", (desc, valor))
    await update.message.reply_text(f"🧾 Orçamento: {desc}\nValor estimado: R$ {valor:.2f}")


async def cmd_quotes(update, context): await update.message.reply_text(texto_lista("ORÇAMENTOS", listar("orcamentos", "id,descricao,valor,criado_em")))


async def cmd_stock(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /stock camiseta 10")
        return
    salvar("estoque", "item,quantidade", (context.args[0], int(context.args[1])))
    await update.message.reply_text("📦 Estoque atualizado.")


async def cmd_stocklist(update, context): await update.message.reply_text(texto_lista("ESTOQUE", listar("estoque", "id,item,quantidade,criado_em")))


async def cmd_production(update, context):
    nome = " ".join(context.args)
    salvar("producao", "nome,status", (nome, "aguardando"))
    await update.message.reply_text(f"🏗️ Produção criada: {nome}")


async def cmd_productions(update, context): await update.message.reply_text(texto_lista("PRODUÇÃO", listar("producao", "id,nome,status,criado_em")))


async def cmd_goal(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /goal vender_1000 1000")
        return
    salvar("metas", "nome,valor,status", (context.args[0], " ".join(context.args[1:]), "ativa"))
    await update.message.reply_text("🎯 Meta criada.")


async def cmd_goals(update, context): await update.message.reply_text(texto_lista("METAS", listar("metas", "id,nome,valor,status,criado_em")))


async def cmd_kpi(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /kpi vendas 10")
        return
    salvar("kpis", "nome,valor", (context.args[0], " ".join(context.args[1:])))
    await update.message.reply_text("📈 KPI registrado.")


async def cmd_kpis(update, context): await update.message.reply_text(texto_lista("KPIS", listar("kpis", "id,nome,valor,criado_em")))


async def cmd_catalog(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /catalog camiseta 35")
        return
    salvar("catalogo", "nome,preco", (context.args[0], float(context.args[1].replace(",", "."))))
    await update.message.reply_text("🛍️ Item no catálogo criado.")


async def cmd_cataloglist(update, context): await update.message.reply_text(texto_lista("CATÁLOGO", listar("catalogo", "id,nome,preco,criado_em")))


async def cmd_report(update, context):
    await update.message.reply_text(f"📊 RELATÓRIO MASTER\n\n{financeiro_resumo()}\n\n{diagnostico()}")


async def cmd_backup(update, context): await update.message.reply_text(backup_db())
async def cmd_logs(update, context): await update.message.reply_text(texto_lista("LOGS", listar("logs", "id,tipo,mensagem,criado_em")))
async def cmd_memory(update, context): await update.message.reply_text(texto_lista("MEMÓRIA", listar("memorias", "id,texto,criado_em")))
async def cmd_notify(update, context):
    msg = " ".join(context.args)
    salvar("notificacoes", "mensagem", (msg,))
    await update.message.reply_text(f"🔔 Notificação criada: {msg}")


async def receber_documento(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    nome = limpar_nome(doc.file_name or "arquivo")
    arquivo = await context.bot.get_file(doc.file_id)
    caminho = os.path.join(UPLOAD_FOLDER, nome)
    await arquivo.download_to_drive(caminho)

    texto = ""
    if nome.lower().endswith(".txt"):
        texto = extrair_txt(caminho)
    elif nome.lower().endswith(".pdf"):
        texto = extrair_pdf(caminho)

    if texto:
        salvar("conhecimento", "texto,origem", (texto[:8000], nome))
        await update.message.reply_text(f"✅ Arquivo salvo e lido: {nome}\n\nPrévia:\n{texto[:1000]}")
    else:
        await update.message.reply_text(f"✅ Arquivo salvo: {nome}\n⚠️ Não consegui extrair texto.")


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    salvar("memorias", "texto", (msg,))
    evento("mensagem")
    log("MSG", msg)
    await update.message.reply_text(resposta_ia(msg))


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    comandos = {
        "start": start,
        "post": cmd_post,
        "story": cmd_story,
        "reels": cmd_reels,
        "video": cmd_video,
        "imagem": cmd_imagem,
        "venda": cmd_venda,
        "campanha": cmd_campanha,
        "batch": cmd_batch,
        "grade": cmd_grade,
        "brain": cmd_brain,
        "diagnostic": cmd_diagnostic,
        "autoplan": cmd_autoplan,
        "task": cmd_task,
        "tasks": cmd_tasks,
        "order": cmd_order,
        "orders": cmd_orders,
        "orderstatus": cmd_orderstatus,
        "lead": cmd_lead,
        "leads": cmd_leads,
        "client": cmd_client,
        "clients": cmd_clients,
        "finance": cmd_finance,
        "expense": cmd_expense,
        "quote": cmd_quote,
        "quotes": cmd_quotes,
        "stock": cmd_stock,
        "stocklist": cmd_stocklist,
        "production": cmd_production,
        "productions": cmd_productions,
        "goal": cmd_goal,
        "goals": cmd_goals,
        "kpi": cmd_kpi,
        "kpis": cmd_kpis,
        "catalog": cmd_catalog,
        "cataloglist": cmd_cataloglist,
        "report": cmd_report,
        "backup": cmd_backup,
        "logs": cmd_logs,
        "memory": cmd_memory,
        "notify": cmd_notify,
    }

    for nome, funcao in comandos.items():
        bot.add_handler(CommandHandler(nome, funcao))

    bot.add_handler(MessageHandler(filters.Document.ALL, receber_documento))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V21 MASTER FREE...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V21 MASTER FREE")
    await asyncio.Event().wait()


def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())


iniciar_banco()
threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)