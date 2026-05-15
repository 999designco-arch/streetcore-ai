import os
import sqlite3
import threading
import asyncio
from datetime import datetime
from flask import Flask, jsonify, request, redirect, session, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v30-supreme")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")
DB_PATH = "streetcore_v30.db"

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
        )""",
        """CREATE TABLE IF NOT EXISTS automacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            acao TEXT,
            status TEXT DEFAULT 'ativa',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS ideias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tema TEXT,
            ideia TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS catalogo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto TEXT,
            preco REAL,
            descricao TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS calendario_conteudo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dia TEXT,
            conteudo TEXT,
            status TEXT DEFAULT 'planejado',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )"""
    ]

    for tabela in tabelas:
        cur.execute(tabela)

    conn.commit()
    conn.close()
    print("✅ Banco V30 SUPREME iniciado.")


def login_required():
    return session.get("logado") is True


def salvar_log(msg):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO logs (mensagem) VALUES (?)", (msg,))
    conn.commit()
    conn.close()


def inserir(tabela, campos, valores):
    conn = db()
    cur = conn.cursor()
    q = ",".join(["?"] * len(valores))
    cur.execute(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)
    conn.commit()
    conn.close()


def listar(tabela):
    conn = db()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT 100")
    dados = cur.fetchall()
    conn.close()
    return dados


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
    return (
        f"🚀 CAMPANHA SUPREME - {tema.upper()}\n\n"
        f"{gerar_post(tema)}\n\n---\n\n"
        f"{gerar_story(tema)}\n\n---\n\n"
        f"{gerar_reels(tema)}\n\n---\n\n"
        "Plano de ação:\n"
        "1. Postar feed hoje às 18h.\n"
        "2. Subir stories em 3 partes.\n"
        "3. Fazer reels com bastidor.\n"
        "4. Chamar clientes no direct.\n"
        "5. Registrar leads no sistema."
    )


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

    arte = 20 if "arte" in texto or "design" in texto else 0
    urgente = 30 if "urgente" in texto else 0

    return (base * quantidade) + arte + urgente


def gerar_proposta(cliente, descricao):
    valor = calcular_orcamento(descricao)

    return (
        f"🧾 PROPOSTA COMERCIAL STREET GRAFF\n\n"
        f"Cliente: {cliente}\n"
        f"Solicitação: {descricao}\n\n"
        "Incluso:\n"
        "- atendimento personalizado;\n"
        "- produção sob medida;\n"
        "- revisão básica;\n"
        "- personalização conforme pedido.\n\n"
        f"Valor estimado: R$ {valor:.2f}\n"
        "Prazo: 5 dias úteis + transporte.\n"
        "Pagamento: somente via PIX.\n\n"
        "Para confirmar, envie arte/referência e quantidade final."
    )


def gerar_contrato(cliente, servico, valor):
    return (
        f"📄 CONTRATO SIMPLES DE SERVIÇO\n\n"
        f"Contratante: {cliente}\n"
        "Contratada: Street Graff\n\n"
        f"Serviço: {servico}\n"
        f"Valor: R$ {valor}\n\n"
        "Condições:\n"
        "1. Pagamento via PIX.\n"
        "2. Produção em até 5 dias úteis após confirmação.\n"
        "3. Alterações após aprovação podem gerar custos extras.\n"
        "4. Produção inicia após pagamento e confirmação dos detalhes.\n\n"
        "Modelo simples gerado automaticamente."
    )


def faq_resposta(pergunta):
    p = pergunta.lower()

    if "prazo" in p:
        return "O prazo padrão é de 5 dias úteis de produção + tempo da transportadora."
    if "pix" in p or "pagamento" in p:
        return "O pagamento é somente via PIX."
    if "camiseta" in p:
        return "Fazemos camisetas personalizadas. O preço varia por quantidade, arte e detalhes."
    if "caneca" in p:
        return "Fazemos canecas personalizadas. O valor depende da quantidade e da personalização."
    if "adesivo" in p:
        return "Fazemos adesivos personalizados em diferentes tamanhos e quantidades."
    if "panfleto" in p:
        return "Fazemos panfletos personalizados para divulgação, eventos e empresas."
    if "brinde" in p:
        return "Fazemos brindes personalizados conforme a necessidade do cliente."
    if "orçamento" in p or "orcamento" in p:
        return "Para orçamento, informe produto, quantidade, tamanho e se já possui arte."

    return "Posso ajudar com orçamento, prazo, pagamento, camisetas, adesivos, canecas, panfletos e brindes."


def atendimento_automatico(cliente, pergunta):
    resposta = faq_resposta(pergunta)
    inserir("atendimentos", "cliente,pergunta,resposta", (cliente, pergunta, resposta))
    return resposta


def busca_sistema(termo):
    termo_like = f"%{termo}%"
    conn = db()
    cur = conn.cursor()
    blocos = []

    pesquisas = [
        ("PEDIDOS", "SELECT id,nome,cliente,status,criado_em FROM pedidos WHERE nome LIKE ? OR cliente LIKE ?"),
        ("LEADS", "SELECT id,nome,origem,status,criado_em FROM leads WHERE nome LIKE ? OR origem LIKE ?"),
        ("CLIENTES", "SELECT id,nome,contato,historico,criado_em FROM clientes WHERE nome LIKE ? OR contato LIKE ?"),
        ("DOCUMENTOS", "SELECT id,titulo,tipo,criado_em FROM documentos WHERE titulo LIKE ? OR texto LIKE ?"),
        ("CONHECIMENTO", "SELECT id,titulo,criado_em FROM conhecimento WHERE titulo LIKE ? OR texto LIKE ?"),
        ("PROPOSTAS", "SELECT id,cliente,descricao,valor,criado_em FROM propostas WHERE cliente LIKE ? OR descricao LIKE ?")
    ]

    for nome, query in pesquisas:
        cur.execute(query, (termo_like, termo_like))
        dados = cur.fetchall()
        if dados:
            blocos.append(f"{nome}:\n" + "\n".join(map(str, dados)))

    conn.close()
    return "\n\n".join(blocos) if blocos else "Nenhum resultado encontrado."


def plano_do_dia():
    return (
        "✅ PLANO DO DIA SUPREME\n\n"
        "1. Verificar novos leads.\n"
        "2. Responder clientes pendentes.\n"
        "3. Criar 1 campanha com foco em venda.\n"
        "4. Gerar 1 post, 1 story e 1 reels.\n"
        "5. Conferir produção e estoque.\n"
        "6. Atualizar pedidos.\n"
        "7. Registrar receitas e despesas.\n"
        "8. Criar propostas para leads quentes.\n"
        "9. Fazer backup.\n"
        "10. Fechar pelo menos 1 venda."
    )


def relatorio():
    r, d, l = financeiro()

    return (
        "📊 RELATÓRIO V30 SUPREME OS\n\n"
        f"Pedidos: {contar('pedidos')}\n"
        f"Leads: {contar('leads')}\n"
        f"Clientes: {contar('clientes')}\n"
        f"Conteúdos: {contar('conteudos')}\n"
        f"Campanhas: {contar('campanhas')}\n"
        f"Tarefas: {contar('tarefas')}\n"
        f"Produção: {contar('producao')}\n"
        f"Estoque: {contar('estoque')}\n"
        f"Documentos: {contar('documentos')}\n"
        f"Conhecimento: {contar('conhecimento')}\n"
        f"Propostas: {contar('propostas')}\n"
        f"Atendimentos: {contar('atendimentos')}\n"
        f"Automações: {contar('automacoes')}\n\n"
        f"Receita: R$ {r:.2f}\n"
        f"Despesa: R$ {d:.2f}\n"
        f"Lucro: R$ {l:.2f}\n\n"
        "Decisão suprema:\n"
        "✅ priorizar leads quentes;\n"
        "✅ criar campanha hoje;\n"
        "✅ converter propostas abertas;\n"
        "✅ controlar produção;\n"
        "✅ manter conteúdo diário."
    )


def copiloto(pergunta):
    return (
        "🧠 COPILOTO SUPREME\n\n"
        f"Pedido recebido: {pergunta}\n\n"
        "Plano recomendado:\n"
        "1. Se for venda: criar campanha + proposta.\n"
        "2. Se for cliente: registrar lead/cliente.\n"
        "3. Se for pedido: criar pedido e produção.\n"
        "4. Se for dinheiro: lançar receita/despesa.\n"
        "5. Se for marketing: gerar post, story e reels.\n\n"
        f"{plano_do_dia()}"
    )


def calendario_semanal(tema):
    return (
        f"📅 CALENDÁRIO SEMANAL - {tema.upper()}\n\n"
        "Segunda: post de produto + story bastidor.\n"
        "Terça: reels antes/depois.\n"
        "Quarta: post de venda + enquete.\n"
        "Quinta: bastidor da produção.\n"
        "Sexta: prova social + oferta.\n"
        "Sábado: campanha promocional.\n"
        "Domingo: inspiração + bastidor leve."
    )


def gerar_ideias(tema):
    ideias = [
        f"Antes e depois de {tema}",
        f"Bastidor produzindo {tema}",
        f"Oferta relâmpago de {tema}",
        f"Depoimento de cliente sobre {tema}",
        f"Reels mostrando detalhes de {tema}",
        f"Story com enquete sobre {tema}",
        f"Post educativo sobre personalização de {tema}"
    ]

    texto = "\n".join([f"{i+1}. {ideia}" for i, ideia in enumerate(ideias)])
    inserir("ideias", "tema,ideia", (tema, texto))
    return f"💡 IDEIAS GERADAS\n\n{texto}"


def layout(conteudo):
    return f"""
    <html>
    <head>
        <title>StreetCore OS V30</title>
        <style>
            body {{ margin:0; background:#050505; color:white; font-family:Arial; }}
            .sidebar {{
                position:fixed; top:0; left:0; bottom:0; width:280px;
                background:#0b0b0b; border-right:1px solid #222; padding:24px; overflow:auto;
            }}
            .sidebar h2 {{ color:#00ff88; }}
            .sidebar a {{ display:block; color:white; text-decoration:none; margin:12px 0; }}
            .sidebar a:hover {{ color:#00ff88; }}
            .main {{ margin-left:330px; padding:30px; }}
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
            a {{ color:#00ff88; }}
            pre {{ white-space:pre-wrap; }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <h2>🔥 StreetCore</h2>
            <a href="/">Dashboard Supremo</a>
            <a href="/supreme">Supreme Center</a>
            <a href="/copiloto">Copiloto</a>
            <a href="/hoje">Plano do Dia</a>
            <a href="/office">AI Office</a>
            <a href="/atendimento">Atendimento</a>
            <a href="/propostas">Propostas</a>
            <a href="/documentos">Documentos</a>
            <a href="/conhecimento">Conhecimento</a>
            <a href="/campanhas">Campanhas</a>
            <a href="/ideias">Ideias</a>
            <a href="/calendario-conteudo">Calendário Conteúdo</a>
            <a href="/catalogo">Catálogo</a>
            <a href="/pedidos">Pedidos</a>
            <a href="/leads">Leads</a>
            <a href="/clientes">Clientes</a>
            <a href="/financeiro-web">Financeiro</a>
            <a href="/relatorio-web">Relatório</a>
            <a href="/buscar">Busca Geral</a>
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
    <h1>🔥 STREETCORE OS V30 SUPREME</h1>
    <p class="ok">Sistema supremo gratuito: vendas, operação, escritório IA, conteúdo e decisão.</p>

    <div class="grid">
        <div class="card"><h2>Pedidos</h2><div class="big">{contar("pedidos")}</div></div>
        <div class="card"><h2>Leads</h2><div class="big">{contar("leads")}</div></div>
        <div class="card"><h2>Clientes</h2><div class="big">{contar("clientes")}</div></div>
        <div class="card"><h2>Propostas</h2><div class="big">{contar("propostas")}</div></div>
        <div class="card"><h2>Campanhas</h2><div class="big">{contar("campanhas")}</div></div>
        <div class="card"><h2>Conteúdos</h2><div class="big">{contar("conteudos")}</div></div>
        <div class="card"><h2>Atendimentos</h2><div class="big">{contar("atendimentos")}</div></div>
        <div class="card"><h2>Receita</h2><div class="big">R$ {r:.2f}</div></div>
        <div class="card"><h2>Lucro</h2><div class="big">R$ {l:.2f}</div></div>
    </div>

    <div class="card"><pre>{plano_do_dia()}</pre></div>
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
            <p>V30 Supreme OS</p>
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
    return jsonify({"status": "online", "version": "StreetCore OS V30 Supreme"})


@app.route("/supreme", methods=["GET", "POST"])
def supreme():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        comando = request.form.get("comando") or ""
        resposta = copiloto(comando)

    return layout(f"""
    <h1>👑 Supreme Center</h1>
    <div class="card">
        <form method="POST">
            <input name="comando" placeholder="Ex: quero vender mais camisetas hoje">
            <button>Executar análise suprema</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    """)


@app.route("/copiloto", methods=["GET", "POST"])
def copiloto_page():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        resposta = copiloto(request.form.get("pergunta") or "")

    return layout(f"""
    <h1>🧠 Copiloto Supremo</h1>
    <div class="card">
        <form method="POST">
            <input name="pergunta" placeholder="O que você quer decidir?">
            <button>Analisar</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    """)


@app.route("/hoje")
def hoje():
    if not login_required():
        return redirect("/login")
    return layout(f"<h1>✅ Plano do Dia</h1><div class='card'><pre>{plano_do_dia()}</pre></div>")


@app.route("/office")
def office():
    if not login_required():
        return redirect("/login")

    return layout(f"""
    <h1>🏢 AI Office Supremo</h1>
    <div class="grid">
        <div class="card"><h2>Documentos</h2><div class="big">{contar("documentos")}</div></div>
        <div class="card"><h2>Conhecimento</h2><div class="big">{contar("conhecimento")}</div></div>
        <div class="card"><h2>Propostas</h2><div class="big">{contar("propostas")}</div></div>
        <div class="card"><h2>Atendimentos</h2><div class="big">{contar("atendimentos")}</div></div>
    </div>
    """)


def tabela_html(titulo, tabela, colunas):
    if not login_required():
        return redirect("/login")

    dados = listar(tabela)
    linhas = "".join(["<tr>" + "".join([f"<td>{x}</td>" for x in d]) + "</tr>" for d in dados])
    head = "".join([f"<th>{c}</th>" for c in colunas])
    return layout(f"<h1>{titulo}</h1><table><tr>{head}</tr>{linhas}</table>")


@app.route("/pedidos")
def pedidos():
    return tabela_html("📦 Pedidos", "pedidos", ["ID", "Nome", "Cliente", "Status", "Data"])


@app.route("/leads")
def leads():
    return tabela_html("🎯 Leads", "leads", ["ID", "Nome", "Origem", "Status", "Data"])


@app.route("/clientes")
def clientes():
    return tabela_html("👤 Clientes", "clientes", ["ID", "Nome", "Contato", "Histórico", "Data"])


@app.route("/logs")
def logs():
    return tabela_html("🧾 Logs", "logs", ["ID", "Mensagem", "Data"])


@app.route("/documentos", methods=["GET", "POST"])
def documentos():
    if not login_required():
        return redirect("/login")

    if request.method == "POST":
        inserir("documentos", "titulo,tipo,texto", (
            request.form.get("titulo"),
            request.form.get("tipo"),
            request.form.get("texto")
        ))

    return tabela_html("📄 Documentos", "documentos", ["ID", "Título", "Tipo", "Texto", "Data"])


@app.route("/conhecimento", methods=["GET", "POST"])
def conhecimento():
    if not login_required():
        return redirect("/login")

    if request.method == "POST":
        inserir("conhecimento", "titulo,texto", (
            request.form.get("titulo"),
            request.form.get("texto")
        ))

    form = """
    <div class="card">
        <form method="POST">
            <input name="titulo" placeholder="Título">
            <textarea name="texto" placeholder="Conhecimento"></textarea>
            <button>Salvar</button>
        </form>
    </div>
    """
    return layout(form + "<h1>🧠 Conhecimento</h1><pre>" + str(listar("conhecimento")) + "</pre>")


@app.route("/propostas", methods=["GET", "POST"])
def propostas():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        cliente = request.form.get("cliente")
        descricao = request.form.get("descricao")
        texto = gerar_proposta(cliente, descricao)
        valor = calcular_orcamento(descricao)
        inserir("propostas", "cliente,descricao,valor,texto", (cliente, descricao, valor, texto))
        resultado = texto

    return layout(f"""
    <h1>🧾 Propostas</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Cliente">
            <textarea name="descricao" placeholder="Descrição"></textarea>
            <button>Gerar proposta</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    <pre>{listar("propostas")}</pre>
    """)


@app.route("/atendimento", methods=["GET", "POST"])
def atendimento():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        resposta = atendimento_automatico(
            request.form.get("cliente") or "cliente",
            request.form.get("pergunta") or ""
        )

    return layout(f"""
    <h1>💬 Atendimento Automático</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Cliente">
            <textarea name="pergunta" placeholder="Pergunta"></textarea>
            <button>Responder</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    <pre>{listar("atendimentos")}</pre>
    """)


@app.route("/campanhas", methods=["GET", "POST"])
def campanhas():
    if not login_required():
        return redirect("/login")

    if request.method == "POST":
        tema = request.form.get("tema") or "Street Graff"
        texto = gerar_campanha(tema)
        inserir("campanhas", "tema,texto", (tema, texto))

    return layout(f"""
    <h1>🚀 Campanhas</h1>
    <div class="card">
        <form method="POST">
            <input name="tema" placeholder="Tema">
            <button>Criar campanha</button>
        </form>
    </div>
    <pre>{listar("campanhas")}</pre>
    """)


@app.route("/ideias", methods=["GET", "POST"])
def ideias():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        resultado = gerar_ideias(request.form.get("tema") or "Street Graff")

    return layout(f"""
    <h1>💡 Ideias</h1>
    <div class="card">
        <form method="POST">
            <input name="tema" placeholder="Tema">
            <button>Gerar ideias</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    <pre>{listar("ideias")}</pre>
    """)


@app.route("/calendario-conteudo", methods=["GET", "POST"])
def calendario_conteudo():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        tema = request.form.get("tema") or "Street Graff"
        resultado = calendario_semanal(tema)
        inserir("calendario_conteudo", "dia,conteudo", ("semana", resultado))

    return layout(f"""
    <h1>📅 Calendário de Conteúdo</h1>
    <div class="card">
        <form method="POST">
            <input name="tema" placeholder="Tema">
            <button>Gerar calendário</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    <pre>{listar("calendario_conteudo")}</pre>
    """)


@app.route("/catalogo", methods=["GET", "POST"])
def catalogo():
    if not login_required():
        return redirect("/login")

    if request.method == "POST":
        inserir("catalogo", "produto,preco,descricao", (
            request.form.get("produto"),
            float(request.form.get("preco") or 0),
            request.form.get("descricao")
        ))

    return layout(f"""
    <h1>🛍️ Catálogo</h1>
    <div class="card">
        <form method="POST">
            <input name="produto" placeholder="Produto">
            <input name="preco" placeholder="Preço">
            <textarea name="descricao" placeholder="Descrição"></textarea>
            <button>Salvar produto</button>
        </form>
    </div>
    <pre>{listar("catalogo")}</pre>
    """)


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


@app.route("/relatorio-web")
def relatorio_web():
    if not login_required():
        return redirect("/login")
    return layout(f"<h1>📊 Relatório Supremo</h1><div class='card'><pre>{relatorio()}</pre></div>")


@app.route("/buscar", methods=["GET", "POST"])
def buscar():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        resultado = busca_sistema(request.form.get("termo") or "")

    return layout(f"""
    <h1>🔎 Busca Geral</h1>
    <div class="card">
        <form method="POST">
            <input name="termo" placeholder="Buscar">
            <button>Buscar</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    """)


@app.route("/backup")
def backup():
    if not login_required():
        return redirect("/login")
    nome = f"backup_v30_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    with open(DB_PATH, "rb") as f:
        data = f.read()
    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={nome}"})


async def responder_texto(update, texto):
    await update.message.reply_text(texto)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await responder_texto(update,
        "🔥 STREETCORE OS V30 SUPREME\n\n"
        "/supreme vender mais hoje\n"
        "/hoje\n"
        "/relatorio\n"
        "/atender cliente pergunta\n"
        "/proposta cliente descricao\n"
        "/contrato cliente servico valor\n"
        "/ideias camisetas\n"
        "/calendario street graff\n"
        "/pedido camiseta joao\n"
        "/lead maria instagram\n"
        "/cliente joao 119999 historico\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/post camisetas\n"
        "/story adesivos\n"
        "/reels canecas\n"
        "/campanha street graff\n"
        "/buscar termo"
    )


async def supreme_cmd(update, context):
    await responder_texto(update, copiloto(" ".join(context.args)))


async def hoje_cmd(update, context):
    await responder_texto(update, plano_do_dia())


async def relatorio_cmd(update, context):
    await responder_texto(update, relatorio())


async def atender_cmd(update, context):
    if len(context.args) < 2:
        await responder_texto(update, "Use: /atender cliente pergunta")
        return
    await responder_texto(update, atendimento_automatico(context.args[0], " ".join(context.args[1:])))


async def proposta_cmd(update, context):
    if len(context.args) < 2:
        await responder_texto(update, "Use: /proposta cliente descricao")
        return
    cliente = context.args[0]
    desc = " ".join(context.args[1:])
    texto = gerar_proposta(cliente, desc)
    inserir("propostas", "cliente,descricao,valor,texto", (cliente, desc, calcular_orcamento(desc), texto))
    await responder_texto(update, texto)


async def contrato_cmd(update, context):
    if len(context.args) < 3:
        await responder_texto(update, "Use: /contrato cliente servico valor")
        return
    await responder_texto(update, gerar_contrato(context.args[0], " ".join(context.args[1:-1]), context.args[-1]))


async def ideias_cmd(update, context):
    await responder_texto(update, gerar_ideias(" ".join(context.args) or "Street Graff"))


async def calendario_cmd(update, context):
    tema = " ".join(context.args) or "Street Graff"
    texto = calendario_semanal(tema)
    inserir("calendario_conteudo", "dia,conteudo", ("semana", texto))
    await responder_texto(update, texto)


async def pedido_cmd(update, context):
    item = context.args[0] if context.args else ""
    cliente = " ".join(context.args[1:]) if len(context.args) > 1 else ""
    inserir("pedidos", "nome,cliente", (item, cliente))
    await responder_texto(update, "📦 Pedido criado.")


async def lead_cmd(update, context):
    nome = context.args[0] if context.args else ""
    origem = " ".join(context.args[1:]) if len(context.args) > 1 else "manual"
    inserir("leads", "nome,origem", (nome, origem))
    await responder_texto(update, "🎯 Lead criado.")


async def cliente_cmd(update, context):
    if len(context.args) < 2:
        await responder_texto(update, "Use: /cliente nome contato historico")
        return
    inserir("clientes", "nome,contato,historico", (context.args[0], context.args[1], " ".join(context.args[2:])))
    await responder_texto(update, "👤 Cliente criado.")


async def receita_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    inserir("financeiro", "tipo,valor,descricao", ("receita", valor, "telegram"))
    await responder_texto(update, f"💰 Receita R$ {valor:.2f}")


async def despesa_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    inserir("financeiro", "tipo,valor,descricao", ("despesa", valor, "telegram"))
    await responder_texto(update, f"💸 Despesa R$ {valor:.2f}")


async def financeiro_cmd(update, context):
    r, d, l = financeiro()
    await responder_texto(update, f"💵 FINANCEIRO\nReceita: R$ {r:.2f}\nDespesa: R$ {d:.2f}\nLucro: R$ {l:.2f}")


async def post_cmd(update, context):
    await responder_texto(update, gerar_post(" ".join(context.args) or "Street Graff"))


async def story_cmd(update, context):
    await responder_texto(update, gerar_story(" ".join(context.args) or "Street Graff"))


async def reels_cmd(update, context):
    await responder_texto(update, gerar_reels(" ".join(context.args) or "Street Graff"))


async def campanha_cmd(update, context):
    tema = " ".join(context.args) or "Street Graff"
    texto = gerar_campanha(tema)
    inserir("campanhas", "tema,texto", (tema, texto))
    await responder_texto(update, texto)


async def buscar_cmd(update, context):
    await responder_texto(update, busca_sistema(" ".join(context.args)))


async def status_cmd(update, context):
    await responder_texto(update, "✅ V30 Supreme OS online.")


async def responder(update, context):
    msg = update.message.text
    salvar_log(msg)
    await responder_texto(update, faq_resposta(msg))


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()

    comandos = {
        "start": start,
        "status": status_cmd,
        "supreme": supreme_cmd,
        "hoje": hoje_cmd,
        "relatorio": relatorio_cmd,
        "atender": atender_cmd,
        "proposta": proposta_cmd,
        "contrato": contrato_cmd,
        "ideias": ideias_cmd,
        "calendario": calendario_cmd,
        "pedido": pedido_cmd,
        "lead": lead_cmd,
        "cliente": cliente_cmd,
        "receita": receita_cmd,
        "despesa": despesa_cmd,
        "financeiro": financeiro_cmd,
        "post": post_cmd,
        "story": story_cmd,
        "reels": reels_cmd,
        "campanha": campanha_cmd,
        "buscar": buscar_cmd,
    }

    for nome, funcao in comandos.items():
        bot.add_handler(CommandHandler(nome, funcao))

    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V30 Supreme...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V30 Supreme")

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
