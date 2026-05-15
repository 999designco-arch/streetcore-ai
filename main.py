import os
import sqlite3
import threading
import asyncio
from datetime import datetime
from flask import Flask, jsonify, request, redirect, session, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v27-free")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")

DB_PATH = "streetcore_v27.db"

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)
app.secret_key = SECRET_KEY


def db():
    return sqlite3.connect(DB_PATH)


def iniciar_banco():
    conn = db()
    cur = conn.cursor()

    tabelas = [
        """
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cliente TEXT,
            status TEXT DEFAULT 'novo',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            origem TEXT,
            status TEXT DEFAULT 'novo',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            contato TEXT,
            historico TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            valor REAL,
            descricao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT,
            tipo TEXT,
            texto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            valor TEXT,
            status TEXT DEFAULT 'ativa',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            data TEXT,
            status TEXT DEFAULT 'pendente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            valor REAL,
            status TEXT DEFAULT 'aberto',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS campanhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT,
            texto TEXT,
            status TEXT DEFAULT 'planejada',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tarefas_auto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarefa TEXT,
            status TEXT DEFAULT 'pendente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]

    for tabela in tabelas:
        cur.execute(tabela)

    conn.commit()
    conn.close()
    print("✅ Banco V27 iniciado.")


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
        "#streetgraff #personalizados #camisetaspersonalizadas #adesivospersonalizados #canecaspersonalizadas"
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


def gerar_campanha_texto(tema):
    return (
        f"🚀 CAMPANHA COMPLETA - {tema.upper()}\n\n"
        f"{gerar_post(tema)}\n\n---\n\n"
        f"{gerar_story(tema)}\n\n---\n\n"
        f"{gerar_reels(tema)}"
    )


def calcular_orcamento(descricao):
    texto = descricao.lower()

    base = 35

    if "caneca" in texto:
        base = 30
    elif "adesivo" in texto:
        base = 8
    elif "panfleto" in texto:
        base = 80
    elif "brinde" in texto:
        base = 20
    elif "camiseta" in texto:
        base = 45

    quantidade = 1

    for palavra in texto.replace(",", " ").split():
        if palavra.isdigit():
            quantidade = int(palavra)
            break

    subtotal = base * quantidade

    taxa_arte = 20 if "arte" in texto or "design" in texto else 0
    urgencia = 30 if "urgente" in texto else 0

    total = subtotal + taxa_arte + urgencia

    return total


def checklist_diario():
    return (
        "✅ CHECKLIST DIÁRIO STREETCORE\n\n"
        "1. Ver novos leads\n"
        "2. Atualizar status dos pedidos\n"
        "3. Conferir financeiro\n"
        "4. Criar 1 post\n"
        "5. Criar 1 reels\n"
        "6. Responder clientes\n"
        "7. Revisar agenda\n"
        "8. Fazer backup\n"
        "9. Criar campanha do dia\n"
        "10. Fechar pelo menos 1 venda"
    )


def relatorio_operacional():
    receita, despesa, lucro = financeiro()

    return (
        "📊 RELATÓRIO OPERACIONAL V27\n\n"
        f"Pedidos: {contar('pedidos')}\n"
        f"Leads: {contar('leads')}\n"
        f"Clientes: {contar('clientes')}\n"
        f"Conteúdos: {contar('conteudos')}\n"
        f"Campanhas: {contar('campanhas')}\n"
        f"Metas: {contar('metas')}\n"
        f"Agenda: {contar('agenda')}\n"
        f"Orçamentos: {contar('orcamentos')}\n\n"
        f"Receita: R$ {receita:.2f}\n"
        f"Despesa: R$ {despesa:.2f}\n"
        f"Lucro: R$ {lucro:.2f}\n\n"
        "Decisão sugerida:\n"
        "✅ gerar campanha\n"
        "✅ captar leads\n"
        "✅ atualizar pedidos\n"
        "✅ fazer reels\n"
        "✅ revisar orçamentos abertos"
    )


def copiloto(pergunta):
    return (
        "🤖 COPILOTO OPERACIONAL V27\n\n"
        f"Pedido recebido: {pergunta}\n\n"
        "Minha decisão operacional:\n"
        "1. Criar campanha se precisar vender\n"
        "2. Criar lead se for cliente novo\n"
        "3. Criar pedido se já houve compra\n"
        "4. Registrar receita se houve pagamento\n"
        "5. Atualizar status se estiver em produção\n\n"
        f"{checklist_diario()}"
    )


def layout(conteudo):
    return f"""
    <html>
    <head>
        <title>StreetCore OS V27</title>
        <style>
            body {{
                margin:0;
                background:#050505;
                color:white;
                font-family:Arial, sans-serif;
            }}
            .sidebar {{
                position:fixed;
                top:0;
                left:0;
                bottom:0;
                width:260px;
                background:#0b0b0b;
                border-right:1px solid #222;
                padding:24px;
                overflow:auto;
            }}
            .sidebar h2 {{ color:#00ff88; }}
            .sidebar a {{
                display:block;
                color:white;
                text-decoration:none;
                margin:12px 0;
            }}
            .sidebar a:hover {{ color:#00ff88; }}
            .main {{
                margin-left:310px;
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
                margin-bottom:18px;
            }}
            .big {{
                color:#00ff88;
                font-size:38px;
                font-weight:bold;
            }}
            .ok {{ color:#00ff88; font-weight:bold; }}
            input, select, textarea {{
                padding:12px;
                border-radius:10px;
                border:0;
                margin:6px 0;
                width:100%;
                background:#1c1c1c;
                color:white;
            }}
            textarea {{ min-height:180px; }}
            button {{
                padding:12px 18px;
                border:0;
                border-radius:10px;
                background:#00ff88;
                font-weight:bold;
                cursor:pointer;
            }}
            table {{
                width:100%;
                border-collapse:collapse;
                background:#111;
                border-radius:14px;
                overflow:hidden;
            }}
            th, td {{
                padding:12px;
                border-bottom:1px solid #333;
                text-align:left;
            }}
            .tag {{
                background:#1f1f1f;
                padding:6px 10px;
                border-radius:8px;
            }}
            a {{ color:#00ff88; }}
            pre {{ white-space:pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🔥 StreetCore</h2>
            <a href="/">Dashboard</a>
            <a href="/copiloto">Copiloto</a>
            <a href="/hoje">O que fazer hoje</a>
            <a href="/campanhas">Campanhas</a>
            <a href="/clientes">Clientes</a>
            <a href="/pedidos">Pedidos</a>
            <a href="/leads">Leads</a>
            <a href="/financeiro-web">Financeiro</a>
            <a href="/conteudo">Gerador IA</a>
            <a href="/metas">Metas</a>
            <a href="/agenda">Agenda</a>
            <a href="/orcamentos">Orçamentos</a>
            <a href="/decisao">Painel de Decisão</a>
            <a href="/criar">Criar</a>
            <a href="/logs">Logs</a>
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

    return layout(f"""
    <h1>🔥 STREETCORE OS V27 MAX AUTOPILOT</h1>
    <p class="ok">Painel com copiloto, campanhas, clientes e checklist diário.</p>

    <div class="grid">
        <div class="card"><h2>Pedidos</h2><div class="big">{contar("pedidos")}</div></div>
        <div class="card"><h2>Leads</h2><div class="big">{contar("leads")}</div></div>
        <div class="card"><h2>Clientes</h2><div class="big">{contar("clientes")}</div></div>
        <div class="card"><h2>Campanhas</h2><div class="big">{contar("campanhas")}</div></div>
        <div class="card"><h2>Orçamentos</h2><div class="big">{contar("orcamentos")}</div></div>
        <div class="card"><h2>Receita</h2><div class="big">R$ {receita:.2f}</div></div>
        <div class="card"><h2>Despesa</h2><div class="big">R$ {despesa:.2f}</div></div>
        <div class="card"><h2>Lucro</h2><div class="big">R$ {lucro:.2f}</div></div>
    </div>

    <div class="card">
        <h2>Autopilot</h2>
        <pre>{checklist_diario()}</pre>
    </div>
    """)


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
            <p>V27 Max Autopilot</p>
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
    return jsonify({"status": "online", "version": "StreetCore OS V27 Max Autopilot"})


@app.route("/copiloto", methods=["GET", "POST"])
def copiloto_page():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        pergunta = request.form.get("pergunta") or ""
        resposta = copiloto(pergunta)

    return layout(f"""
    <h1>🤖 Copiloto Operacional</h1>
    <div class="card">
        <form method="POST">
            <label>O que você quer decidir?</label>
            <input name="pergunta" placeholder="Ex: como vender mais hoje?">
            <button>Analisar</button>
        </form>
    </div>
    <div class="card">
        <pre>{resposta}</pre>
    </div>
    """)


@app.route("/hoje")
def hoje_page():
    if not login_required():
        return redirect("/login")

    return layout(f"""
    <h1>✅ O que fazer hoje</h1>
    <div class="card">
        <pre>{checklist_diario()}</pre>
    </div>
    <div class="card">
        <h2>Relatório rápido</h2>
        <pre>{relatorio_operacional()}</pre>
    </div>
    """)


@app.route("/campanhas", methods=["GET", "POST"])
def campanhas_page():
    if not login_required():
        return redirect("/login")

    mensagem = ""

    if request.method == "POST":
        tema = request.form.get("tema") or "Street Graff"
        texto = gerar_campanha_texto(tema)

        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO campanhas (tema, texto) VALUES (?, ?)",
            (tema, texto)
        )
        conn.commit()
        conn.close()

        mensagem = "Campanha criada."

    dados = listar("campanhas")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td><pre>{d[2]}</pre></td><td>{d[3]}</td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🚀 Central de Campanhas</h1>

    <div class="card">
        <p class="ok">{mensagem}</p>
        <form method="POST">
            <input name="tema" placeholder="Tema da campanha">
            <button>Criar campanha</button>
        </form>
    </div>

    <table>
        <tr><th>ID</th><th>Tema</th><th>Texto</th><th>Status</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/clientes", methods=["GET", "POST"])
def clientes_page():
    if not login_required():
        return redirect("/login")

    mensagem = ""

    if request.method == "POST":
        nome = request.form.get("nome")
        contato = request.form.get("contato")
        historico = request.form.get("historico")

        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO clientes (nome, contato, historico) VALUES (?, ?, ?)",
            (nome, contato, historico)
        )
        conn.commit()
        conn.close()

        mensagem = "Cliente criado."

    dados = listar("clientes")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td><pre>{d[3]}</pre></td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>👤 Clientes</h1>

    <div class="card">
        <p class="ok">{mensagem}</p>
        <form method="POST">
            <input name="nome" placeholder="Nome">
            <input name="contato" placeholder="Contato">
            <textarea name="historico" placeholder="Histórico do cliente"></textarea>
            <button>Criar cliente</button>
        </form>
    </div>

    <table>
        <tr><th>ID</th><th>Nome</th><th>Contato</th><th>Histórico</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/conteudo", methods=["GET", "POST"])
def conteudo_web():
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
            resultado = gerar_campanha_texto(tema)

        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO conteudos (tema, tipo, texto) VALUES (?, ?, ?)",
            (tema, tipo, resultado)
        )
        conn.commit()
        conn.close()

    return layout(f"""
    <h1>🤖 Gerador IA de Conteúdo</h1>

    <div class="card">
        <form method="POST">
            <label>Tema</label>
            <input name="tema" placeholder="Ex: camisetas personalizadas">

            <label>Tipo</label>
            <select name="tipo">
                <option value="post">Post</option>
                <option value="story">Story</option>
                <option value="reels">Reels</option>
                <option value="campanha">Campanha completa</option>
            </select>

            <button>Gerar conteúdo</button>
        </form>
    </div>

    <div class="card">
        <h2>Resultado</h2>
        <textarea>{resultado}</textarea>
    </div>
    """)


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

        elif tipo == "orcamento":
            valor_calc = calcular_orcamento(nome)
            cur.execute("INSERT INTO orcamentos (descricao, valor) VALUES (?, ?)", (nome, valor_calc))
            mensagem = f"Orçamento criado: R$ {valor_calc:.2f}"

        conn.commit()
        conn.close()
        salvar_log(f"Ação web: {tipo} - {nome}")

    return layout(f"""
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
                <option value="orcamento">Orçamento</option>
            </select>

            <label>Nome/Descrição</label>
            <input name="nome" placeholder="Ex: camiseta personalizada">

            <label>Valor, se for financeiro</label>
            <input name="valor" placeholder="Ex: 100">

            <button>Criar</button>
        </form>
    </div>
    """)


@app.route("/pedidos")
def pedidos_page():
    if not login_required():
        return redirect("/login")

    dados = listar("pedidos")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td><span class='tag'>{d[3]}</span></td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>📦 Pedidos</h1>
    <table>
        <tr><th>ID</th><th>Pedido</th><th>Cliente</th><th>Status</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/leads")
def leads_page():
    if not login_required():
        return redirect("/login")

    dados = listar("leads")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🎯 Leads</h1>
    <table>
        <tr><th>ID</th><th>Nome</th><th>Origem</th><th>Status</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/financeiro-web")
def financeiro_web():
    if not login_required():
        return redirect("/login")

    receita, despesa, lucro = financeiro()

    return layout(f"""
    <h1>💵 Financeiro</h1>
    <div class="grid">
        <div class="card"><h2>Receita</h2><div class="big">R$ {receita:.2f}</div></div>
        <div class="card"><h2>Despesa</h2><div class="big">R$ {despesa:.2f}</div></div>
        <div class="card"><h2>Lucro</h2><div class="big">R$ {lucro:.2f}</div></div>
    </div>
    """)


@app.route("/metas")
def metas_page():
    if not login_required():
        return redirect("/login")

    return layout(f"<h1>🎯 Metas</h1><pre>{listar('metas')}</pre>")


@app.route("/agenda")
def agenda_page():
    if not login_required():
        return redirect("/login")

    return layout(f"<h1>📅 Agenda</h1><pre>{listar('agenda')}</pre>")


@app.route("/orcamentos")
def orcamentos_page():
    if not login_required():
        return redirect("/login")

    return layout(f"<h1>🧾 Orçamentos</h1><pre>{listar('orcamentos')}</pre>")


@app.route("/decisao")
def decisao_page():
    if not login_required():
        return redirect("/login")

    return layout(f"<h1>🧠 Painel de Decisão</h1><div class='card'><pre>{relatorio_operacional()}</pre></div>")


@app.route("/logs")
def logs_page():
    if not login_required():
        return redirect("/login")

    return layout(f"<h1>🧾 Logs</h1><pre>{listar('logs')}</pre>")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V27 MAX AUTOPILOT\n\n"
        "/copiloto como vender mais hoje\n"
        "/hoje\n"
        "/relatorio\n"
        "/campanha street graff\n"
        "/pedido camiseta personalizada\n"
        "/lead joao instagram\n"
        "/cliente joao 119999 pedido camiseta\n"
        "/orcamento 10 camisetas com arte\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/post camisetas\n"
        "/story adesivos\n"
        "/reels canecas\n"
        "/status"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ StreetCore OS V27 online.")


async def copiloto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(copiloto(" ".join(context.args)))


async def hoje_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(checklist_diario())


async def relatorio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(relatorio_operacional())


async def pedido_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO pedidos (nome) VALUES (?)", (nome,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"📦 Pedido criado: {nome}")


async def lead_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /lead joao instagram")
        return

    nome = context.args[0]
    origem = " ".join(context.args[1:]) or "manual"

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO leads (nome, origem) VALUES (?, ?)", (nome, origem))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🎯 Lead criado: {nome}")


async def cliente_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use: /cliente nome contato historico")
        return

    nome = context.args[0]
    contato = context.args[1]
    historico = " ".join(context.args[2:])

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clientes (nome, contato, historico) VALUES (?, ?, ?)",
        (nome, contato, historico)
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(f"👤 Cliente criado: {nome}")


async def orcamento_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = " ".join(context.args)
    valor = calcular_orcamento(descricao)

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO orcamentos (descricao, valor) VALUES (?, ?)", (descricao, valor))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🧾 Orçamento criado: R$ {valor:.2f}")


async def receita_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = float(context.args[0].replace(",", "."))
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("receita", valor, "telegram"))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"💰 Receita: R$ {valor:.2f}")


async def despesa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    valor = float(context.args[0].replace(",", "."))
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("despesa", valor, "telegram"))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"💸 Despesa: R$ {valor:.2f}")


async def financeiro_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r, d, l = financeiro()
    await update.message.reply_text(f"💵 FINANCEIRO\nReceita: R$ {r:.2f}\nDespesa: R$ {d:.2f}\nLucro: R$ {l:.2f}")


async def campanha_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args) or "Street Graff"
    texto = gerar_campanha_texto(tema)

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO campanhas (tema, texto) VALUES (?, ?)", (tema, texto))
    conn.commit()
    conn.close()

    await update.message.reply_text(texto)


async def post_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_post(" ".join(context.args) or "Street Graff"))


async def story_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_story(" ".join(context.args) or "Street Graff"))


async def reels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_reels(" ".join(context.args) or "Street Graff"))


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salvar_log(update.message.text)
    await update.message.reply_text("🤖 StreetCore IA V27 recebeu. Use /start.")


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("status", status))
    bot.add_handler(CommandHandler("copiloto", copiloto_cmd))
    bot.add_handler(CommandHandler("hoje", hoje_cmd))
    bot.add_handler(CommandHandler("relatorio", relatorio_cmd))
    bot.add_handler(CommandHandler("pedido", pedido_cmd))
    bot.add_handler(CommandHandler("lead", lead_cmd))
    bot.add_handler(CommandHandler("cliente", cliente_cmd))
    bot.add_handler(CommandHandler("orcamento", orcamento_cmd))
    bot.add_handler(CommandHandler("receita", receita_cmd))
    bot.add_handler(CommandHandler("despesa", despesa_cmd))
    bot.add_handler(CommandHandler("financeiro", financeiro_cmd))
    bot.add_handler(CommandHandler("campanha", campanha_cmd))
    bot.add_handler(CommandHandler("post", post_cmd))
    bot.add_handler(CommandHandler("story", story_cmd))
    bot.add_handler(CommandHandler("reels", reels_cmd))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V27...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V27")

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
