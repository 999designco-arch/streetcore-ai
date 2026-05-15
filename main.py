import os
import sqlite3
import threading
import asyncio
from datetime import datetime
from flask import Flask, jsonify, request, redirect, session, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v28-free")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")
DB_PATH = "streetcore_v28.db"

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)
app.secret_key = SECRET_KEY


def db():
    return sqlite3.connect(DB_PATH)


def iniciar_banco():
    conn = db()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        cliente TEXT,
        status TEXT DEFAULT 'novo',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        origem TEXT,
        status TEXT DEFAULT 'novo',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        contato TEXT,
        historico TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS financeiro (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        valor REAL,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mensagem TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS conteudos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT,
        tipo TEXT,
        texto TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS campanhas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT,
        texto TEXT,
        status TEXT DEFAULT 'planejada',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS tarefas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        status TEXT DEFAULT 'pendente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS producao (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        cliente TEXT,
        status TEXT DEFAULT 'aguardando',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS estoque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        quantidade INTEGER,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS fornecedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        contato TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS notificacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mensagem TEXT,
        status TEXT DEFAULT 'nova',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")

    conn.commit()
    conn.close()
    print("✅ Banco V28 iniciado.")


def login_required():
    return session.get("logado") is True


def salvar_log(msg):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO logs (mensagem) VALUES (?)", (msg,))
    conn.commit()
    conn.close()


def contar(tabela):
    conn = db()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {tabela}")
    total = cur.fetchone()[0]
    conn.close()
    return total


def listar(tabela):
    conn = db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT 100")
    dados = cur.fetchall()
    conn.close()
    return dados


def financeiro():
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'")
    receita = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'")
    despesa = cur.fetchone()[0] or 0
    conn.close()
    return receita, despesa, receita - despesa


def gerar_post(tema):
    return (
        f"🔥 POST PRONTO - {tema.upper()}\n\n"
        "Sua marca precisa aparecer com presença.\n"
        "A Street Graff cria camisetas, adesivos, canecas, panfletos e brindes personalizados.\n\n"
        "📲 Chama no direct e peça seu orçamento.\n\n"
        "#streetgraff #personalizados #camisetaspersonalizadas #adesivospersonalizados"
    )


def gerar_story(tema):
    return (
        f"📲 STORY - {tema.upper()}\n\n"
        "Tela 1: Sua marca ainda está invisível?\n"
        "Tela 2: Personalizados com estilo urbano.\n"
        "Tela 3: Camisetas, adesivos, canecas, panfletos e brindes.\n"
        "Tela 4: Chama no direct e peça seu orçamento."
    )


def gerar_reels(tema):
    return (
        f"🎬 REELS - {tema.upper()}\n\n"
        "Gancho: Sua marca precisa aparecer mais?\n"
        "Cena 1: Mostre produto personalizado.\n"
        "Cena 2: Mostre bastidor da produção.\n"
        "Cena 3: Mostre resultado final.\n"
        "CTA: Chama no direct e peça seu orçamento."
    )


def gerar_campanha(tema):
    return f"{gerar_post(tema)}\n\n---\n\n{gerar_story(tema)}\n\n---\n\n{gerar_reels(tema)}"


def checklist():
    return (
        "✅ CHECKLIST OPERACIONAL\n\n"
        "1. Ver leads novos\n"
        "2. Atualizar pedidos\n"
        "3. Conferir produção\n"
        "4. Conferir estoque\n"
        "5. Registrar receita/despesa\n"
        "6. Criar campanha do dia\n"
        "7. Responder clientes\n"
        "8. Fazer backup"
    )


def relatorio():
    r, d, l = financeiro()
    return (
        "📊 RELATÓRIO V28\n\n"
        f"Pedidos: {contar('pedidos')}\n"
        f"Leads: {contar('leads')}\n"
        f"Clientes: {contar('clientes')}\n"
        f"Tarefas: {contar('tarefas')}\n"
        f"Produção: {contar('producao')}\n"
        f"Estoque: {contar('estoque')}\n"
        f"Fornecedores: {contar('fornecedores')}\n"
        f"Notificações: {contar('notificacoes')}\n\n"
        f"Receita: R$ {r:.2f}\n"
        f"Despesa: R$ {d:.2f}\n"
        f"Lucro: R$ {l:.2f}\n\n"
        "Decisão: focar em leads, produção e fechamento de pedidos."
    )


def layout(conteudo):
    return f"""
    <html>
    <head>
        <title>StreetCore OS V28</title>
        <style>
            body {{ margin:0; background:#050505; color:white; font-family:Arial; }}
            .sidebar {{
                position:fixed; top:0; left:0; bottom:0; width:260px;
                background:#0b0b0b; border-right:1px solid #222; padding:24px; overflow:auto;
            }}
            .sidebar h2 {{ color:#00ff88; }}
            .sidebar a {{ display:block; color:white; text-decoration:none; margin:12px 0; }}
            .sidebar a:hover {{ color:#00ff88; }}
            .main {{ margin-left:310px; padding:30px; }}
            .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:18px; }}
            .card {{ background:#111; border:1px solid #333; border-radius:18px; padding:22px; margin-bottom:18px; }}
            .big {{ color:#00ff88; font-size:36px; font-weight:bold; }}
            .ok {{ color:#00ff88; font-weight:bold; }}
            input, select, textarea {{
                padding:12px; border-radius:10px; border:0; margin:6px 0;
                width:100%; background:#1c1c1c; color:white;
            }}
            textarea {{ min-height:150px; }}
            button {{
                padding:12px 18px; border:0; border-radius:10px;
                background:#00ff88; font-weight:bold; cursor:pointer;
            }}
            table {{ width:100%; border-collapse:collapse; background:#111; border-radius:14px; overflow:hidden; }}
            th, td {{ padding:12px; border-bottom:1px solid #333; text-align:left; }}
            .tag {{ background:#1f1f1f; padding:6px 10px; border-radius:8px; }}
            a {{ color:#00ff88; }}
            pre {{ white-space:pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🔥 StreetCore</h2>
            <a href="/">Dashboard</a>
            <a href="/command">Command Center</a>
            <a href="/tarefas">Tarefas</a>
            <a href="/producao">Produção</a>
            <a href="/estoque">Estoque</a>
            <a href="/fornecedores">Fornecedores</a>
            <a href="/notificacoes">Notificações</a>
            <a href="/clientes">Clientes</a>
            <a href="/pedidos">Pedidos</a>
            <a href="/leads">Leads</a>
            <a href="/financeiro-web">Financeiro</a>
            <a href="/conteudo">Gerador IA</a>
            <a href="/relatorio-web">Relatório</a>
            <a href="/backup">Backup</a>
            <a href="/logs">Logs</a>
            <a href="/logout">Sair</a>
        </div>
        <div class="main">{conteudo}</div>
    </body>
    </html>
    """


@app.route("/")
def home():
    if not login_required():
        return redirect("/login")

    r, d, l = financeiro()

    return layout(f"""
    <h1>🔥 STREETCORE OS V28 COMMAND CENTER</h1>
    <p class="ok">Centro operacional com produção, tarefas, estoque e notificações.</p>

    <div class="grid">
        <div class="card"><h2>Pedidos</h2><div class="big">{contar("pedidos")}</div></div>
        <div class="card"><h2>Leads</h2><div class="big">{contar("leads")}</div></div>
        <div class="card"><h2>Tarefas</h2><div class="big">{contar("tarefas")}</div></div>
        <div class="card"><h2>Produção</h2><div class="big">{contar("producao")}</div></div>
        <div class="card"><h2>Estoque</h2><div class="big">{contar("estoque")}</div></div>
        <div class="card"><h2>Receita</h2><div class="big">R$ {r:.2f}</div></div>
        <div class="card"><h2>Lucro</h2><div class="big">R$ {l:.2f}</div></div>
    </div>

    <div class="card"><pre>{checklist()}</pre></div>
    """)


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
    if request.method == "POST":
        if request.form.get("usuario") == ADMIN_USER and request.form.get("senha") == ADMIN_PASS:
            session["logado"] = True
            return redirect("/")
        erro = "<p style='color:red;'>Login incorreto.</p>"

    return f"""
    <html>
    <body style="background:#050505;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="background:#111;padding:40px;border-radius:20px;border:1px solid #333;width:330px;">
            <h1>🔥 StreetCore</h1>
            <p>V28 Command Center</p>
            {erro}
            <form method="POST">
                <input name="usuario" placeholder="Usuário" style="width:100%;padding:14px;margin-bottom:12px;border-radius:10px;border:0;">
                <input name="senha" type="password" placeholder="Senha" style="width:100%;padding:14px;margin-bottom:12px;border-radius:10px;border:0;">
                <button style="width:100%;padding:14px;border:0;border-radius:10px;background:#00ff88;font-weight:bold;">Entrar</button>
            </form>
            <p>admin / streetcore</p>
        </div>
    </body>
    </html>
    """


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/health")
def health():
    return jsonify({"status": "online", "version": "StreetCore OS V28 Command Center"})


@app.route("/command", methods=["GET", "POST"])
def command():
    if not login_required():
        return redirect("/login")

    msg = ""
    if request.method == "POST":
        tipo = request.form.get("tipo")
        nome = request.form.get("nome")
        extra = request.form.get("extra")

        conn = db()
        cur = conn.cursor()

        if tipo == "tarefa":
            cur.execute("INSERT INTO tarefas (titulo) VALUES (?)", (nome,))
            msg = "Tarefa criada."

        elif tipo == "producao":
            cur.execute("INSERT INTO producao (item, cliente) VALUES (?, ?)", (nome, extra))
            msg = "Produção criada."

        elif tipo == "estoque":
            cur.execute("INSERT INTO estoque (item, quantidade) VALUES (?, ?)", (nome, int(extra or 0)))
            msg = "Estoque atualizado."

        elif tipo == "fornecedor":
            cur.execute("INSERT INTO fornecedores (nome, contato) VALUES (?, ?)", (nome, extra))
            msg = "Fornecedor criado."

        elif tipo == "notificacao":
            cur.execute("INSERT INTO notificacoes (mensagem) VALUES (?)", (nome,))
            msg = "Notificação criada."

        elif tipo == "pedido":
            cur.execute("INSERT INTO pedidos (nome, cliente) VALUES (?, ?)", (nome, extra))
            msg = "Pedido criado."

        elif tipo == "lead":
            cur.execute("INSERT INTO leads (nome, origem) VALUES (?, ?)", (nome, extra or "painel"))
            msg = "Lead criado."

        conn.commit()
        conn.close()
        salvar_log(f"Command Center: {tipo} - {nome}")

    return layout(f"""
    <h1>🧠 Command Center</h1>
    <div class="card">
        <p class="ok">{msg}</p>
        <form method="POST">
            <label>Tipo</label>
            <select name="tipo">
                <option value="tarefa">Tarefa</option>
                <option value="producao">Produção</option>
                <option value="estoque">Estoque</option>
                <option value="fornecedor">Fornecedor</option>
                <option value="notificacao">Notificação</option>
                <option value="pedido">Pedido</option>
                <option value="lead">Lead</option>
            </select>
            <label>Nome / Descrição</label>
            <input name="nome">
            <label>Extra: cliente, contato, origem ou quantidade</label>
            <input name="extra">
            <button>Executar</button>
        </form>
    </div>
    """)


def table_page(titulo, tabela, colunas):
    if not login_required():
        return redirect("/login")
    dados = listar(tabela)
    linhas = "".join(["<tr>" + "".join([f"<td>{x}</td>" for x in d]) + "</tr>" for d in dados])
    head = "".join([f"<th>{c}</th>" for c in colunas])
    return layout(f"<h1>{titulo}</h1><table><tr>{head}</tr>{linhas}</table>")


@app.route("/tarefas")
def tarefas_page():
    return table_page("✅ Tarefas", "tarefas", ["ID", "Título", "Status", "Data"])


@app.route("/producao")
def producao_page():
    return table_page("🏗️ Produção", "producao", ["ID", "Item", "Cliente", "Status", "Data"])


@app.route("/estoque")
def estoque_page():
    return table_page("📦 Estoque", "estoque", ["ID", "Item", "Quantidade", "Data"])


@app.route("/fornecedores")
def fornecedores_page():
    return table_page("🏭 Fornecedores", "fornecedores", ["ID", "Nome", "Contato", "Data"])


@app.route("/notificacoes")
def notificacoes_page():
    return table_page("🔔 Notificações", "notificacoes", ["ID", "Mensagem", "Status", "Data"])


@app.route("/clientes")
def clientes_page():
    return table_page("👤 Clientes", "clientes", ["ID", "Nome", "Contato", "Histórico", "Data"])


@app.route("/pedidos")
def pedidos_page():
    return table_page("📦 Pedidos", "pedidos", ["ID", "Nome", "Cliente", "Status", "Data"])


@app.route("/leads")
def leads_page():
    return table_page("🎯 Leads", "leads", ["ID", "Nome", "Origem", "Status", "Data"])


@app.route("/financeiro-web")
def financeiro_web():
    if not login_required():
        return redirect("/login")
    r, d, l = financeiro()
    return layout(f"""
    <h1>💵 Financeiro</h1>
    <div class="grid">
        <div class="card"><h2>Receita</h2><div class="big">R$ {r:.2f}</div></div>
        <div class="card"><h2>Despesa</h2><div class="big">R$ {d:.2f}</div></div>
        <div class="card"><h2>Lucro</h2><div class="big">R$ {l:.2f}</div></div>
    </div>
    """)


@app.route("/conteudo", methods=["GET", "POST"])
def conteudo():
    if not login_required():
        return redirect("/login")
    resultado = ""
    if request.method == "POST":
        tema = request.form.get("tema") or "Street Graff"
        tipo = request.form.get("tipo")
        if tipo == "post":
            resultado = gerar_post(tema)
        elif tipo == "story":
            resultado = gerar_story(tema)
        elif tipo == "reels":
            resultado = gerar_reels(tema)
        else:
            resultado = gerar_campanha(tema)

        conn = db()
        cur = conn.cursor()
        cur.execute("INSERT INTO conteudos (tema, tipo, texto) VALUES (?, ?, ?)", (tema, tipo, resultado))
        conn.commit()
        conn.close()

    return layout(f"""
    <h1>🤖 Gerador IA</h1>
    <div class="card">
        <form method="POST">
            <input name="tema" placeholder="Tema">
            <select name="tipo">
                <option value="post">Post</option>
                <option value="story">Story</option>
                <option value="reels">Reels</option>
                <option value="campanha">Campanha</option>
            </select>
            <button>Gerar</button>
        </form>
    </div>
    <div class="card"><textarea>{resultado}</textarea></div>
    """)


@app.route("/relatorio-web")
def relatorio_web():
    if not login_required():
        return redirect("/login")
    return layout(f"<h1>📊 Relatório</h1><div class='card'><pre>{relatorio()}</pre></div>")


@app.route("/logs")
def logs_page():
    return table_page("🧾 Logs", "logs", ["ID", "Mensagem", "Data"])


@app.route("/backup")
def backup():
    if not login_required():
        return redirect("/login")
    nome = f"backup_v28_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    with open(DB_PATH, "rb") as f:
        data = f.read()
    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={nome}"})


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V28 COMMAND CENTER\n\n"
        "/tarefa criar arte\n"
        "/tarefas\n"
        "/producao camiseta joao\n"
        "/producoes\n"
        "/estoque camiseta 10\n"
        "/estoques\n"
        "/fornecedor malharia 119999\n"
        "/fornecedores\n"
        "/notificar revisar pedidos\n"
        "/notificacoes\n"
        "/pedido camiseta joao\n"
        "/lead maria instagram\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/relatorio\n"
        "/post camisetas\n"
        "/campanha street graff"
    )


async def status(update, context):
    await update.message.reply_text("✅ V28 online.")


async def criar_generico(update, context, tabela, campos, valores, resposta):
    conn = db()
    cur = conn.cursor()
    q = ",".join(["?"] * len(valores))
    cur.execute(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)
    conn.commit()
    conn.close()
    await update.message.reply_text(resposta)


async def tarefa_cmd(update, context):
    nome = " ".join(context.args)
    await criar_generico(update, context, "tarefas", "titulo", (nome,), f"✅ Tarefa criada: {nome}")


async def tarefas_cmd(update, context):
    await update.message.reply_text(str(listar("tarefas")))


async def producao_cmd(update, context):
    item = context.args[0] if context.args else ""
    cliente = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    await criar_generico(update, context, "producao", "item,cliente", (item, cliente), "🏗️ Produção criada.")


async def producoes_cmd(update, context):
    await update.message.reply_text(str(listar("producao")))


async def estoque_cmd(update, context):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /estoque camiseta 10")
        return
    await criar_generico(update, context, "estoque", "item,quantidade", (context.args[0], int(context.args[1])), "📦 Estoque atualizado.")


async def estoques_cmd(update, context):
    await update.message.reply_text(str(listar("estoque")))


async def fornecedor_cmd(update, context):
    nome = context.args[0] if context.args else ""
    contato = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    await criar_generico(update, context, "fornecedores", "nome,contato", (nome, contato), "🏭 Fornecedor criado.")


async def fornecedores_cmd(update, context):
    await update.message.reply_text(str(listar("fornecedores")))


async def notificar_cmd(update, context):
    msg = " ".join(context.args)
    await criar_generico(update, context, "notificacoes", "mensagem", (msg,), f"🔔 Notificação: {msg}")


async def notificacoes_cmd(update, context):
    await update.message.reply_text(str(listar("notificacoes")))


async def pedido_cmd(update, context):
    item = context.args[0] if context.args else ""
    cliente = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    await criar_generico(update, context, "pedidos", "nome,cliente", (item, cliente), "📦 Pedido criado.")


async def lead_cmd(update, context):
    nome = context.args[0] if context.args else ""
    origem = " ".join(context.args[1:]) if len(context.args) > 1 else "manual"
    await criar_generico(update, context, "leads", "nome,origem", (nome, origem), "🎯 Lead criado.")


async def receita_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    await criar_generico(update, context, "financeiro", "tipo,valor,descricao", ("receita", valor, "telegram"), f"💰 Receita R$ {valor:.2f}")


async def despesa_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    await criar_generico(update, context, "financeiro", "tipo,valor,descricao", ("despesa", valor, "telegram"), f"💸 Despesa R$ {valor:.2f}")


async def financeiro_cmd(update, context):
    r, d, l = financeiro()
    await update.message.reply_text(f"💵 FINANCEIRO\nReceita: R$ {r:.2f}\nDespesa: R$ {d:.2f}\nLucro: R$ {l:.2f}")


async def relatorio_cmd(update, context):
    await update.message.reply_text(relatorio())


async def post_cmd(update, context):
    await update.message.reply_text(gerar_post(" ".join(context.args) or "Street Graff"))


async def campanha_cmd(update, context):
    await update.message.reply_text(gerar_campanha(" ".join(context.args) or "Street Graff"))


async def responder(update, context):
    salvar_log(update.message.text)
    await update.message.reply_text("🤖 V28 recebeu. Use /start.")


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    comandos = {
        "start": start,
        "status": status,
        "tarefa": tarefa_cmd,
        "tarefas": tarefas_cmd,
        "producao": producao_cmd,
        "producoes": producoes_cmd,
        "estoque": estoque_cmd,
        "estoques": estoques_cmd,
        "fornecedor": fornecedor_cmd,
        "fornecedores": fornecedores_cmd,
        "notificar": notificar_cmd,
        "notificacoes": notificacoes_cmd,
        "pedido": pedido_cmd,
        "lead": lead_cmd,
        "receita": receita_cmd,
        "despesa": despesa_cmd,
        "financeiro": financeiro_cmd,
        "relatorio": relatorio_cmd,
        "post": post_cmd,
        "campanha": campanha_cmd,
    }

    for nome, func in comandos.items():
        bot.add_handler(CommandHandler(nome, func))

    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V28...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V28")

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
