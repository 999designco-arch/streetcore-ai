import os
import sqlite3
import threading
import asyncio
from flask import Flask, jsonify, request, redirect, session
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v24-free")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")

DB_PATH = "streetcore_v24.db"

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)
app.secret_key = SECRET_KEY


def db():
    return sqlite3.connect(DB_PATH)


def iniciar_banco():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            status TEXT DEFAULT 'novo',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            origem TEXT,
            status TEXT DEFAULT 'novo',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            valor REAL,
            descricao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Banco V24 iniciado.")


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
    cur.execute(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT 50")
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


def buscar_geral(termo):
    conn = db()
    cur = conn.cursor()

    termo_like = f"%{termo}%"

    cur.execute("SELECT id, nome, status, criado_em FROM pedidos WHERE nome LIKE ? LIMIT 20", (termo_like,))
    pedidos = cur.fetchall()

    cur.execute("SELECT id, nome, origem, status, criado_em FROM leads WHERE nome LIKE ? OR origem LIKE ? LIMIT 20", (termo_like, termo_like))
    leads = cur.fetchall()

    conn.close()

    return pedidos, leads


def layout(conteudo):
    return f"""
    <html>
    <head>
        <title>StreetCore OS V24</title>
        <style>
            body {{
                margin: 0;
                background: #050505;
                color: white;
                font-family: Arial, sans-serif;
            }}

            .sidebar {{
                position: fixed;
                top: 0;
                left: 0;
                bottom: 0;
                width: 240px;
                background: #0b0b0b;
                border-right: 1px solid #222;
                padding: 24px;
            }}

            .sidebar h2 {{
                color: #00ff88;
            }}

            .sidebar a {{
                display: block;
                color: white;
                text-decoration: none;
                margin: 13px 0;
            }}

            .sidebar a:hover {{
                color: #00ff88;
            }}

            .main {{
                margin-left: 290px;
                padding: 30px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
                gap: 18px;
            }}

            .card {{
                background: #111;
                border: 1px solid #333;
                border-radius: 18px;
                padding: 22px;
                margin-bottom: 18px;
            }}

            .big {{
                color: #00ff88;
                font-size: 38px;
                font-weight: bold;
            }}

            .ok {{
                color: #00ff88;
                font-weight: bold;
            }}

            input, select {{
                padding: 12px;
                border-radius: 10px;
                border: 0;
                margin: 6px 0;
                width: 100%;
                background: #1c1c1c;
                color: white;
            }}

            button {{
                padding: 12px 18px;
                border: 0;
                border-radius: 10px;
                background: #00ff88;
                font-weight: bold;
                cursor: pointer;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: #111;
                border-radius: 14px;
                overflow: hidden;
            }}

            th, td {{
                padding: 12px;
                border-bottom: 1px solid #333;
                text-align: left;
            }}

            .tag {{
                background: #1f1f1f;
                padding: 6px 10px;
                border-radius: 8px;
            }}

            a {{
                color: #00ff88;
            }}
        </style>
    </head>

    <body>
        <div class="sidebar">
            <h2>🔥 StreetCore</h2>
            <a href="/">Dashboard</a>
            <a href="/pedidos">Pedidos</a>
            <a href="/leads">Leads</a>
            <a href="/financeiro-web">Financeiro</a>
            <a href="/criar">Criar</a>
            <a href="/buscar">Buscar</a>
            <a href="/logs">Logs</a>
            <a href="/health">Health</a>
            <a href="/logout">Sair</a>
        </div>

        <div class="main">
            {conteudo}
        </div>
    </body>
    </html>
    """


@app.route("/")
def home():
    if not login_required():
        return redirect("/login")

    receita, despesa, lucro = financeiro()

    conteudo = f"""
    <h1>🔥 STREETCORE OS V24 MASTER PANEL</h1>
    <p class="ok">Painel com ações, busca, pedidos, leads e financeiro.</p>

    <div class="grid">
        <div class="card">
            <h2>Pedidos</h2>
            <div class="big">{contar("pedidos")}</div>
            <a href="/pedidos">Ver pedidos</a>
        </div>

        <div class="card">
            <h2>Leads</h2>
            <div class="big">{contar("leads")}</div>
            <a href="/leads">Ver leads</a>
        </div>

        <div class="card">
            <h2>Receita</h2>
            <div class="big">R$ {receita:.2f}</div>
        </div>

        <div class="card">
            <h2>Despesa</h2>
            <div class="big">R$ {despesa:.2f}</div>
        </div>

        <div class="card">
            <h2>Lucro</h2>
            <div class="big">R$ {lucro:.2f}</div>
        </div>

        <div class="card">
            <h2>Status</h2>
            <p>✅ Telegram online</p>
            <p>✅ Flask online</p>
            <p>✅ Railway online</p>
            <p>✅ SQLite ativo</p>
        </div>
    </div>

    <div class="card">
        <h2>Ações rápidas</h2>
        <a href="/criar">Criar pedido, lead, receita ou despesa</a><br>
        <a href="/buscar">Buscar informações</a>
    </div>
    """

    return layout(conteudo)


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if usuario == ADMIN_USER and senha == ADMIN_PASS:
            session["logado"] = True
            return redirect("/")

        erro = "<p style='color:red;'>Login incorreto.</p>"

    return f"""
    <html>
    <body style="background:#050505;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="background:#111;padding:40px;border-radius:20px;border:1px solid #333;width:330px;">
            <h1>🔥 StreetCore</h1>
            <p>V24 Master Panel</p>
            {erro}
            <form method="POST">
                <input name="usuario" placeholder="Usuário" style="width:100%;padding:14px;margin-bottom:12px;border-radius:10px;border:0;">
                <input name="senha" type="password" placeholder="Senha" style="width:100%;padding:14px;margin-bottom:12px;border-radius:10px;border:0;">
                <button style="width:100%;padding:14px;border:0;border-radius:10px;background:#00ff88;font-weight:bold;">Entrar</button>
            </form>
            <p>Usuário padrão: admin</p>
            <p>Senha padrão: streetcore</p>
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
    return jsonify({
        "status": "online",
        "version": "StreetCore OS V24 Master Panel"
    })


@app.route("/criar", methods=["GET", "POST"])
def criar_web():
    if not login_required():
        return redirect("/login")

    mensagem = ""

    if request.method == "POST":
        tipo = request.form.get("tipo")
        nome = request.form.get("nome")
        valor = request.form.get("valor")

        conn = db()
        cur = conn.cursor()

        if tipo == "pedido":
            cur.execute("INSERT INTO pedidos (nome) VALUES (?)", (nome,))
            mensagem = "Pedido criado."

        elif tipo == "lead":
            cur.execute("INSERT INTO leads (nome, origem) VALUES (?, ?)", (nome, "painel"))
            mensagem = "Lead criado."

        elif tipo == "receita":
            cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("receita", float(valor), nome))
            mensagem = "Receita adicionada."

        elif tipo == "despesa":
            cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("despesa", float(valor), nome))
            mensagem = "Despesa adicionada."

        conn.commit()
        conn.close()
        salvar_log(f"Ação web: {tipo} - {nome}")

    conteudo = f"""
    <h1>➕ Criar</h1>
    <div class="card">
        <p class="ok">{mensagem}</p>

        <form method="POST">
            <label>Tipo</label>
            <select name="tipo">
                <option value="pedido">Pedido</option>
                <option value="lead">Lead</option>
                <option value="receita">Receita</option>
                <option value="despesa">Despesa</option>
            </select>

            <label>Nome/Descrição</label>
            <input name="nome" placeholder="Ex: camiseta personalizada">

            <label>Valor, se for financeiro</label>
            <input name="valor" placeholder="Ex: 100">

            <button>Criar</button>
        </form>
    </div>
    """

    return layout(conteudo)


@app.route("/pedidos")
def pedidos_page():
    if not login_required():
        return redirect("/login")

    dados = listar("pedidos")

    linhas = "".join([
        f"""
        <tr>
            <td>{d[0]}</td>
            <td>{d[1]}</td>
            <td><span class="tag">{d[2]}</span></td>
            <td>{d[3]}</td>
            <td>
                <a href="/pedido-status/{d[0]}/em_producao">Produção</a> |
                <a href="/pedido-status/{d[0]}/finalizado">Finalizar</a>
            </td>
        </tr>
        """
        for d in dados
    ])

    conteudo = f"""
    <h1>📦 Pedidos</h1>
    <table>
        <tr>
            <th>ID</th>
            <th>Pedido</th>
            <th>Status</th>
            <th>Data</th>
            <th>Ações</th>
        </tr>
        {linhas}
    </table>
    """

    return layout(conteudo)


@app.route("/pedido-status/<int:pedido_id>/<status>")
def pedido_status(pedido_id, status):
    if not login_required():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET status=? WHERE id=?", (status, pedido_id))
    conn.commit()
    conn.close()

    salvar_log(f"Pedido {pedido_id} atualizado para {status}")

    return redirect("/pedidos")


@app.route("/leads")
def leads_page():
    if not login_required():
        return redirect("/login")

    dados = listar("leads")

    linhas = "".join([
        f"""
        <tr>
            <td>{d[0]}</td>
            <td>{d[1]}</td>
            <td>{d[2]}</td>
            <td><span class="tag">{d[3]}</span></td>
            <td>{d[4]}</td>
        </tr>
        """
        for d in dados
    ])

    conteudo = f"""
    <h1>🎯 Leads</h1>
    <table>
        <tr>
            <th>ID</th>
            <th>Nome</th>
            <th>Origem</th>
            <th>Status</th>
            <th>Data</th>
        </tr>
        {linhas}
    </table>
    """

    return layout(conteudo)


@app.route("/financeiro-web")
def financeiro_web():
    if not login_required():
        return redirect("/login")

    receita, despesa, lucro = financeiro()

    conteudo = f"""
    <h1>💵 Financeiro</h1>

    <div class="grid">
        <div class="card">
            <h2>Receita</h2>
            <div class="big">R$ {receita:.2f}</div>
        </div>

        <div class="card">
            <h2>Despesa</h2>
            <div class="big">R$ {despesa:.2f}</div>
        </div>

        <div class="card">
            <h2>Lucro</h2>
            <div class="big">R$ {lucro:.2f}</div>
        </div>
    </div>
    """

    return layout(conteudo)


@app.route("/buscar", methods=["GET", "POST"])
def buscar_page():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        termo = request.form.get("termo")
        pedidos, leads = buscar_geral(termo)

        resultado += "<h2>Pedidos encontrados</h2>"
        resultado += "<pre>" + ("\n".join([str(p) for p in pedidos]) or "Nenhum pedido.") + "</pre>"

        resultado += "<h2>Leads encontrados</h2>"
        resultado += "<pre>" + ("\n".join([str(l) for l in leads]) or "Nenhum lead.") + "</pre>"

    conteudo = f"""
    <h1>🔎 Buscar</h1>

    <div class="card">
        <form method="POST">
            <input name="termo" placeholder="Digite algo para buscar">
            <button>Buscar</button>
        </form>
    </div>

    <div class="card">
        {resultado}
    </div>
    """

    return layout(conteudo)


@app.route("/logs")
def logs_page():
    if not login_required():
        return redirect("/login")

    dados = listar("logs")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td></tr>"
        for d in dados
    ])

    conteudo = f"""
    <h1>🧾 Logs</h1>

    <table>
        <tr>
            <th>ID</th>
            <th>Mensagem</th>
            <th>Data</th>
        </tr>
        {linhas}
    </table>
    """

    return layout(conteudo)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V24 MASTER PANEL\n\n"
        "Comandos:\n"
        "/pedido camiseta personalizada\n"
        "/pedidos\n"
        "/pedido_status 1 finalizado\n"
        "/lead joao instagram\n"
        "/leads\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/post camisetas\n"
        "/status"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ StreetCore OS V24 online.")


async def pedido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)

    if not nome:
        await update.message.reply_text("Use assim: /pedido camiseta personalizada")
        return

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO pedidos (nome) VALUES (?)", (nome,))
    conn.commit()
    conn.close()

    salvar_log(f"Pedido criado: {nome}")
    await update.message.reply_text(f"📦 Pedido criado: {nome}")


async def pedidos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = listar("pedidos")
    texto = "\n".join([str(d) for d in dados]) or "Nenhum pedido."
    await update.message.reply_text(texto)


async def pedido_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /pedido_status 1 finalizado")
        return

    pedido_id = context.args[0]
    status_novo = " ".join(context.args[1:])

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET status=? WHERE id=?", (status_novo, pedido_id))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Pedido #{pedido_id} atualizado para {status_novo}")


async def lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use assim: /lead joao instagram")
        return

    nome = context.args[0]
    origem = " ".join(context.args[1:]) or "manual"

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO leads (nome, origem) VALUES (?, ?)",
        (nome, origem)
    )
    conn.commit()
    conn.close()

    salvar_log(f"Lead criado: {nome}")
    await update.message.reply_text(f"🎯 Lead criado: {nome}")


async def leads_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = listar("leads")
    texto = "\n".join([str(d) for d in dados]) or "Nenhum lead."
    await update.message.reply_text(texto)


async def receita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0].replace(",", "."))
    except Exception:
        await update.message.reply_text("Use assim: /receita 100")
        return

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)",
        ("receita", valor, "telegram")
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"💰 Receita adicionada: R$ {valor:.2f}")


async def despesa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0].replace(",", "."))
    except Exception:
        await update.message.reply_text("Use assim: /despesa 50")
        return

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)",
        ("despesa", valor, "telegram")
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"💸 Despesa adicionada: R$ {valor:.2f}")


async def financeiro_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    receita_total, despesa_total, lucro = financeiro()

    await update.message.reply_text(
        f"💵 FINANCEIRO\n\n"
        f"Receita: R$ {receita_total:.2f}\n"
        f"Despesa: R$ {despesa_total:.2f}\n"
        f"Lucro: R$ {lucro:.2f}"
    )


async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"

    texto = (
        f"🔥 POST PRONTO - {tema.upper()}\n\n"
        "Sua marca precisa aparecer com presença.\n"
        "A Street Graff cria camisetas, adesivos, canecas, panfletos e brindes personalizados.\n\n"
        "📲 Chama no direct e peça seu orçamento.\n\n"
        "#streetgraff #personalizados #camisetaspersonalizadas #adesivospersonalizados"
    )

    await update.message.reply_text(texto)


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensagem = update.message.text
    salvar_log(mensagem)

    await update.message.reply_text(
        "🤖 STREETCORE IA V24\n\n"
        "Recebi sua mensagem. Use /start para ver os comandos."
    )


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("status", status))
    bot.add_handler(CommandHandler("pedido", pedido))
    bot.add_handler(CommandHandler("pedidos", pedidos_cmd))
    bot.add_handler(CommandHandler("pedido_status", pedido_status_cmd))
    bot.add_handler(CommandHandler("lead", lead))
    bot.add_handler(CommandHandler("leads", leads_cmd))
    bot.add_handler(CommandHandler("receita", receita))
    bot.add_handler(CommandHandler("despesa", despesa))
    bot.add_handler(CommandHandler("financeiro", financeiro_cmd))
    bot.add_handler(CommandHandler("post", post))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V24...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V24")

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