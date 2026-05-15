import os
import sqlite3
import threading
import asyncio
from datetime import datetime
from flask import Flask, jsonify, request, redirect, session, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v29-free")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")
DB_PATH = "streetcore_v29.db"

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
        """CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            cliente TEXT,
            status TEXT DEFAULT 'novo',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            origem TEXT,
            status TEXT DEFAULT 'novo',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            contato TEXT,
            historico TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            valor REAL,
            descricao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS conteudos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT,
            tipo TEXT,
            texto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS campanhas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT,
            texto TEXT,
            status TEXT DEFAULT 'planejada',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            status TEXT DEFAULT 'pendente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS producao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT,
            cliente TEXT,
            status TEXT DEFAULT 'aguardando',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT,
            quantidade INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS fornecedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            contato TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS notificacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mensagem TEXT,
            status TEXT DEFAULT 'nova',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS documentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            tipo TEXT,
            texto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS conhecimento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            texto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS propostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            descricao TEXT,
            valor REAL,
            texto TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS atendimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            pergunta TEXT,
            resposta TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    ]

    for tabela in tabelas:
        cur.execute(tabela)

    conn.commit()
    conn.close()
    print("✅ Banco V29 AI OFFICE iniciado.")


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


def calcular_orcamento(descricao):
    texto = descricao.lower()
    base = 35

    if "camiseta" in texto:
        base = 45
    elif "caneca" in texto:
        base = 30
    elif "adesivo" in texto:
        base = 8
    elif "panfleto" in texto:
        base = 80
    elif "brinde" in texto:
        base = 20

    quantidade = 1
    for palavra in texto.replace(",", " ").split():
        if palavra.isdigit():
            quantidade = int(palavra)
            break

    adicional_arte = 20 if "arte" in texto or "design" in texto else 0
    urgencia = 30 if "urgente" in texto else 0

    return (base * quantidade) + adicional_arte + urgencia


def gerar_proposta(cliente, descricao):
    valor = calcular_orcamento(descricao)

    return (
        f"🧾 PROPOSTA COMERCIAL - STREET GRAFF\n\n"
        f"Cliente: {cliente}\n"
        f"Solicitação: {descricao}\n\n"
        "Itens inclusos:\n"
        "- atendimento personalizado;\n"
        "- produção sob medida;\n"
        "- personalização conforme pedido;\n"
        "- revisão básica antes da produção.\n\n"
        f"Valor estimado: R$ {valor:.2f}\n\n"
        "Prazo estimado: 5 dias úteis + transporte.\n"
        "Pagamento: somente via PIX.\n\n"
        "Para confirmar o pedido, envie a arte/referência e confirme a quantidade."
    )


def gerar_contrato(cliente, servico, valor):
    return (
        f"📄 CONTRATO SIMPLES DE SERVIÇO\n\n"
        f"Contratante: {cliente}\n"
        "Contratada: Street Graff\n\n"
        f"Serviço: {servico}\n"
        f"Valor combinado: R$ {valor}\n\n"
        "Condições:\n"
        "1. O pagamento será realizado via PIX.\n"
        "2. O prazo de produção é de 5 dias úteis após confirmação.\n"
        "3. Alterações após aprovação podem gerar custos adicionais.\n"
        "4. A produção inicia após confirmação do pagamento e detalhes finais.\n\n"
        "Este é um modelo simples gerado automaticamente."
    )


def faq_resposta(pergunta):
    p = pergunta.lower()

    if "prazo" in p:
        return "O prazo padrão é de 5 dias úteis de produção + tempo da transportadora."
    if "pagamento" in p or "pix" in p:
        return "O pagamento é somente via PIX."
    if "camiseta" in p:
        return "Fazemos camisetas personalizadas sob encomenda. O preço varia por quantidade e arte."
    if "caneca" in p:
        return "Fazemos canecas personalizadas. O valor depende da quantidade e personalização."
    if "adesivo" in p:
        return "Fazemos adesivos personalizados em diferentes tamanhos e quantidades."
    if "panfleto" in p:
        return "Fazemos panfletos personalizados para divulgação, eventos e empresas."
    if "brinde" in p:
        return "Fazemos brindes personalizados conforme a necessidade do cliente."
    if "orçamento" in p or "orcamento" in p:
        return "Para orçamento, informe produto, quantidade, tamanho e se já possui arte."

    return (
        "Posso ajudar com orçamento, prazo, pagamento, camisetas, adesivos, canecas, panfletos e brindes. "
        "Envie produto + quantidade para uma resposta melhor."
    )


def atendimento_automatico(cliente, pergunta):
    resposta = faq_resposta(pergunta)

    conn = db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO atendimentos (cliente, pergunta, resposta) VALUES (?, ?, ?)",
        (cliente, pergunta, resposta)
    )
    conn.commit()
    conn.close()

    return resposta


def busca_sistema(termo):
    termo_like = f"%{termo}%"
    conn = db()
    cur = conn.cursor()

    resultados = []

    buscas = [
        ("pedidos", "SELECT id,nome,cliente,status,criado_em FROM pedidos WHERE nome LIKE ? OR cliente LIKE ?"),
        ("leads", "SELECT id,nome,origem,status,criado_em FROM leads WHERE nome LIKE ? OR origem LIKE ?"),
        ("clientes", "SELECT id,nome,contato,historico,criado_em FROM clientes WHERE nome LIKE ? OR contato LIKE ? OR historico LIKE ?"),
        ("documentos", "SELECT id,titulo,tipo,criado_em FROM documentos WHERE titulo LIKE ? OR texto LIKE ?"),
        ("conhecimento", "SELECT id,titulo,criado_em FROM conhecimento WHERE titulo LIKE ? OR texto LIKE ?"),
    ]

    for nome, query in buscas:
        try:
            if nome == "clientes":
                cur.execute(query, (termo_like, termo_like, termo_like))
            else:
                cur.execute(query, (termo_like, termo_like))
            dados = cur.fetchall()
            if dados:
                resultados.append(f"\n{nome.upper()}:\n" + "\n".join(map(str, dados)))
        except Exception:
            pass

    conn.close()

    if not resultados:
        return "Nenhum resultado encontrado."

    return "\n".join(resultados)


def checklist():
    return (
        "✅ CHECKLIST AI OFFICE\n\n"
        "1. Ver leads novos\n"
        "2. Responder atendimentos\n"
        "3. Criar propostas pendentes\n"
        "4. Atualizar pedidos\n"
        "5. Conferir produção\n"
        "6. Registrar financeiro\n"
        "7. Criar conteúdo do dia\n"
        "8. Salvar conhecimento importante\n"
        "9. Fazer backup\n"
        "10. Fechar vendas"
    )


def relatorio():
    r, d, l = financeiro()
    return (
        "📊 RELATÓRIO V29 AI OFFICE\n\n"
        f"Pedidos: {contar('pedidos')}\n"
        f"Leads: {contar('leads')}\n"
        f"Clientes: {contar('clientes')}\n"
        f"Tarefas: {contar('tarefas')}\n"
        f"Documentos: {contar('documentos')}\n"
        f"Conhecimentos: {contar('conhecimento')}\n"
        f"Propostas: {contar('propostas')}\n"
        f"Atendimentos: {contar('atendimentos')}\n\n"
        f"Receita: R$ {r:.2f}\n"
        f"Despesa: R$ {d:.2f}\n"
        f"Lucro: R$ {l:.2f}\n\n"
        "Decisão: priorizar propostas, atendimento rápido e fechamento de pedidos."
    )


def layout(conteudo):
    return f"""
    <html>
    <head>
        <title>StreetCore OS V29</title>
        <style>
            body {{ margin:0; background:#050505; color:white; font-family:Arial; }}
            .sidebar {{
                position:fixed; top:0; left:0; bottom:0; width:270px;
                background:#0b0b0b; border-right:1px solid #222; padding:24px; overflow:auto;
            }}
            .sidebar h2 {{ color:#00ff88; }}
            .sidebar a {{ display:block; color:white; text-decoration:none; margin:12px 0; }}
            .sidebar a:hover {{ color:#00ff88; }}
            .main {{ margin-left:320px; padding:30px; }}
            .grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:18px; }}
            .card {{ background:#111; border:1px solid #333; border-radius:18px; padding:22px; margin-bottom:18px; }}
            .big {{ color:#00ff88; font-size:36px; font-weight:bold; }}
            .ok {{ color:#00ff88; font-weight:bold; }}
            input, select, textarea {{
                padding:12px; border-radius:10px; border:0; margin:6px 0;
                width:100%; background:#1c1c1c; color:white;
            }}
            textarea {{ min-height:170px; }}
            button {{
                padding:12px 18px; border:0; border-radius:10px;
                background:#00ff88; font-weight:bold; cursor:pointer;
            }}
            table {{ width:100%; border-collapse:collapse; background:#111; border-radius:14px; overflow:hidden; }}
            th, td {{ padding:12px; border-bottom:1px solid #333; text-align:left; vertical-align:top; }}
            .tag {{ background:#1f1f1f; padding:6px 10px; border-radius:8px; }}
            a {{ color:#00ff88; }}
            pre {{ white-space:pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🔥 StreetCore</h2>
            <a href="/">Dashboard</a>
            <a href="/office">AI Office</a>
            <a href="/atendimento">Atendimento</a>
            <a href="/propostas">Propostas</a>
            <a href="/documentos">Documentos</a>
            <a href="/conhecimento">Conhecimento</a>
            <a href="/buscar">Busca Geral</a>
            <a href="/command">Command Center</a>
            <a href="/tarefas">Tarefas</a>
            <a href="/producao">Produção</a>
            <a href="/estoque">Estoque</a>
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
    <h1>🔥 STREETCORE OS V29 AI OFFICE</h1>
    <p class="ok">Centro de documentos, propostas, atendimento e conhecimento.</p>

    <div class="grid">
        <div class="card"><h2>Pedidos</h2><div class="big">{contar("pedidos")}</div></div>
        <div class="card"><h2>Leads</h2><div class="big">{contar("leads")}</div></div>
        <div class="card"><h2>Clientes</h2><div class="big">{contar("clientes")}</div></div>
        <div class="card"><h2>Propostas</h2><div class="big">{contar("propostas")}</div></div>
        <div class="card"><h2>Documentos</h2><div class="big">{contar("documentos")}</div></div>
        <div class="card"><h2>Atendimentos</h2><div class="big">{contar("atendimentos")}</div></div>
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
            <p>V29 AI Office</p>
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
    return jsonify({"status": "online", "version": "StreetCore OS V29 AI Office"})


@app.route("/office")
def office():
    if not login_required():
        return redirect("/login")

    return layout(f"""
    <h1>🏢 AI Office</h1>
    <div class="grid">
        <div class="card"><h2>Documentos</h2><div class="big">{contar("documentos")}</div><a href="/documentos">Abrir</a></div>
        <div class="card"><h2>Conhecimento</h2><div class="big">{contar("conhecimento")}</div><a href="/conhecimento">Abrir</a></div>
        <div class="card"><h2>Propostas</h2><div class="big">{contar("propostas")}</div><a href="/propostas">Abrir</a></div>
        <div class="card"><h2>Atendimento</h2><div class="big">{contar("atendimentos")}</div><a href="/atendimento">Abrir</a></div>
    </div>
    <div class="card"><pre>{relatorio()}</pre></div>
    """)


@app.route("/documentos", methods=["GET", "POST"])
def documentos():
    if not login_required():
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        titulo = request.form.get("titulo")
        tipo = request.form.get("tipo")
        texto = request.form.get("texto")

        conn = db()
        cur = conn.cursor()
        cur.execute("INSERT INTO documentos (titulo, tipo, texto) VALUES (?, ?, ?)", (titulo, tipo, texto))
        conn.commit()
        conn.close()
        msg = "Documento salvo."

    dados = listar("documentos")
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td><pre>{d[3]}</pre></td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>📄 Documentos</h1>
    <div class="card">
        <p class="ok">{msg}</p>
        <form method="POST">
            <input name="titulo" placeholder="Título">
            <select name="tipo">
                <option value="modelo">Modelo</option>
                <option value="contrato">Contrato</option>
                <option value="proposta">Proposta</option>
                <option value="anotacao">Anotação</option>
            </select>
            <textarea name="texto" placeholder="Texto do documento"></textarea>
            <button>Salvar documento</button>
        </form>
    </div>
    <table><tr><th>ID</th><th>Título</th><th>Tipo</th><th>Texto</th><th>Data</th></tr>{linhas}</table>
    """)


@app.route("/conhecimento", methods=["GET", "POST"])
def conhecimento():
    if not login_required():
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        titulo = request.form.get("titulo")
        texto = request.form.get("texto")

        conn = db()
        cur = conn.cursor()
        cur.execute("INSERT INTO conhecimento (titulo, texto) VALUES (?, ?)", (titulo, texto))
        conn.commit()
        conn.close()
        msg = "Conhecimento salvo."

    dados = listar("conhecimento")
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td><pre>{d[2]}</pre></td><td>{d[3]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🧠 Base de Conhecimento</h1>
    <div class="card">
        <p class="ok">{msg}</p>
        <form method="POST">
            <input name="titulo" placeholder="Título">
            <textarea name="texto" placeholder="Informação importante"></textarea>
            <button>Salvar conhecimento</button>
        </form>
    </div>
    <table><tr><th>ID</th><th>Título</th><th>Texto</th><th>Data</th></tr>{linhas}</table>
    """)


@app.route("/propostas", methods=["GET", "POST"])
def propostas():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        cliente = request.form.get("cliente")
        descricao = request.form.get("descricao")
        resultado = gerar_proposta(cliente, descricao)
        valor = calcular_orcamento(descricao)

        conn = db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO propostas (cliente, descricao, valor, texto) VALUES (?, ?, ?, ?)",
            (cliente, descricao, valor, resultado)
        )
        conn.commit()
        conn.close()

    dados = listar("propostas")
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>R$ {d[3]:.2f}</td><td><pre>{d[4]}</pre></td><td>{d[5]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🧾 Propostas Comerciais</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Cliente">
            <textarea name="descricao" placeholder="Ex: 10 camisetas personalizadas com arte"></textarea>
            <button>Gerar proposta</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    <table><tr><th>ID</th><th>Cliente</th><th>Descrição</th><th>Valor</th><th>Texto</th><th>Data</th></tr>{linhas}</table>
    """)


@app.route("/atendimento", methods=["GET", "POST"])
def atendimento():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        cliente = request.form.get("cliente") or "cliente"
        pergunta = request.form.get("pergunta") or ""
        resposta = atendimento_automatico(cliente, pergunta)

    dados = listar("atendimentos")
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>💬 Atendimento Automático</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Nome do cliente">
            <textarea name="pergunta" placeholder="Pergunta do cliente"></textarea>
            <button>Responder</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    <table><tr><th>ID</th><th>Cliente</th><th>Pergunta</th><th>Resposta</th><th>Data</th></tr>{linhas}</table>
    """)


@app.route("/buscar", methods=["GET", "POST"])
def buscar():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        termo = request.form.get("termo") or ""
        resultado = busca_sistema(termo)

    return layout(f"""
    <h1>🔎 Busca Geral</h1>
    <div class="card">
        <form method="POST">
            <input name="termo" placeholder="Buscar em pedidos, leads, clientes, documentos e conhecimento">
            <button>Buscar</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    """)


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
        elif tipo == "pedido":
            cur.execute("INSERT INTO pedidos (nome, cliente) VALUES (?, ?)", (nome, extra))
            msg = "Pedido criado."
        elif tipo == "lead":
            cur.execute("INSERT INTO leads (nome, origem) VALUES (?, ?)", (nome, extra or "painel"))
            msg = "Lead criado."
        elif tipo == "cliente":
            cur.execute("INSERT INTO clientes (nome, contato, historico) VALUES (?, ?, ?)", (nome, extra, "Criado pelo painel"))
            msg = "Cliente criado."
        elif tipo == "notificacao":
            cur.execute("INSERT INTO notificacoes (mensagem) VALUES (?)", (nome,))
            msg = "Notificação criada."

        conn.commit()
        conn.close()
        salvar_log(f"Command Center: {tipo} - {nome}")

    return layout(f"""
    <h1>🧠 Command Center</h1>
    <div class="card">
        <p class="ok">{msg}</p>
        <form method="POST">
            <select name="tipo">
                <option value="tarefa">Tarefa</option>
                <option value="pedido">Pedido</option>
                <option value="lead">Lead</option>
                <option value="cliente">Cliente</option>
                <option value="notificacao">Notificação</option>
            </select>
            <input name="nome" placeholder="Nome / descrição">
            <input name="extra" placeholder="Extra: cliente, origem ou contato">
            <button>Executar</button>
        </form>
    </div>
    """)


def tabela_html(titulo, tabela, colunas):
    if not login_required():
        return redirect("/login")
    dados = listar(tabela)
    linhas = "".join(["<tr>" + "".join([f"<td>{x}</td>" for x in d]) + "</tr>" for d in dados])
    head = "".join([f"<th>{c}</th>" for c in colunas])
    return layout(f"<h1>{titulo}</h1><table><tr>{head}</tr>{linhas}</table>")


@app.route("/tarefas")
def tarefas_page():
    return tabela_html("✅ Tarefas", "tarefas", ["ID", "Título", "Status", "Data"])


@app.route("/producao")
def producao_page():
    return tabela_html("🏗️ Produção", "producao", ["ID", "Item", "Cliente", "Status", "Data"])


@app.route("/estoque")
def estoque_page():
    return tabela_html("📦 Estoque", "estoque", ["ID", "Item", "Quantidade", "Data"])


@app.route("/clientes")
def clientes_page():
    return tabela_html("👤 Clientes", "clientes", ["ID", "Nome", "Contato", "Histórico", "Data"])


@app.route("/pedidos")
def pedidos_page():
    return tabela_html("📦 Pedidos", "pedidos", ["ID", "Nome", "Cliente", "Status", "Data"])


@app.route("/leads")
def leads_page():
    return tabela_html("🎯 Leads", "leads", ["ID", "Nome", "Origem", "Status", "Data"])


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
    return tabela_html("🧾 Logs", "logs", ["ID", "Mensagem", "Data"])


@app.route("/backup")
def backup():
    if not login_required():
        return redirect("/login")
    nome = f"backup_v29_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    with open(DB_PATH, "rb") as f:
        data = f.read()
    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={nome}"})


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔥 STREETCORE OS V29 AI OFFICE\n\n"
        "/atender cliente pergunta\n"
        "/proposta cliente descricao\n"
        "/contrato cliente servico valor\n"
        "/doc titulo texto\n"
        "/saber titulo texto\n"
        "/buscar termo\n"
        "/pedido camiseta joao\n"
        "/lead maria instagram\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/post camisetas\n"
        "/campanha street graff\n"
        "/relatorio"
    )


async def responder_generico(update, texto):
    await update.message.reply_text(texto)


async def atender_cmd(update, context):
    if len(context.args) < 2:
        await responder_generico(update, "Use: /atender cliente pergunta")
        return
    cliente = context.args[0]
    pergunta = " ".join(context.args[1:])
    await responder_generico(update, atendimento_automatico(cliente, pergunta))


async def proposta_cmd(update, context):
    if len(context.args) < 2:
        await responder_generico(update, "Use: /proposta cliente descricao")
        return
    cliente = context.args[0]
    descricao = " ".join(context.args[1:])
    texto = gerar_proposta(cliente, descricao)
    valor = calcular_orcamento(descricao)

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO propostas (cliente, descricao, valor, texto) VALUES (?, ?, ?, ?)", (cliente, descricao, valor, texto))
    conn.commit()
    conn.close()

    await responder_generico(update, texto)


async def contrato_cmd(update, context):
    if len(context.args) < 3:
        await responder_generico(update, "Use: /contrato cliente servico valor")
        return
    cliente = context.args[0]
    valor = context.args[-1]
    servico = " ".join(context.args[1:-1])
    await responder_generico(update, gerar_contrato(cliente, servico, valor))


async def doc_cmd(update, context):
    if len(context.args) < 2:
        await responder_generico(update, "Use: /doc titulo texto")
        return
    titulo = context.args[0]
    texto = " ".join(context.args[1:])
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO documentos (titulo, tipo, texto) VALUES (?, ?, ?)", (titulo, "telegram", texto))
    conn.commit()
    conn.close()
    await responder_generico(update, "📄 Documento salvo.")


async def saber_cmd(update, context):
    if len(context.args) < 2:
        await responder_generico(update, "Use: /saber titulo texto")
        return
    titulo = context.args[0]
    texto = " ".join(context.args[1:])
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO conhecimento (titulo, texto) VALUES (?, ?)", (titulo, texto))
    conn.commit()
    conn.close()
    await responder_generico(update, "🧠 Conhecimento salvo.")


async def buscar_cmd(update, context):
    termo = " ".join(context.args)
    await responder_generico(update, busca_sistema(termo))


async def pedido_cmd(update, context):
    item = context.args[0] if context.args else ""
    cliente = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO pedidos (nome, cliente) VALUES (?, ?)", (item, cliente))
    conn.commit()
    conn.close()
    await responder_generico(update, "📦 Pedido criado.")


async def lead_cmd(update, context):
    nome = context.args[0] if context.args else ""
    origem = " ".join(context.args[1:]) if len(context.args) > 1 else "manual"
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO leads (nome, origem) VALUES (?, ?)", (nome, origem))
    conn.commit()
    conn.close()
    await responder_generico(update, "🎯 Lead criado.")


async def receita_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("receita", valor, "telegram"))
    conn.commit()
    conn.close()
    await responder_generico(update, f"💰 Receita R$ {valor:.2f}")


async def despesa_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO financeiro (tipo, valor, descricao) VALUES (?, ?, ?)", ("despesa", valor, "telegram"))
    conn.commit()
    conn.close()
    await responder_generico(update, f"💸 Despesa R$ {valor:.2f}")


async def financeiro_cmd(update, context):
    r, d, l = financeiro()
    await responder_generico(update, f"💵 FINANCEIRO\nReceita: R$ {r:.2f}\nDespesa: R$ {d:.2f}\nLucro: R$ {l:.2f}")


async def post_cmd(update, context):
    await responder_generico(update, gerar_post(" ".join(context.args) or "Street Graff"))


async def campanha_cmd(update, context):
    await responder_generico(update, gerar_campanha(" ".join(context.args) or "Street Graff"))


async def relatorio_cmd(update, context):
    await responder_generico(update, relatorio())


async def status_cmd(update, context):
    await responder_generico(update, "✅ V29 AI Office online.")


async def responder(update, context):
    salvar_log(update.message.text)
    await responder_generico(update, faq_resposta(update.message.text))


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    comandos = {
        "start": start,
        "status": status_cmd,
        "atender": atender_cmd,
        "proposta": proposta_cmd,
        "contrato": contrato_cmd,
        "doc": doc_cmd,
        "saber": saber_cmd,
        "buscar": buscar_cmd,
        "pedido": pedido_cmd,
        "lead": lead_cmd,
        "receita": receita_cmd,
        "despesa": despesa_cmd,
        "financeiro": financeiro_cmd,
        "post": post_cmd,
        "campanha": campanha_cmd,
        "relatorio": relatorio_cmd,
    }

    for nome, func in comandos.items():
        bot.add_handler(CommandHandler(nome, func))

    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V29...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V29")

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
