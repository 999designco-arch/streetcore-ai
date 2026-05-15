import os
import sqlite3
import threading
import asyncio
from datetime import datetime
from flask import Flask, jsonify, request, redirect, session, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v26-free")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")

DB_PATH = "streetcore_v26.db"

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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT,
            tipo TEXT,
            texto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            valor TEXT,
            status TEXT DEFAULT 'ativa',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agenda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            data TEXT,
            status TEXT DEFAULT 'pendente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT,
            valor REAL,
            status TEXT DEFAULT 'aberto',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Banco V26 iniciado.")


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


def contar_status_leads(status):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM leads WHERE status=?", (status,))
    total = cur.fetchone()[0]
    conn.close()
    return total


def listar_leads_status(status):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, nome, origem, status, criado_em FROM leads WHERE status=? ORDER BY id DESC LIMIT 50",
        (status,)
    )
    dados = cur.fetchall()
    conn.close()
    return dados


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

    quantidade = 1

    for palavra in texto.split():
        if palavra.isdigit():
            quantidade = int(palavra)
            break

    return base * quantidade


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


def gerar_campanha(tema):
    return f"{gerar_post(tema)}\n\n---\n\n{gerar_story(tema)}\n\n---\n\n{gerar_reels(tema)}"


def relatorio_operacional():
    receita, despesa, lucro = financeiro()

    return (
        "📊 RELATÓRIO OPERACIONAL V26\n\n"
        f"Pedidos: {contar('pedidos')}\n"
        f"Leads: {contar('leads')}\n"
        f"Conteúdos: {contar('conteudos')}\n"
        f"Metas: {contar('metas')}\n"
        f"Agenda: {contar('agenda')}\n"
        f"Orçamentos: {contar('orcamentos')}\n\n"
        f"Receita: R$ {receita:.2f}\n"
        f"Despesa: R$ {despesa:.2f}\n"
        f"Lucro: R$ {lucro:.2f}\n\n"
        "Decisão sugerida:\n"
        "✅ gerar mais leads\n"
        "✅ publicar reels\n"
        "✅ atualizar status dos pedidos\n"
        "✅ revisar orçamento aberto\n"
        "✅ acompanhar lucro"
    )


def layout(conteudo):
    return f"""
    <html>
    <head>
        <title>StreetCore OS V26</title>
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
                width:250px;
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
                margin-left:300px;
                padding:30px;
            }}
            .grid {{
                display:grid;
                grid-template-columns:repeat(auto-fit,minmax(230px,1fr));
                gap:18px;
            }}
            .kanban {{
                display:grid;
                grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
                gap:15px;
            }}
            .card {{
                background:#111;
                border:1px solid #333;
                border-radius:18px;
                padding:22px;
                margin-bottom:18px;
            }}
            .lead-card {{
                background:#171717;
                border:1px solid #333;
                border-radius:14px;
                padding:14px;
                margin-bottom:12px;
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
            <a href="/kanban">Kanban CRM</a>
            <a href="/pedidos">Pedidos</a>
            <a href="/leads">Leads</a>
            <a href="/financeiro-web">Financeiro</a>
            <a href="/conteudo">Gerador IA</a>
            <a href="/conteudos">Conteúdos</a>
            <a href="/metas">Metas</a>
            <a href="/agenda">Agenda</a>
            <a href="/orcamentos">Orçamentos</a>
            <a href="/decisao">Painel de Decisão</a>
            <a href="/criar">Criar</a>
            <a href="/buscar">Buscar</a>
            <a href="/backup">Backup</a>
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

    conteudo = f"""
    <h1>🔥 STREETCORE OS V26 ULTRA PANEL</h1>
    <p class="ok">Painel avançado com Kanban, metas, agenda, orçamentos e decisão.</p>

    <div class="grid">
        <div class="card"><h2>Pedidos</h2><div class="big">{contar("pedidos")}</div></div>
        <div class="card"><h2>Leads</h2><div class="big">{contar("leads")}</div></div>
        <div class="card"><h2>Conteúdos</h2><div class="big">{contar("conteudos")}</div></div>
        <div class="card"><h2>Metas</h2><div class="big">{contar("metas")}</div></div>
        <div class="card"><h2>Agenda</h2><div class="big">{contar("agenda")}</div></div>
        <div class="card"><h2>Orçamentos</h2><div class="big">{contar("orcamentos")}</div></div>
        <div class="card"><h2>Receita</h2><div class="big">R$ {receita:.2f}</div></div>
        <div class="card"><h2>Lucro</h2><div class="big">R$ {lucro:.2f}</div></div>
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
            <p>V26 Ultra Panel</p>
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
    return jsonify({"status": "online", "version": "StreetCore OS V26 Ultra Panel"})


@app.route("/kanban")
def kanban():
    if not login_required():
        return redirect("/login")

    status_list = ["novo", "contatado", "orcamento", "convertido"]

    colunas = ""

    for status in status_list:
        leads = listar_leads_status(status)

        cards = "".join([
            f"""
            <div class="lead-card">
                <strong>#{l[0]} - {l[1]}</strong>
                <p>Origem: {l[2]}</p>
                <p>Status: {l[3]}</p>
                <a href="/lead-status/{l[0]}/novo">Novo</a> |
                <a href="/lead-status/{l[0]}/contatado">Contatado</a> |
                <a href="/lead-status/{l[0]}/orcamento">Orçamento</a> |
                <a href="/lead-status/{l[0]}/convertido">Convertido</a>
            </div>
            """
            for l in leads
        ])

        colunas += f"""
        <div class="card">
            <h2>{status.upper()}</h2>
            {cards}
        </div>
        """

    return layout(f"""
    <h1>🧩 Kanban CRM</h1>
    <div class="kanban">
        {colunas}
    </div>
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
            resultado = gerar_campanha(tema)

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


@app.route("/conteudos")
def conteudos_page():
    if not login_required():
        return redirect("/login")

    dados = listar("conteudos")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td><pre>{d[3]}</pre></td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🧠 Conteúdos salvos</h1>
    <table>
        <tr><th>ID</th><th>Tema</th><th>Tipo</th><th>Texto</th><th>Data</th></tr>
        {linhas}
    </table>
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

        elif tipo == "meta":
            cur.execute("INSERT INTO metas (nome, valor) VALUES (?, ?)", (nome, valor))
            mensagem = "Meta criada."

        elif tipo == "agenda":
            cur.execute("INSERT INTO agenda (titulo, data) VALUES (?, ?)", (nome, valor))
            mensagem = "Evento criado."

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
                <option value="meta">Meta</option>
                <option value="agenda">Agenda</option>
                <option value="orcamento">Orçamento</option>
            </select>

            <label>Nome/Descrição</label>
            <input name="nome" placeholder="Ex: camiseta personalizada">

            <label>Valor/Data</label>
            <input name="valor" placeholder="Ex: 100 ou 20/05 14h">

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

    return layout(f"""
    <h1>📦 Pedidos</h1>
    <a href="/export/pedidos">Exportar CSV</a><br><br>
    <table>
        <tr><th>ID</th><th>Pedido</th><th>Status</th><th>Data</th><th>Ações</th></tr>
        {linhas}
    </table>
    """)


@app.route("/pedido-status/<int:pedido_id>/<status>")
def pedido_status(pedido_id, status):
    if not login_required():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET status=? WHERE id=?", (status, pedido_id))
    conn.commit()
    conn.close()

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
            <td>
                <a href="/lead-status/{d[0]}/contatado">Contatado</a> |
                <a href="/lead-status/{d[0]}/orcamento">Orçamento</a> |
                <a href="/lead-status/{d[0]}/convertido">Convertido</a>
            </td>
        </tr>
        """
        for d in dados
    ])

    return layout(f"""
    <h1>🎯 Leads</h1>
    <a href="/export/leads">Exportar CSV</a><br><br>
    <table>
        <tr><th>ID</th><th>Nome</th><th>Origem</th><th>Status</th><th>Data</th><th>Ações</th></tr>
        {linhas}
    </table>
    """)


@app.route("/lead-status/<int:lead_id>/<status>")
def lead_status(lead_id, status):
    if not login_required():
        return redirect("/login")

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE leads SET status=? WHERE id=?", (status, lead_id))
    conn.commit()
    conn.close()

    return redirect("/kanban")


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

    dados = listar("metas")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🎯 Metas</h1>
    <table>
        <tr><th>ID</th><th>Meta</th><th>Valor</th><th>Status</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/agenda")
def agenda_page():
    if not login_required():
        return redirect("/login")

    dados = listar("agenda")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>📅 Agenda</h1>
    <table>
        <tr><th>ID</th><th>Título</th><th>Data</th><th>Status</th><th>Criado</th></tr>
        {linhas}
    </table>
    """)


@app.route("/orcamentos")
def orcamentos_page():
    if not login_required():
        return redirect("/login")

    dados = listar("orcamentos")

    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>R$ {d[2]:.2f}</td><td>{d[3]}</td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🧾 Orçamentos</h1>
    <table>
        <tr><th>ID</th><th>Descrição</th><th>Valor</th><th>Status</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/decisao")
def decisao_page():
    if not login_required():
        return redirect("/login")

    relatorio = relatorio_operacional()

    return layout(f"""
    <h1>🧠 Painel de Decisão</h1>
    <div class="card">
        <pre>{relatorio}</pre>
    </div>
    """)


@app.route("/buscar", methods=["GET", "POST"])
def buscar_page():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        termo = request.form.get("termo")
        termo_like = f"%{termo}%"

        conn = db()
        cur = conn.cursor()
        cur.execute("SELECT id,nome,status,criado_em FROM pedidos WHERE nome LIKE ?", (termo_like,))
        pedidos = cur.fetchall()

        cur.execute("SELECT id,nome,origem,status,criado_em FROM leads WHERE nome LIKE ? OR origem LIKE ?", (termo_like, termo_like))
        leads = cur.fetchall()
        conn.close()

        resultado = f"<h2>Pedidos</h2><pre>{pedidos}</pre><h2>Leads</h2><pre>{leads}</pre>"

    return layout(f"""
    <h1>🔎 Buscar</h1>
    <div class="card">
        <form method="POST">
            <input name="termo" placeholder="Digite algo para buscar">
            <button>Buscar</button>
        </form>
    </div>
    <div class="card">{resultado}</div>
    """)


@app.route("/backup")
def backup_page():
    if not login_required():
        return redirect("/login")

    nome = f"backup_v26_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

    with open(DB_PATH, "rb") as origem:
        conteudo = origem.read()

    return Response(
        conteudo,
        mimetype="application/octet-stream",
        headers={"Content-Disposition": f"attachment;filename={nome}"}
    )


@app.route("/export/<tabela>")
def export_csv(tabela):
    if not login_required():
        return redirect("/login")

    if tabela not in ["pedidos", "leads", "financeiro", "conteudos", "metas", "agenda", "orcamentos"]:
        return "Tabela não permitida."

    conn = db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {tabela}")
    dados = cur.fetchall()
    colunas = [desc[0] for desc in cur.description]
    conn.close()

    def gerar():
        yield ",".join(colunas) + "\n"
        for linha in dados:
            yield ",".join([str(x).replace(",", " ") for x in linha]) + "\n"

    return Response(
        gerar(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={tabela}.csv"}
    )


@app.route("/logs")
def logs_page():
    if not login_required():
        return redirect("/login")

    dados = listar("logs")
    linhas = "".join([f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td></tr>" for d in dados])

    return layout(f"""
    <h1>🧾 Logs</h1>
    <table><tr><th>ID</th><th>Mensagem</th><th>Data</th></tr>{linhas}</table>
    """)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V26 ULTRA PANEL\n\n"
        "/pedido camiseta personalizada\n"
        "/pedidos\n"
        "/pedido_status 1 finalizado\n"
        "/lead joao instagram\n"
        "/leads\n"
        "/lead_status 1 convertido\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/meta vender_1000 1000\n"
        "/metas\n"
        "/agenda reunião 20/05\n"
        "/agendas\n"
        "/orcamento 10 camisetas\n"
        "/orcamentos\n"
        "/relatorio\n"
        "/post camisetas\n"
        "/story adesivos\n"
        "/reels canecas\n"
        "/campanha street graff\n"
        "/status"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ StreetCore OS V26 online.")


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

    await update.message.reply_text(f"📦 Pedido criado: {nome}")


async def pedidos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(listar("pedidos")))


async def pedido_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /pedido_status 1 finalizado")
        return

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET status=? WHERE id=?", (" ".join(context.args[1:]), context.args[0]))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Pedido atualizado.")


async def lead(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use assim: /lead joao instagram")
        return

    nome = context.args[0]
    origem = " ".join(context.args[1:]) or "manual"

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO leads (nome, origem) VALUES (?, ?)", (nome, origem))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🎯 Lead criado: {nome}")


async def leads_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(listar("leads")))


async def lead_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /lead_status 1 convertido")
        return

    conn = db()
    cur = conn.cursor()
    cur.execute("UPDATE leads SET status=? WHERE id=?", (" ".join(context.args[1:]), context.args[0]))
    conn.commit()
    conn.close()

    await update.message.reply_text("✅ Lead atualizado.")


async def receita(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0].replace(",", "."))
    except Exception:
        await update.message.reply_text("Use assim: /receita 100")
        return

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("receita", valor, "telegram"))
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
    cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("despesa", valor, "telegram"))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"💸 Despesa adicionada: R$ {valor:.2f}")


async def financeiro_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r, d, l = financeiro()
    await update.message.reply_text(f"💵 FINANCEIRO\nReceita: R$ {r:.2f}\nDespesa: R$ {d:.2f}\nLucro: R$ {l:.2f}")


async def meta_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /meta vender_1000 1000")
        return

    nome = context.args[0]
    valor = " ".join(context.args[1:])

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO metas (nome, valor) VALUES (?, ?)", (nome, valor))
    conn.commit()
    conn.close()

    await update.message.reply_text("🎯 Meta criada.")


async def metas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(listar("metas")))


async def agenda_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Use assim: /agenda reunião 20/05")
        return

    titulo = context.args[0]
    data = " ".join(context.args[1:])

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO agenda (titulo, data) VALUES (?, ?)", (titulo, data))
    conn.commit()
    conn.close()

    await update.message.reply_text("📅 Evento criado.")


async def agendas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(listar("agenda")))


async def orcamento_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    descricao = " ".join(context.args)

    if not descricao:
        await update.message.reply_text("Use assim: /orcamento 10 camisetas")
        return

    valor = calcular_orcamento(descricao)

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO orcamentos (descricao, valor) VALUES (?, ?)", (descricao, valor))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"🧾 Orçamento criado: R$ {valor:.2f}")


async def orcamentos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(str(listar("orcamentos")))


async def relatorio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(relatorio_operacional())


async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_post(" ".join(context.args) or "Street Graff"))


async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_story(" ".join(context.args) or "Street Graff"))


async def reels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_reels(" ".join(context.args) or "Street Graff"))


async def campanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(gerar_campanha(" ".join(context.args) or "Street Graff"))


async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    salvar_log(update.message.text)
    await update.message.reply_text("🤖 StreetCore IA V26 recebeu. Use /start.")


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("status", status))
    bot.add_handler(CommandHandler("pedido", pedido))
    bot.add_handler(CommandHandler("pedidos", pedidos_cmd))
    bot.add_handler(CommandHandler("pedido_status", pedido_status_cmd))
    bot.add_handler(CommandHandler("lead", lead))
    bot.add_handler(CommandHandler("leads", leads_cmd))
    bot.add_handler(CommandHandler("lead_status", lead_status_cmd))
    bot.add_handler(CommandHandler("receita", receita))
    bot.add_handler(CommandHandler("despesa", despesa))
    bot.add_handler(CommandHandler("financeiro", financeiro_cmd))
    bot.add_handler(CommandHandler("meta", meta_cmd))
    bot.add_handler(CommandHandler("metas", metas_cmd))
    bot.add_handler(CommandHandler("agenda", agenda_cmd))
    bot.add_handler(CommandHandler("agendas", agendas_cmd))
    bot.add_handler(CommandHandler("orcamento", orcamento_cmd))
    bot.add_handler(CommandHandler("orcamentos", orcamentos_cmd))
    bot.add_handler(CommandHandler("relatorio", relatorio_cmd))
    bot.add_handler(CommandHandler("post", post))
    bot.add_handler(CommandHandler("story", story))
    bot.add_handler(CommandHandler("reels", reels))
    bot.add_handler(CommandHandler("campanha", campanha))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V26...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V26")

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
