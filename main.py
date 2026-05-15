import os
import sqlite3
import threading
import asyncio
from flask import Flask, jsonify, request, redirect, session
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v23-free")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")

DB_PATH = "streetcore_v23.db"

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
    print("✅ Banco V23 iniciado.")


def contar(tabela):
    conn = db()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {tabela}")
    total = cur.fetchone()[0]
    conn.close()
    return total


def financeiro():
    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'")
    receita = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'")
    despesa = cur.fetchone()[0] or 0

    conn.close()
    return receita, despesa, receita - despesa


def listar(tabela):
    conn = db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT 30")
    dados = cur.fetchall()
    conn.close()
    return dados


def salvar_log(msg):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO logs (mensagem) VALUES (?)", (msg,))
    conn.commit()
    conn.close()


def login_required():
    return session.get("logado") is True


def layout_base(conteudo):
    return f"""
    <html>
    <head>
        <title>StreetCore OS V23</title>
        <style>
            body {{
                margin:0;
                background:#050505;
                color:white;
                font-family:Arial, sans-serif;
            }}

            .sidebar {{
                position:fixed;
                left:0;
                top:0;
                bottom:0;
                width:230px;
                background:#0d0d0d;
                border-right:1px solid #222;
                padding:25px;
            }}

            .sidebar h2 {{
                color:#00ff88;
            }}

            .sidebar a {{
                display:block;
                color:white;
                text-decoration:none;
                margin:14px 0;
            }}

            .sidebar a:hover {{
                color:#00ff88;
            }}

            .main {{
                margin-left:280px;
                padding:30px;
            }}

            .grid {{
                display:grid;
                grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
                gap:18px;
            }}

            .card {{
                background:#111;
                border:1px solid #333;
                border-radius:18px;
                padding:22px;
            }}

            .big {{
                font-size:38px;
                color:#00ff88;
                font-weight:bold;
            }}

            .ok {{
                color:#00ff88;
                font-weight:bold;
            }}

            table {{
                width:100%;
                border-collapse:collapse;
                background:#111;
                border-radius:12px;
                overflow:hidden;
            }}

            th, td {{
                padding:12px;
                border-bottom:1px solid #333;
                text-align:left;
            }}

            input {{
                padding:12px;
                border-radius:10px;
                border:0;
                margin:6px;
                background:#1c1c1c;
                color:white;
            }}

            button {{
                padding:12px 18px;
                border:0;
                border-radius:10px;
                background:#00ff88;
                font-weight:bold;
            }}

            a {{
                color:#00ff88;
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
    <h1>🔥 STREETCORE OS V23 ENTERPRISE FREE</h1>
    <p class="ok">Painel visual profissional online.</p>

    <div class="grid">
        <div class="card">
            <h2>Pedidos</h2>
            <div class="big">{contar("pedidos")}</div>
        </div>

        <div class="card">
            <h2>Leads</h2>
            <div class="big">{contar("leads")}</div>
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
    """

    return layout_base(conteudo)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if usuario == ADMIN_USER and senha == ADMIN_PASS:
            session["logado"] = True
            return redirect("/")

        erro = "<p style='color:red;'>Login incorreto</p>"
    else:
        erro = ""

    return f"""
    <html>
    <body style="background:#050505;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh;">
        <div style="background:#111;padding:40px;border-radius:20px;border:1px solid #333;width:320px;">
            <h1>🔥 StreetCore</h1>
            <p>Painel V23 Enterprise Free</p>
            {erro}
            <form method="POST">
                <input name="usuario" placeholder="Usuário" style="width:100%;padding:14px;margin-bottom:12px;border-radius:10px;border:0;">
                <input name="senha" type="password" placeholder="Senha" style="width:100%;padding:14px;margin-bottom:12px;border-radius:10px;border:0;">
                <button style="width:100%;padding:14px;border:0;border-radius:10px;background:#00ff88;font-weight:bold;">Entrar</button>
            </form>
            <p>Usuário: admin</p>
            <p>Senha: streetcore</p>
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
        "version": "StreetCore OS V23 Enterprise Free"
    })


@app.route("/pedidos")
def pedidos_page():
    if not login_required():
        return redirect("/login")

    dados = listar("pedidos")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td></tr>"
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
        </tr>
        {linhas}
    </table>
    """

    return layout_base(conteudo)


@app.route("/leads")
def leads_page():
    if not login_required():
        return redirect("/login")

    dados = listar("leads")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td></tr>"
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

    return layout_base(conteudo)


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

    return layout_base(conteudo)


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

    return layout_base(conteudo)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V23 ENTERPRISE FREE\n\n"
        "Comandos:\n"
        "/pedido camiseta personalizada\n"
        "/pedidos\n"
        "/lead joao instagram\n"
        "/leads\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/post camisetas\n"
        "/status"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ StreetCore OS V23 online.")


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
        "INSERT INTO financeiro (tipo, valor) VALUES (?, ?)",
        ("receita", valor)
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
        "INSERT INTO financeiro (tipo, valor) VALUES (?, ?)",
        ("despesa", valor)
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
        "🤖 STREETCORE IA V23\n\n"
        "Recebi sua mensagem. Use /start para ver os comandos."
    )


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("status", status))
    bot.add_handler(CommandHandler("pedido", pedido))
    bot.add_handler(CommandHandler("pedidos", pedidos_cmd))
    bot.add_handler(CommandHandler("lead", lead))
    bot.add_handler(CommandHandler("leads", leads_cmd))
    bot.add_handler(CommandHandler("receita", receita))
    bot.add_handler(CommandHandler("despesa", despesa))
    bot.add_handler(CommandHandler("financeiro", financeiro_cmd))
    bot.add_handler(CommandHandler("post", post))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V23...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V23")

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