import os
import re
import io
import csv
import json
import time
import shutil
import sqlite3
import threading
import asyncio
import urllib.request
from datetime import datetime

from flask import Flask, jsonify, request, redirect, session, Response, send_file
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
except Exception:
    canvas = None
    A4 = None


# =========================
# CONFIG
# =========================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v43-stable-ultra-pro")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")
API_KEY = os.getenv("STREETCORE_API_KEY", "streetcore-api")
DB_PATH = os.getenv("DB_PATH", "streetcore_master.db")

USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")

UPLOAD_FOLDER = "uploads"
BACKUP_FOLDER = "backups"

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)
app.secret_key = SECRET_KEY

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)

telegram_app = None
telegram_loop = None


# =========================
# BANCO
# =========================

TABLES = {
    "usuarios": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        senha TEXT,
        nivel TEXT DEFAULT 'admin',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "pedidos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        cliente TEXT,
        status TEXT DEFAULT 'novo',
        valor REAL DEFAULT 0,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "leads": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        origem TEXT,
        status TEXT DEFAULT 'novo',
        temperatura TEXT DEFAULT 'frio',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "clientes": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        contato TEXT,
        historico TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "financeiro": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        valor REAL DEFAULT 0,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "produtos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        preco REAL DEFAULT 0,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "estoque": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        quantidade INTEGER DEFAULT 0,
        minimo INTEGER DEFAULT 5,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "producao": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        cliente TEXT,
        status TEXT DEFAULT 'aguardando',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "tarefas": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        status TEXT DEFAULT 'pendente',
        prioridade TEXT DEFAULT 'normal',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "campanhas": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT,
        texto TEXT,
        status TEXT DEFAULT 'planejada',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "conteudos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT,
        tipo TEXT,
        texto TEXT,
        status TEXT DEFAULT 'rascunho',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "propostas": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        descricao TEXT,
        valor REAL DEFAULT 0,
        texto TEXT,
        status TEXT DEFAULT 'aberta',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "documentos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        tipo TEXT,
        texto TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "conhecimento": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        texto TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "uploads": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        tipo TEXT,
        texto TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "atendimentos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        pergunta TEXT,
        resposta TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "fornecedores": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        contato TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "notificacoes": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mensagem TEXT,
        status TEXT DEFAULT 'nova',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "metas": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        valor TEXT,
        status TEXT DEFAULT 'ativa',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "automacoes": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        acao TEXT,
        status TEXT DEFAULT 'ativa',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "memoria": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chave TEXT,
        valor TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "agentes": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        funcao TEXT,
        ultima_resposta TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "instagram_queue": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        conteudo TEXT,
        legenda TEXT,
        status TEXT DEFAULT 'aguardando_aprovacao',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "pipeline": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        etapa TEXT,
        valor REAL DEFAULT 0,
        observacao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "oportunidades": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        produto TEXT,
        valor REAL DEFAULT 0,
        probabilidade INTEGER DEFAULT 50,
        status TEXT DEFAULT 'aberta',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "auditoria": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acao TEXT,
        detalhes TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "ideias": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT,
        ideia TEXT,
        status TEXT DEFAULT 'nova',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "rotinas": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        status TEXT DEFAULT 'ativa',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "eventos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        data TEXT,
        status TEXT DEFAULT 'pendente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "cliente_portal": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        pedido TEXT,
        status TEXT DEFAULT 'recebido',
        codigo TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "erros": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rota TEXT,
        erro TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "chat_sessions": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        pergunta TEXT,
        resposta TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "templates": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        tipo TEXT,
        conteudo TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "contratos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT,
        servico TEXT,
        valor REAL DEFAULT 0,
        texto TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "agenda": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        data TEXT,
        hora TEXT,
        status TEXT DEFAULT 'pendente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "status_pedidos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT,
        cliente TEXT,
        pedido TEXT,
        status TEXT DEFAULT 'recebido',
        observacao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "logs": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mensagem TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """
}

SAFE_TABLES = list(TABLES.keys())


def db():
    return sqlite3.connect(DB_PATH)


def sql(query, params=(), fetch=False):
    conn = db()
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data


def table_columns(tabela):
    try:
        return [c[1] for c in sql(f"PRAGMA table_info({tabela})", fetch=True)]
    except Exception:
        return []


def migrate_columns(tabela, schema):
    existentes = table_columns(tabela)
    campos = []
    for linha in schema.splitlines():
        linha = linha.strip().rstrip(",")
        if not linha or linha.startswith("id "):
            continue
        nome = linha.split()[0]
        if nome not in existentes and nome not in ["PRIMARY", "FOREIGN"]:
            campos.append((nome, " ".join(linha.split()[1:])))

    for nome, tipo in campos:
        try:
            sql(f"ALTER TABLE {tabela} ADD COLUMN {nome} {tipo}")
        except Exception:
            pass


def iniciar_banco():
    for nome, schema in TABLES.items():
        sql(f"CREATE TABLE IF NOT EXISTS {nome} ({schema})")
        migrate_columns(nome, schema)

    if not sql("SELECT * FROM usuarios WHERE usuario=?", (ADMIN_USER,), True):
        sql("INSERT INTO usuarios (usuario, senha, nivel) VALUES (?, ?, ?)", (ADMIN_USER, ADMIN_PASS, "admin"))

    agentes_padrao = [
        ("CEO IA", "Decidir prioridades, operação e crescimento"),
        ("Vendas IA", "Criar propostas, follow-up e conversão"),
        ("Marketing IA", "Criar campanhas, posts e ideias"),
        ("Atendimento IA", "Responder clientes e dúvidas"),
        ("Financeiro IA", "Analisar receita, despesa e lucro"),
        ("Produção IA", "Acompanhar pedidos, estoque e produção"),
        ("Social Media IA", "Criar posts, stories, reels e calendário")
    ]

    for nome, funcao in agentes_padrao:
        if not sql("SELECT * FROM agentes WHERE nome=?", (nome,), True):
            sql("INSERT INTO agentes (nome, funcao, ultima_resposta) VALUES (?, ?, ?)", (nome, funcao, "Aguardando primeira execução."))

    print("✅ StreetCore OS V44 LUXURY SAAS PRO iniciado.")


def inserir(tabela, campos, valores):
    if tabela not in SAFE_TABLES:
        raise ValueError("Tabela não permitida")
    q = ",".join(["?"] * len(valores))
    sql(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)


def listar(tabela, limite=200):
    if tabela not in SAFE_TABLES:
        return []
    return sql(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT ?", (limite,), True)


def contar(tabela):
    if tabela not in SAFE_TABLES:
        return 0
    try:
        return sql(f"SELECT COUNT(*) FROM {tabela}", fetch=True)[0][0]
    except Exception:
        return 0


def log(msg):
    try:
        inserir("logs", "mensagem", (str(msg),))
    except Exception:
        pass


def auditar(acao, detalhes=""):
    try:
        inserir("auditoria", "acao, detalhes", (str(acao), str(detalhes)))
    except Exception:
        pass


def registrar_erro(rota, erro):
    try:
        inserir("erros", "rota, erro", (str(rota), str(erro)))
    except Exception:
        pass


# =========================
# HELPERS
# =========================

def numero_float(valor, padrao=0):
    try:
        if valor is None or str(valor).strip() == "":
            return padrao
        return float(str(valor).replace(",", "."))
    except Exception:
        return padrao


def numero_int(valor, padrao=0):
    try:
        if valor is None or str(valor).strip() == "":
            return padrao
        return int(float(str(valor).replace(",", ".")))
    except Exception:
        return padrao


def texto_limpo(valor, padrao=""):
    try:
        valor = "" if valor is None else str(valor).strip()
        return valor if valor else padrao
    except Exception:
        return padrao


def login_required():
    return session.get("ok") is True


def is_admin():
    return session.get("nivel") == "admin"


def limpar_nome(nome):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", nome or "arquivo")


def financeiro():
    receita = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'", fetch=True)[0][0] or 0
    despesa = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'", fetch=True)[0][0] or 0
    return receita, despesa, receita - despesa


def extrair_txt(path):
    for enc in ["utf-8", "latin-1"]:
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except Exception:
            pass
    return ""


def extrair_pdf(path):
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(path)
        return "\n".join([(p.extract_text() or "") for p in reader.pages])
    except Exception:
        return ""


def extrair_arquivo(path):
    if path.lower().endswith(".txt"):
        return extrair_txt(path)
    if path.lower().endswith(".pdf"):
        return extrair_pdf(path)
    return ""


def ollama(prompt):
    if not USE_OLLAMA or not OLLAMA_URL:
        return ""
    try:
        payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}).encode("utf-8")
        req = urllib.request.Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=35) as res:
            data = json.loads(res.read().decode("utf-8"))
            return data.get("response", "")
    except Exception:
        return ""


def memoria_salvar(chave, valor):
    try:
        inserir("memoria", "chave, valor", (chave, valor))
    except Exception:
        pass


def memoria_buscar(chave):
    dados = sql("SELECT valor FROM memoria WHERE chave LIKE ? ORDER BY id DESC LIMIT 5", (f"%{chave}%",), True)
    return "\n".join([d[0] for d in dados]) if dados else ""


# =========================
# IA / NEGÓCIO
# =========================

def post(tema):
    ia = ollama(f"Crie um post de Instagram para Street Graff sobre {tema}. Tom jovem, street, vendedor, com CTA e hashtags.")
    if ia:
        return ia
    return f"""🔥 POST PRONTO - {tema.upper()}

Sua marca precisa aparecer com presença.
A Street Graff cria camisetas, adesivos, canecas, panfletos e brindes personalizados.

📲 Chama no direct e peça seu orçamento.
Pagamento via PIX.

#streetgraff #personalizados #camisetaspersonalizadas #adesivospersonalizados"""


def story(tema):
    return f"""📲 STORY - {tema.upper()}

Tela 1: Sua marca ainda está invisível?
Tela 2: Personalizados com estilo urbano.
Tela 3: Camisetas, adesivos, canecas, panfletos e brindes.
Tela 4: Chama no direct e peça seu orçamento."""


def reels(tema):
    return f"""🎬 REELS - {tema.upper()}

Gancho: Sua marca precisa aparecer mais?
Cena 1: Produto personalizado em destaque.
Cena 2: Bastidor da produção.
Cena 3: Resultado final.
CTA: Chama no direct."""


def campanha(tema):
    texto = f"{post(tema)}\n\n---\n\n{story(tema)}\n\n---\n\n{reels(tema)}"
    inserir("campanhas", "tema, texto, status", (tema, texto, "planejada"))
    return texto


def valor_orcamento(desc):
    t = (desc or "").lower()
    base = 35
    if "camiseta" in t:
        base = 45
    if "caneca" in t:
        base = 30
    if "adesivo" in t:
        base = 8
    if "panfleto" in t:
        base = 80
    if "brinde" in t:
        base = 20
    qtd = 1
    for palavra in t.replace(",", " ").split():
        if palavra.isdigit():
            qtd = int(palavra)
            break
    return base * qtd + (20 if "arte" in t or "design" in t else 0) + (30 if "urgente" in t else 0)


def gerar_proposta(cliente, desc):
    valor = valor_orcamento(desc)
    return f"""🧾 PROPOSTA COMERCIAL STREET GRAFF

Cliente: {cliente}
Solicitação: {desc}

Incluso:
- atendimento personalizado;
- produção sob medida;
- revisão básica;
- personalização conforme pedido.

Valor estimado: R$ {valor:.2f}
Prazo: 5 dias úteis + transporte.
Pagamento: somente via PIX.

Para confirmar, envie arte/referência e quantidade final."""


def faq(pergunta):
    p = (pergunta or "").lower()
    if "prazo" in p:
        return "Prazo padrão: 5 dias úteis de produção + transporte."
    if "pagamento" in p or "pix" in p:
        return "Pagamento somente via PIX."
    if "orçamento" in p or "orcamento" in p:
        return "Informe produto, quantidade, tamanho e se já possui arte."
    if "camiseta" in p:
        return "Fazemos camisetas personalizadas. Valor depende da quantidade e da arte."
    if "caneca" in p:
        return "Fazemos canecas personalizadas sob encomenda."
    if "adesivo" in p:
        return "Fazemos adesivos personalizados em vários tamanhos."
    ia = ollama(f"Responda como atendente da Street Graff: {pergunta}")
    return ia or "Fazemos camisetas, adesivos, canecas, panfletos e brindes personalizados."


def score_lead(nome, origem="", mensagem=""):
    texto = f"{nome} {origem} {mensagem}".lower()
    score = 20
    for p in ["orçamento", "orcamento", "preço", "preco", "comprar", "pedido", "pix", "urgente", "hoje", "quanto"]:
        if p in texto:
            score += 12
    for p in ["interesse", "ver", "talvez", "camiseta", "caneca", "adesivo", "panfleto", "brinde"]:
        if p in texto:
            score += 5
    if score >= 70:
        return "quente", min(score, 100)
    if score >= 40:
        return "morno", min(score, 100)
    return "frio", min(score, 100)


def buscar(termo):
    like = f"%{termo}%"
    blocos = []
    pesquisas = {
        "pedidos": "nome LIKE ? OR cliente LIKE ?",
        "leads": "nome LIKE ? OR origem LIKE ? OR status LIKE ? OR temperatura LIKE ?",
        "clientes": "nome LIKE ? OR contato LIKE ? OR historico LIKE ?",
        "propostas": "cliente LIKE ? OR descricao LIKE ? OR texto LIKE ?",
        "documentos": "titulo LIKE ? OR texto LIKE ?",
        "conhecimento": "titulo LIKE ? OR texto LIKE ?",
        "uploads": "nome LIKE ? OR texto LIKE ?",
        "memoria": "chave LIKE ? OR valor LIKE ?"
    }
    for tabela, where in pesquisas.items():
        params = tuple([like] * where.count("?"))
        dados = sql(f"SELECT * FROM {tabela} WHERE {where} LIMIT 20", params, True)
        if dados:
            blocos.append(f"{tabela.upper()}:\n" + "\n".join(map(str, dados)))
    return "\n\n".join(blocos) if blocos else "Nenhum resultado encontrado."


def relatorio():
    receita, despesa, lucro = financeiro()
    linhas = []
    for tabela in ["pedidos", "leads", "clientes", "propostas", "produtos", "estoque", "producao", "tarefas", "campanhas", "conteudos", "uploads", "atendimentos", "pipeline", "oportunidades"]:
        linhas.append(f"{tabela}: {contar(tabela)}")
    return "📊 RELATÓRIO V44 LUXURY SAAS PRO\n\n" + "\n".join(linhas) + f"""

Receita: R$ {receita:.2f}
Despesa: R$ {despesa:.2f}
Lucro: R$ {lucro:.2f}

Ações recomendadas:
✅ fechar leads quentes
✅ revisar propostas abertas
✅ criar campanha
✅ atualizar produção
✅ conferir estoque"""


def diagnostico_sistema():
    receita, despesa, lucro = financeiro()
    try:
        estoque_baixo = sql("SELECT item, quantidade, minimo FROM estoque WHERE quantidade <= minimo LIMIT 20", fetch=True)
    except Exception:
        estoque_baixo = []
    alertas = [f"{x[0]} ({x[1]}/{x[2]})" for x in estoque_baixo]
    return f"""🧠 DIAGNÓSTICO V44

Receita: R$ {receita:.2f}
Despesa: R$ {despesa:.2f}
Lucro: R$ {lucro:.2f}

Leads: {contar('leads')}
Pedidos: {contar('pedidos')}
Propostas: {contar('propostas')}
Tarefas: {contar('tarefas')}

Estoque baixo:
{chr(10).join(alertas) if alertas else "Nenhum item crítico."}

Próximas ações:
1. Fazer follow-up.
2. Criar conteúdo.
3. Atualizar produção.
4. Fechar propostas abertas.
"""


def pipeline_resumo():
    dados = listar("pipeline", 100)
    if not dados:
        return "Pipeline vazio."
    etapas = {}
    total = 0
    for d in dados:
        etapa = d[2]
        valor = numero_float(d[3], 0)
        etapas[etapa] = etapas.get(etapa, 0) + 1
        total += valor
    return "📊 PIPELINE\n\nTotal: R$ %.2f\n\n%s" % (total, "\n".join([f"{k}: {v}" for k, v in etapas.items()]))


def relatorio_executivo():
    return f"{relatorio()}\n\n{diagnostico_sistema()}\n\n{pipeline_resumo()}"


def agente_responder(nome, pergunta):
    func = sql("SELECT funcao FROM agentes WHERE nome=?", (nome,), True)
    funcao = func[0][0] if func else "Agente geral"
    prompt = f"Você é {nome}. Função: {funcao}. Contexto: {relatorio()}. Pedido: {pergunta}. Responda com plano prático."
    ia = ollama(prompt)
    if not ia:
        ia = f"🤖 {nome}\nFunção: {funcao}\n\nPlano:\n1. Analisar dados.\n2. Criar ação.\n3. Registrar tarefa.\n4. Acompanhar resultado.\n\nPedido: {pergunta}"
    sql("UPDATE agentes SET ultima_resposta=? WHERE nome=?", (ia, nome))
    return ia


def conselho_multiagentes(comando):
    agentes = ["CEO IA", "Vendas IA", "Marketing IA", "Atendimento IA", "Financeiro IA", "Produção IA", "Social Media IA"]
    return "\n\n".join([f"### {a}\n{agente_responder(a, comando)}" for a in agentes])


def chat_responder(pergunta):
    contexto = relatorio_executivo()
    memoria = memoria_buscar("mensagem_usuario")
    prompt = f"Você é o StreetCore, IA da Street Graff. Contexto: {contexto}. Memória: {memoria}. Usuário: {pergunta}. Responda prático."
    ia = ollama(prompt)
    if not ia:
        t = (pergunta or "").lower()
        if "campanha" in t or "vender" in t:
            ia = campanha(pergunta)
        elif "relatorio" in t or "relatório" in t:
            ia = contexto
        elif "proposta" in t:
            ia = "Para proposta: informe cliente + descrição do pedido."
        else:
            ia = f"Entendi. Posso criar campanha, proposta, lead, tarefa, diagnóstico ou consultar dados.\n\nMensagem: {pergunta}"
    inserir("chat_sessions", "usuario, pergunta, resposta", (session.get("usuario", "web"), pergunta, ia))
    memoria_salvar("mensagem_usuario", pergunta)
    return ia


def gerar_pdf_proposta(cliente, desc):
    texto = gerar_proposta(cliente, desc)
    buffer = io.BytesIO()
    if canvas is None:
        buffer.write(texto.encode("utf-8"))
        buffer.seek(0)
        return buffer, "txt"
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Proposta Comercial - Street Graff")
    y -= 35
    c.setFont("Helvetica", 11)
    for linha in texto.split("\n"):
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 50
        c.drawString(50, y, linha[:95])
        y -= 17
    c.save()
    buffer.seek(0)
    return buffer, "pdf"


def rodar_automacoes():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    inserir("tarefas", "titulo, status, prioridade", (f"Revisar leads novos - {agora}", "pendente", "alta"))
    inserir("notificacoes", "mensagem, status", (f"Rodar campanha diária - {agora}", "nova"))
    texto_post = post("Street Graff")
    inserir("conteudos", "tema, tipo, texto, status", ("Street Graff", "post_auto", texto_post, "rascunho"))
    inserir("instagram_queue", "tipo, conteudo, legenda, status", ("post", texto_post, "Legenda automática.", "aguardando_aprovacao"))
    inserir("automacoes", "nome, acao, status", ("auto_diaria", f"Executada em {agora}", "ativa"))
    return "Automações executadas: tarefa, notificação, post e fila Instagram criados."


def followup_leads():
    leads = sql("SELECT id, nome, origem, temperatura FROM leads ORDER BY id DESC LIMIT 20", fetch=True)
    if not leads:
        return "Nenhum lead encontrado."
    linhas = []
    for lead_id, nome, origem, temp in leads:
        texto = f"Follow-up com {nome} ({temp}) vindo de {origem}"
        inserir("tarefas", "titulo, status, prioridade", (texto, "pendente", "alta" if temp == "quente" else "normal"))
        linhas.append("✅ " + texto)
    return "📞 FOLLOW-UP CRIADO\n\n" + "\n".join(linhas)


def auto_organizar():
    return f"{followup_leads()}\n\n---\n\n{rodar_automacoes()}"


def criar_codigo_cliente():
    import random
    import string
    return "SG-" + "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def scheduler_loop():
    ultima = None
    while True:
        try:
            agora = datetime.now()
            if agora.hour == 9 and ultima != agora.date():
                rodar_automacoes()
                ultima = agora.date()
        except Exception as e:
            log(f"Erro scheduler: {e}")
        time.sleep(60)


# =========================
# UI CHATGPT STYLE
# =========================

def layout(conteudo):
    menu = [
        ("Chat IA", "/chat"), ("Workspace", "/workspace"), ("Luxury", "/luxury"), ("Templates", "/templates"), ("Contratos", "/contratos"), ("Agenda", "/agenda"), ("Status Pedido", "/status-pedido"), ("Dashboard", "/"), ("Criar", "/criar"),
        ("Executivo", "/executivo"), ("Quantum", "/quantum"), ("Master", "/master"), ("Ultra", "/ultra"),
        ("Neural", "/neural"), ("Multiagentes", "/multiagentes"), ("Pipeline", "/pipeline"),
        ("Kanban Leads", "/kanban-leads"), ("Kanban Produção", "/kanban-producao"), ("Conteúdo", "/conteudo"),
        ("Aprovações", "/aprovacoes"), ("Instagram", "/instagram"), ("Propostas", "/propostas"),
        ("PDF Proposta", "/pdf-proposta"), ("Atendimento", "/atendimento"), ("Upload", "/upload"),
        ("Busca", "/buscar"), ("Financeiro", "/financeiro"), ("Qualidade", "/qualidade"),
        ("Portal Cliente", "/portal-cliente"), ("Backup", "/backup"), ("Sair", "/logout")
    ]
    tables = ["pedidos", "leads", "clientes", "produtos", "estoque", "producao", "tarefas", "campanhas", "conteudos", "documentos", "conhecimento", "uploads", "atendimentos", "pipeline", "oportunidades", "auditoria", "fornecedores", "notificacoes", "metas", "automacoes", "memoria", "agentes", "instagram_queue", "cliente_portal", "erros", "chat_sessions", "logs"]
    links = "".join([f"<a class='nav-link' href='{url}'>{nome}</a>" for nome, url in menu])
    table_links = "".join([f"<a class='mini-link' href='/table/{t}'>{t.title()}</a>" for t in tables if t in SAFE_TABLES])

    return f"""
<html>
<head>
<title>StreetCore V44 Luxury SaaS Pro</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
:root{{--bg:#212121;--panel:#171717;--card:#262626;--border:#3f3f46;--text:#ececec;--muted:#b4b4b4;--green:#10a37f;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial}}
.shell{{display:flex;min-height:100vh}}
.sidebar{{width:310px;background:#171717;border-right:1px solid #2f2f2f;padding:14px;position:fixed;top:0;left:0;bottom:0;overflow:auto}}
.brand{{display:flex;align-items:center;gap:10px;padding:12px;border-radius:14px;background:#212121;border:1px solid #333;margin-bottom:12px}}
.logo{{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--green),#087f5b);color:white;font-weight:900}}
.brand h2{{font-size:16px;margin:0}} .brand p{{color:var(--muted);font-size:12px;margin:2px 0 0 0}}
.nav-link{{display:block;color:#ececec;text-decoration:none;padding:11px 12px;border-radius:10px;margin:2px 0;font-size:14px}}
.nav-link:hover{{background:#2f2f2f}}
.section-title{{color:#8e8e8e;text-transform:uppercase;font-size:11px;letter-spacing:.08em;padding:14px 12px 6px}}
.mini-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5px}}
.mini-link{{color:#d4d4d4;text-decoration:none;font-size:12px;padding:8px;border-radius:8px;background:#202020;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
.mini-link:hover{{background:#2f2f2f}}
.main{{margin-left:310px;width:calc(100% - 310px);min-height:100vh;display:flex;justify-content:center}}
.content{{width:100%;max-width:1180px;padding:28px}}
.topbar{{position:sticky;top:0;z-index:3;background:rgba(33,33,33,.86);backdrop-filter:blur(16px);border-bottom:1px solid rgba(255,255,255,.06);margin:-28px -28px 24px;padding:16px 28px;display:flex;justify-content:space-between;align-items:center}}
.topbar-title{{font-weight:700}} .topbar-badge{{background:#2f2f2f;border:1px solid #444;padding:8px 12px;border-radius:999px;color:#d6d6d6;font-size:13px}}
h1{{font-size:30px;margin:0 0 16px;letter-spacing:-.03em}} h2{{font-size:18px;margin:0 0 10px}} p{{color:#d4d4d4}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}}
.card{{background:var(--card);border:1px solid #3a3a3a;border-radius:18px;padding:20px;margin-bottom:14px;box-shadow:0 10px 30px rgba(0,0,0,.16)}}
.card:hover{{border-color:#555}}
.big{{color:#fff;font-size:32px;font-weight:800;letter-spacing:-.04em}}
input,select,textarea{{padding:14px 15px;border-radius:14px;border:1px solid #444;margin:7px 0;width:100%;background:#2f2f2f;color:white;outline:none;font-size:15px}}
textarea{{min-height:170px;resize:vertical}}
button{{padding:13px 18px;border:0;border-radius:12px;background:white;color:#111;font-weight:700;cursor:pointer}}
button:hover{{opacity:.88}}
table{{width:100%;border-collapse:separate;border-spacing:0;background:#262626;border:1px solid #3a3a3a;border-radius:16px;overflow:hidden}}
th,td{{padding:13px;border-bottom:1px solid #3a3a3a;vertical-align:top;font-size:14px}} th{{color:#bdbdbd;text-align:left;background:#202020}}
a{{color:#7dd3fc}} pre{{white-space:pre-wrap;line-height:1.55;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}}
.chat-wrap{{max-width:900px;margin:0 auto;min-height:calc(100vh - 120px);display:flex;flex-direction:column}}
.chat-hero{{text-align:center;padding:52px 20px 22px}} .chat-hero h1{{font-size:34px;margin-bottom:8px}}
.chat-box{{display:flex;flex-direction:column;gap:16px;margin-bottom:110px}}
.message{{display:flex;gap:14px;align-items:flex-start}} .message.user{{justify-content:flex-end}}
.avatar{{width:34px;height:34px;border-radius:50%;background:#3a3a3a;display:flex;align-items:center;justify-content:center;font-weight:800;flex:0 0 auto;font-size:12px}}
.avatar.ai{{background:var(--green)}}
.bubble{{background:#2f2f2f;border:1px solid #444;border-radius:18px;padding:16px;max-width:100%;line-height:1.55}}
.message.user .bubble{{background:#3a3a3a}}
.chat-input{{position:fixed;bottom:0;left:310px;right:0;background:linear-gradient(180deg,rgba(33,33,33,0),#212121 30%);padding:26px 24px}}
.chat-input-inner{{max-width:900px;margin:0 auto;display:flex;gap:10px;background:#2f2f2f;border:1px solid #555;border-radius:22px;padding:10px}}
.chat-input-inner textarea{{margin:0;min-height:52px;max-height:160px;border:0;background:transparent;resize:none}}
.chat-input-inner button{{border-radius:16px;padding:0 18px}}
.bar{{background:var(--green);height:18px;border-radius:10px}}
@media(max-width:850px){{.sidebar{{position:relative;width:100%;height:auto}}.shell{{display:block}}.main{{margin-left:0;width:100%}}.chat-input{{left:0}}}}
@media print{{.sidebar,.topbar,.chat-input{{display:none}}.main{{margin-left:0;width:100%}}body{{background:white;color:black}}.card{{border:1px solid #999;background:white;color:black}}}}
</style>
</head>
<body>
<div class="shell">
<aside class="sidebar">
<div class="brand"><div class="logo">SG</div><div><h2>StreetCore V44</h2><p>Stable Ultra Pro</p></div></div>
<div class="section-title">Sistema</div>{links}
<div class="section-title">Tabelas</div><div class="mini-grid">{table_links}</div>
</aside>
<main class="main"><div class="content"><div class="topbar"><div class="topbar-title">StreetCore OS</div><div class="topbar-badge">Visual estilo ChatGPT</div></div>{conteudo}</div></main>
</div>
</body>
</html>
"""


# =========================
# ERROS
# =========================

@app.errorhandler(404)
def tratar_404(e):
    registrar_erro(request.path, "404 rota não encontrada")
    return layout(f"""
    <h1>🔎 Página não encontrada</h1>
    <div class="card">
        <p>Essa página não existe nesta versão estável.</p>
        <p><strong>Rota:</strong> {request.path}</p>
        <a href="/">Voltar ao painel</a> · <a href="/workspace">Workspace</a> · <a href="/chat">Chat IA</a>
    </div>
    """), 404


@app.errorhandler(Exception)
def tratar_erro(e):
    registrar_erro(request.path, e)
    try:
        return layout(f"""
        <h1>⚠️ Erro controlado</h1>
        <div class="card">
            <p>O sistema encontrou um erro, mas não travou.</p>
            <pre>{str(e)}</pre>
            <a href="/">Voltar ao painel</a>
        </div>
        """), 500
    except Exception:
        return f"Erro controlado: {e}", 500


# =========================
# ROTAS WEB
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        user = sql("SELECT usuario, nivel FROM usuarios WHERE usuario=? AND senha=?", (usuario, senha), True)
        if user:
            session["ok"] = True
            session["usuario"] = user[0][0]
            session["nivel"] = user[0][1]
            return redirect("/")
        erro = "<p style='color:red'>Login incorreto</p>"
    return f"""
<body style="background:#212121;color:white;font-family:Arial;display:flex;align-items:center;justify-content:center;height:100vh">
<div style="background:#262626;padding:40px;border-radius:20px;width:350px;border:1px solid #444">
<h1>🔥 StreetCore V44</h1>{erro}
<form method="POST">
<input name="usuario" placeholder="Usuário" style="width:100%;padding:14px;margin-bottom:12px;border-radius:12px;background:#333;color:white;border:1px solid #555">
<input name="senha" type="password" placeholder="Senha" style="width:100%;padding:14px;margin-bottom:12px;border-radius:12px;background:#333;color:white;border:1px solid #555">
<button style="width:100%;padding:14px;background:white;border:0;border-radius:12px;font-weight:bold">Entrar</button>
</form><p>admin / streetcore</p></div></body>"""


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def home():
    if not login_required():
        return redirect("/login")
    receita, despesa, lucro = financeiro()
    cards = [
        ("💰 Receita", f"R$ {receita:.2f}"),
        ("📉 Despesa", f"R$ {despesa:.2f}"),
        ("📈 Lucro", f"R$ {lucro:.2f}"),
        ("🎯 Leads", contar("leads")),
        ("📦 Pedidos", contar("pedidos")),
        ("🧾 Propostas", contar("propostas")),
        ("🏭 Produção", contar("producao")),
        ("🤖 Chats", contar("chat_sessions")),
    ]
    html = "".join([f"<div class='card'><h2>{t}</h2><div class='big'>{v}</div></div>" for t, v in cards])
    return layout(f"""
    <h1>🚀 StreetCore V44 Luxury SaaS Pro</h1>
    <p>Painel estável, visual estilo ChatGPT, funções corrigidas e operação organizada.</p>
    <div class="grid">{html}</div>
    <div class="card"><h2>🧠 Centro de decisão</h2><pre>{relatorio_executivo()}</pre></div>
    """)


@app.route("/health")
def health():
    return jsonify({"status": "online", "version": "V44 LUXURY SAAS PRO", "webhook": bool(WEBHOOK_URL), "ollama": USE_OLLAMA})


@app.route("/workspace")
def workspace():
    if not login_required():
        return redirect("/login")
    return layout("""
    <h1>🧩 Workspace Operacional</h1>
    <div class="grid">
        <div class="card"><h2>Chat IA</h2><p>Converse com o sistema.</p><a href="/chat">Abrir chat</a></div>
        <div class="card"><h2>Criar</h2><p>Cadastre tudo.</p><a href="/criar">Criar registro</a></div>
        <div class="card"><h2>Pipeline</h2><p>Acompanhe vendas.</p><a href="/pipeline">Ver pipeline</a></div>
        <div class="card"><h2>Executivo</h2><p>Relatório principal.</p><a href="/executivo">Abrir</a></div>
        <div class="card"><h2>Kanban Leads</h2><p>Leads por temperatura.</p><a href="/kanban-leads">Abrir</a></div>
        <div class="card"><h2>Conteúdo</h2><p>Posts e campanhas.</p><a href="/conteudo">Criar</a></div>
    </div>
    """)


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if not login_required():
        return redirect("/login")
    pergunta = ""
    if request.method == "POST":
        pergunta = request.form.get("pergunta", "")
        chat_responder(pergunta)
    historico = listar("chat_sessions", 20)
    mensagens = ""
    for h in reversed(historico):
        mensagens += f"""
        <div class="message user"><div class="bubble">{h[2]}</div><div class="avatar">EU</div></div>
        <div class="message"><div class="avatar ai">AI</div><div class="bubble"><pre>{h[3]}</pre></div></div>
        """
    if not mensagens:
        mensagens = "<div class='chat-hero'><h1>Como posso ajudar sua operação hoje?</h1><p>Peça campanha, relatório, proposta ou diagnóstico.</p></div>"
    return layout(f"""
    <div class="chat-wrap">
        <div class="chat-box">{mensagens}</div>
        <form method="POST" class="chat-input">
            <div class="chat-input-inner">
                <textarea name="pergunta" placeholder="Envie uma mensagem para o StreetCore...">{pergunta}</textarea>
                <button>Enviar</button>
            </div>
        </form>
    </div>
    """)


@app.route("/criar", methods=["GET", "POST"])
def criar():
    if not login_required():
        return redirect("/login")
    msg = ""
    if request.method == "POST":
        tipo = texto_limpo(request.form.get("tipo"))
        nome = texto_limpo(request.form.get("nome"))
        extra = texto_limpo(request.form.get("extra"))
        valor = texto_limpo(request.form.get("valor"))
        try:
            if tipo == "pedido":
                inserir("pedidos", "nome, cliente, valor", (nome, extra, numero_float(valor)))
                inserir("pipeline", "cliente, etapa, valor, observacao", (extra, "pedido_criado", numero_float(valor), nome))
                msg = "Pedido criado."
            elif tipo == "lead":
                temp, score = score_lead(nome, extra, nome)
                inserir("leads", "nome, origem, temperatura", (nome, extra or "painel", temp))
                msg = f"Lead criado. Temperatura: {temp}."
            elif tipo == "cliente":
                inserir("clientes", "nome, contato, historico", (nome, extra, "Criado no painel"))
                msg = "Cliente criado."
            elif tipo == "produto":
                inserir("produtos", "nome, preco, descricao", (nome, numero_float(valor), extra))
                msg = "Produto criado."
            elif tipo == "estoque":
                inserir("estoque", "item, quantidade, minimo", (nome, numero_int(valor), 5))
                msg = "Estoque criado."
            elif tipo == "producao":
                inserir("producao", "item, cliente, status", (nome, extra, "aguardando"))
                msg = "Produção criada."
            elif tipo == "tarefa":
                inserir("tarefas", "titulo, status, prioridade", (nome, "pendente", extra or "normal"))
                msg = "Tarefa criada."
            elif tipo == "receita":
                inserir("financeiro", "tipo, valor, descricao", ("receita", numero_float(valor), nome or "Receita"))
                msg = "Receita criada."
            elif tipo == "despesa":
                inserir("financeiro", "tipo, valor, descricao", ("despesa", numero_float(valor), nome or "Despesa"))
                msg = "Despesa criada."
            elif tipo == "fornecedor":
                inserir("fornecedores", "nome, contato", (nome, extra))
                msg = "Fornecedor criado."
            elif tipo == "meta":
                inserir("metas", "nome, valor, status", (nome, valor or extra, "ativa"))
                msg = "Meta criada."
            elif tipo == "notificacao":
                inserir("notificacoes", "mensagem, status", (nome, "nova"))
                msg = "Notificação criada."
            else:
                msg = "Tipo inválido."
            auditar("criar", f"{tipo} | {nome} | {msg}")
        except Exception as e:
            msg = f"Erro ao criar: {e}"
    return layout(f"""
    <h1>➕ Criar Registro</h1>
    <div class="card"><p>{msg}</p>
    <form method="POST">
    <label>Tipo</label>
    <select name="tipo">
        <option value="pedido">Pedido</option><option value="lead">Lead</option><option value="cliente">Cliente</option>
        <option value="produto">Produto</option><option value="estoque">Estoque</option><option value="producao">Produção</option>
        <option value="tarefa">Tarefa</option><option value="receita">Receita</option><option value="despesa">Despesa</option>
        <option value="fornecedor">Fornecedor</option><option value="meta">Meta</option><option value="notificacao">Notificação</option>
    </select>
    <input name="nome" placeholder="Nome / descrição">
    <input name="extra" placeholder="Cliente, origem, contato, prioridade ou descrição">
    <input name="valor" placeholder="Valor ou quantidade">
    <button>Criar</button>
    </form></div>
    """)


@app.route("/executivo")
def executivo():
    if not login_required():
        return redirect("/login")
    return layout(f"<h1>📊 Executivo</h1><div class='card'><pre>{relatorio_executivo()}</pre></div>")


@app.route("/qualidade")
def qualidade():
    if not login_required():
        return redirect("/login")
    return layout(f"<h1>🛡️ Qualidade</h1><div class='card'><pre>{diagnostico_sistema()}</pre></div>")


@app.route("/quantum", methods=["GET", "POST"])
def quantum():
    if not login_required():
        return redirect("/login")
    resp = ""
    if request.method == "POST":
        comando = request.form.get("comando", "")
        resp = chat_responder(comando)
    return layout(f"<h1>⚛️ Quantum Command</h1><div class='card'><form method='POST'><input name='comando' placeholder='Digite uma ordem'><button>Executar</button></form></div><div class='card'><pre>{resp}</pre></div>")


@app.route("/master")
@app.route("/ultra")
@app.route("/neural")
def centros_ia():
    if not login_required():
        return redirect("/login")
    return layout(f"<h1>🧠 Centro IA</h1><div class='card'><pre>{conselho_multiagentes('Analise a operação e diga o que fazer agora.')}</pre></div>")


@app.route("/multiagentes", methods=["GET", "POST"])
def multiagentes():
    if not login_required():
        return redirect("/login")
    resp = ""
    if request.method == "POST":
        resp = agente_responder(request.form.get("agente"), request.form.get("pergunta"))
    agentes = sql("SELECT nome FROM agentes ORDER BY id", fetch=True)
    opts = "".join([f"<option>{a[0]}</option>" for a in agentes])
    return layout(f"<h1>🤖 Multiagentes</h1><div class='card'><form method='POST'><select name='agente'>{opts}</select><textarea name='pergunta'></textarea><button>Executar</button></form></div><div class='card'><pre>{resp}</pre></div>")


@app.route("/pipeline", methods=["GET", "POST"])
def pipeline():
    if not login_required():
        return redirect("/login")
    msg = ""
    if request.method == "POST":
        inserir("pipeline", "cliente, etapa, valor, observacao", (request.form.get("cliente"), request.form.get("etapa"), numero_float(request.form.get("valor")), request.form.get("obs")))
        msg = "Pipeline atualizado."
    dados = listar("pipeline", 100)
    rows = "".join([f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>R$ {numero_float(d[3]):.2f}</td><td>{d[4]}</td><td>{d[5]}</td></tr>" for d in dados])
    return layout(f"<h1>📊 Pipeline</h1><div class='card'><p>{msg}</p><form method='POST'><input name='cliente' placeholder='Cliente'><select name='etapa'><option>novo</option><option>contato</option><option>proposta</option><option>negociacao</option><option>fechado</option><option>perdido</option></select><input name='valor' placeholder='Valor'><input name='obs' placeholder='Obs'><button>Adicionar</button></form></div><div class='card'><pre>{pipeline_resumo()}</pre></div><table>{rows}</table>")


@app.route("/kanban-leads")
def kanban_leads():
    if not login_required():
        return redirect("/login")
    html = "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px'>"
    for col in ["frio", "morno", "quente"]:
        dados = sql("SELECT id,nome,origem,temperatura,criado_em FROM leads WHERE temperatura=? ORDER BY id DESC LIMIT 50", (col,), True)
        cards = "".join([f"<div class='card'><strong>#{d[0]} - {d[1]}</strong><p>Origem: {d[2]}</p><p>{d[3]}</p><small>{d[4]}</small></div>" for d in dados])
        html += f"<div><h2>{col.upper()}</h2>{cards}</div>"
    html += "</div>"
    return layout(f"<h1>🧲 Kanban Leads</h1>{html}")


@app.route("/kanban-producao")
def kanban_producao():
    if not login_required():
        return redirect("/login")
    html = "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:18px'>"
    for col in ["aguardando", "em_producao", "finalizado"]:
        dados = sql("SELECT id,item,cliente,status,criado_em FROM producao WHERE status=? ORDER BY id DESC LIMIT 50", (col,), True)
        cards = "".join([f"<div class='card'><strong>#{d[0]} - {d[1]}</strong><p>Cliente: {d[2]}</p><p>{d[3]}</p><small>{d[4]}</small></div>" for d in dados])
        html += f"<div><h2>{col.upper()}</h2>{cards}</div>"
    html += "</div>"
    return layout(f"<h1>🏭 Kanban Produção</h1>{html}")


@app.route("/conteudo", methods=["GET", "POST"])
def conteudo():
    if not login_required():
        return redirect("/login")
    res = ""
    if request.method == "POST":
        tema = request.form.get("tema", "Street Graff")
        tipo = request.form.get("tipo")
        res = campanha(tema) if tipo == "campanha" else reels(tema) if tipo == "reels" else story(tema) if tipo == "story" else post(tema)
        inserir("conteudos", "tema, tipo, texto, status", (tema, tipo, res, "rascunho"))
    return layout(f"<h1>🤖 Conteúdo IA</h1><div class='card'><form method='POST'><input name='tema' placeholder='Tema'><select name='tipo'><option>post</option><option>story</option><option>reels</option><option>campanha</option></select><button>Gerar</button></form></div><div class='card'><textarea>{res}</textarea></div>")


@app.route("/aprovacoes")
def aprovacoes():
    if not login_required():
        return redirect("/login")
    dados = sql("SELECT id,tema,tipo,texto,status,criado_em FROM conteudos ORDER BY id DESC LIMIT 100", fetch=True)
    rows = "".join([f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td><pre>{d[3]}</pre></td><td>{d[4]}</td><td><a href='/aprovar/{d[0]}'>Aprovar</a></td></tr>" for d in dados])
    return layout(f"<h1>✅ Aprovações</h1><table><tr><th>ID</th><th>Tema</th><th>Tipo</th><th>Texto</th><th>Status</th><th>Ação</th></tr>{rows}</table>")


@app.route("/aprovar/<int:item_id>")
def aprovar(item_id):
    if not login_required():
        return redirect("/login")
    sql("UPDATE conteudos SET status='aprovado' WHERE id=?", (item_id,))
    return redirect("/aprovacoes")


@app.route("/instagram")
def instagram():
    if not login_required():
        return redirect("/login")
    dados = listar("instagram_queue", 100)
    rows = "".join([f"<tr><td>{d[0]}</td><td>{d[1]}</td><td><pre>{d[2]}</pre></td><td>{d[3]}</td><td>{d[4]}</td><td>{d[5]}</td></tr>" for d in dados])
    return layout(f"<h1>📲 Instagram Queue</h1><table><tr><th>ID</th><th>Tipo</th><th>Conteúdo</th><th>Legenda</th><th>Status</th><th>Data</th></tr>{rows}</table>")


@app.route("/propostas", methods=["GET", "POST"])
def propostas():
    if not login_required():
        return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente = request.form.get("cliente")
        descricao = request.form.get("descricao")
        res = gerar_proposta(cliente, descricao)
        inserir("propostas", "cliente, descricao, valor, texto", (cliente, descricao, valor_orcamento(descricao), res))
    return layout(f"<h1>🧾 Propostas</h1><div class='card'><form method='POST'><input name='cliente' placeholder='Cliente'><textarea name='descricao' placeholder='Descrição'></textarea><button>Gerar</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/pdf-proposta", methods=["GET", "POST"])
def pdf_proposta():
    if not login_required():
        return redirect("/login")
    if request.method == "POST":
        buffer, tipo = gerar_pdf_proposta(request.form.get("cliente"), request.form.get("descricao"))
        if tipo == "pdf":
            return send_file(buffer, as_attachment=True, download_name="proposta_streetgraff.pdf", mimetype="application/pdf")
        return send_file(buffer, as_attachment=True, download_name="proposta_streetgraff.txt", mimetype="text/plain")
    return layout("<h1>📄 PDF Proposta</h1><div class='card'><form method='POST'><input name='cliente' placeholder='Cliente'><textarea name='descricao' placeholder='Descrição'></textarea><button>Gerar PDF</button></form></div>")


@app.route("/atendimento", methods=["GET", "POST"])
def atendimento():
    if not login_required():
        return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente = request.form.get("cliente", "cliente")
        pergunta = request.form.get("pergunta", "")
        res = faq(pergunta)
        inserir("atendimentos", "cliente, pergunta, resposta", (cliente, pergunta, res))
    return layout(f"<h1>💬 Atendimento</h1><div class='card'><form method='POST'><input name='cliente'><textarea name='pergunta'></textarea><button>Responder</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if not login_required():
        return redirect("/login")
    msg = ""
    if request.method == "POST":
        file = request.files.get("arquivo")
        if file:
            nome = limpar_nome(file.filename)
            path = os.path.join(UPLOAD_FOLDER, nome)
            file.save(path)
            texto = extrair_arquivo(path)
            inserir("uploads", "nome, tipo, texto", (nome, nome.split(".")[-1].lower(), texto[:12000]))
            inserir("conhecimento", "titulo, texto", (f"Upload: {nome}", texto[:12000]))
            msg = f"Arquivo salvo e lido: {nome}"
    return layout(f"<h1>📎 Upload</h1><div class='card'><p>{msg}</p><form method='POST' enctype='multipart/form-data'><input type='file' name='arquivo'><button>Enviar</button></form></div><pre>{listar('uploads', 20)}</pre>")


@app.route("/buscar", methods=["GET", "POST"])
def buscar_web():
    if not login_required():
        return redirect("/login")
    res = ""
    if request.method == "POST":
        res = buscar(request.form.get("termo", ""))
    return layout(f"<h1>🔎 Busca</h1><div class='card'><form method='POST'><input name='termo'><button>Buscar</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/financeiro")
def financeiro_web():
    if not login_required():
        return redirect("/login")
    r, d, l = financeiro()
    return layout(f"<h1>💵 Financeiro</h1><div class='grid'><div class='card'><h2>Receita</h2><div class='big'>R$ {r:.2f}</div></div><div class='card'><h2>Despesa</h2><div class='big'>R$ {d:.2f}</div></div><div class='card'><h2>Lucro</h2><div class='big'>R$ {l:.2f}</div></div></div>")


@app.route("/automacoes", methods=["GET", "POST"])
def automacoes():
    if not login_required():
        return redirect("/login")
    msg = ""
    if request.method == "POST":
        msg = rodar_automacoes()
    return layout(f"<h1>⚙️ Automações</h1><div class='card'><form method='POST'><button>Rodar automações</button></form></div><div class='card'><pre>{msg}</pre></div>")


@app.route("/portal-cliente")
def portal_cliente():
    return """
<html><body style="background:#212121;color:white;font-family:Arial;padding:30px">
<h1>🔥 Street Graff</h1>
<p>Camisetas, adesivos, canecas, panfletos e brindes personalizados.</p>
<form action="/cliente-orcamento" method="POST">
<input name="cliente" placeholder="Seu nome" style="padding:12px;width:100%;margin:6px;border-radius:10px">
<textarea name="descricao" placeholder="Descreva seu pedido" style="padding:12px;width:100%;height:120px;margin:6px;border-radius:10px"></textarea>
<button style="padding:12px;background:#10a37f;color:white;border:0;border-radius:10px">Enviar pedido</button>
</form>
</body></html>"""


@app.route("/cliente-orcamento", methods=["POST"])
def cliente_orcamento():
    cliente = request.form.get("cliente")
    descricao = request.form.get("descricao")
    codigo = criar_codigo_cliente()
    texto = gerar_proposta(cliente, descricao)
    inserir("leads", "nome, origem, temperatura", (cliente, "portal_cliente", "quente"))
    inserir("propostas", "cliente, descricao, valor, texto", (cliente, descricao, valor_orcamento(descricao), texto))
    inserir("cliente_portal", "cliente, pedido, status, codigo", (cliente, descricao, "recebido", codigo))
    return f"<pre>{texto}</pre><p>Código de acompanhamento: {codigo}</p><a href='/portal-cliente'>Voltar</a>"


@app.route("/table/<tabela>")
def table(tabela):
    if not login_required():
        return redirect("/login")
    if tabela not in SAFE_TABLES:
        return "Tabela não permitida"
    dados = listar(tabela, 1000)
    rows = "".join(["<tr>" + "".join([f"<td>{x}</td>" for x in d]) + f"<td><a href='/delete/{tabela}/{d[0]}'>Excluir</a></td></tr>" for d in dados])
    return layout(f"<h1>{tabela.title()}</h1><a href='/export/{tabela}'>Exportar CSV</a><table>{rows}</table>")


@app.route("/delete/<tabela>/<int:item_id>")
def delete(tabela, item_id):
    if not login_required():
        return redirect("/login")
    if not is_admin():
        return "Apenas admin."
    if tabela in SAFE_TABLES:
        sql(f"DELETE FROM {tabela} WHERE id=?", (item_id,))
    return redirect(f"/table/{tabela}")


@app.route("/export/<tabela>")
def export(tabela):
    if not login_required():
        return redirect("/login")
    if tabela not in SAFE_TABLES:
        return "Tabela não permitida"
    output = io.StringIO()
    writer = csv.writer(output)
    for row in listar(tabela, 10000):
        writer.writerow(row)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={tabela}.csv"})


@app.route("/export-completo")
def export_completo():
    if not login_required():
        return redirect("/login")
    output = io.StringIO()
    writer = csv.writer(output)
    for tabela in SAFE_TABLES:
        writer.writerow([])
        writer.writerow([f"TABELA: {tabela}"])
        for row in listar(tabela, 10000):
            writer.writerow(row)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=streetcore_export_completo.csv"})


@app.route("/backup")
def backup():
    if not login_required():
        return redirect("/login")
    nome = f"backup_v43_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    destino = os.path.join(BACKUP_FOLDER, nome)
    shutil.copy(DB_PATH, destino)
    with open(destino, "rb") as f:
        data = f.read()
    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={nome}"})


@app.route("/api/info")
def api_info():
    return jsonify({"version": "V44 LUXURY SAAS PRO", "api_key_header": "X-API-Key", "tables": SAFE_TABLES})


def api_auth():
    return request.headers.get("X-API-Key") == API_KEY


@app.route("/api/relatorio")
def api_relatorio():
    if not api_auth():
        return jsonify({"erro": "API key inválida"}), 403
    return jsonify({"relatorio": relatorio_executivo()})


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    if not telegram_app or not telegram_loop:
        return "bot indisponível", 503
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), telegram_loop)
    return "ok"


# =========================
# TELEGRAM
# =========================

async def send(update, texto):
    await update.message.reply_text(str(texto)[:3900])


async def start_cmd(update, context):
    await send(update, "🔥 STREETCORE V44\n/chat mensagem\n/relatorio\n/pedido camiseta joao\n/lead maria instagram\n/proposta joao 10 camisetas\n/receita 100\n/despesa 50\n/post camisetas\n/campanha street graff\n/buscar joao")


async def chat_cmd(update, context):
    await send(update, chat_responder(" ".join(context.args) or "Me dê um plano para hoje."))


async def relatorio_cmd(update, context):
    await send(update, relatorio_executivo())


async def post_cmd(update, context):
    await send(update, post(" ".join(context.args) or "Street Graff"))


async def campanha_cmd(update, context):
    await send(update, campanha(" ".join(context.args) or "Street Graff"))


async def buscar_cmd(update, context):
    await send(update, buscar(" ".join(context.args)))


async def pedido_cmd(update, context):
    inserir("pedidos", "nome, cliente", (context.args[0] if context.args else "", " ".join(context.args[1:])))
    await send(update, "📦 Pedido criado.")


async def lead_cmd(update, context):
    nome = context.args[0] if context.args else ""
    origem = " ".join(context.args[1:]) or "telegram"
    temp, score = score_lead(nome, origem, nome)
    inserir("leads", "nome, origem, temperatura", (nome, origem, temp))
    await send(update, f"🎯 Lead criado. Temperatura: {temp}. Score: {score}")


async def proposta_cmd(update, context):
    cliente = context.args[0] if context.args else "cliente"
    descricao = " ".join(context.args[1:]) or "pedido"
    texto = gerar_proposta(cliente, descricao)
    inserir("propostas", "cliente, descricao, valor, texto", (cliente, descricao, valor_orcamento(descricao), texto))
    await send(update, texto)


async def receita_cmd(update, context):
    valor = numero_float(context.args[0] if context.args else 0)
    inserir("financeiro", "tipo, valor, descricao", ("receita", valor, "telegram"))
    await send(update, f"💰 Receita R$ {valor:.2f}")


async def despesa_cmd(update, context):
    valor = numero_float(context.args[0] if context.args else 0)
    inserir("financeiro", "tipo, valor, descricao", ("despesa", valor, "telegram"))
    await send(update, f"💸 Despesa R$ {valor:.2f}")


async def documento_cmd(update, context):
    doc = update.message.document
    nome = limpar_nome(doc.file_name)
    path = os.path.join(UPLOAD_FOLDER, nome)
    arquivo = await context.bot.get_file(doc.file_id)
    await arquivo.download_to_drive(path)
    texto = extrair_arquivo(path)
    inserir("uploads", "nome, tipo, texto", (nome, nome.split(".")[-1].lower(), texto[:12000]))
    inserir("conhecimento", "titulo, texto", (f"Telegram upload: {nome}", texto[:12000]))
    await send(update, f"✅ Arquivo salvo e lido: {nome}\n\nPrévia:\n{texto[:1000]}")


async def responder(update, context):
    msg = update.message.text
    log(msg)
    memoria_salvar("mensagem_usuario", msg)
    await send(update, faq(msg))


async def telegram_main():
    global telegram_app, telegram_loop
    telegram_loop = asyncio.get_event_loop()
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    comandos = {
        "start": start_cmd,
        "chat": chat_cmd,
        "relatorio": relatorio_cmd,
        "pedido": pedido_cmd,
        "lead": lead_cmd,
        "proposta": proposta_cmd,
        "receita": receita_cmd,
        "despesa": despesa_cmd,
        "post": post_cmd,
        "campanha": campanha_cmd,
        "buscar": buscar_cmd,
        "luxury": luxury_cmd,
    }

    for nome, funcao in comandos.items():
        telegram_app.add_handler(CommandHandler(nome, funcao))

    telegram_app.add_handler(MessageHandler(filters.Document.ALL, documento_cmd))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V44...")
    await telegram_app.initialize()
    await telegram_app.start()

    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(f"{WEBHOOK_URL.rstrip('/')}/telegram-webhook")
        print("✅ Telegram WEBHOOK ativo V44")
    else:
        await telegram_app.updater.start_polling()
        print("✅ Telegram POLLING ativo V44")

    await asyncio.Event().wait()


def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())



# =========================
# V44 LUXURY SAAS PRO EXTRA
# =========================

def gerar_contrato_texto(cliente, servico, valor):
    return f"""📄 CONTRATO DE PRESTAÇÃO DE SERVIÇO - STREET GRAFF

CONTRATANTE: {cliente}
CONTRATADA: Street Graff

SERVIÇO:
{servico}

VALOR:
R$ {numero_float(valor):.2f}

CONDIÇÕES:
1. O pagamento é realizado via PIX.
2. A produção inicia após confirmação do pagamento e aprovação dos detalhes.
3. O prazo padrão é de 5 dias úteis + prazo de transporte.
4. Alterações após aprovação podem gerar custo adicional.
5. A Street Graff não se responsabiliza por atraso causado por informações incompletas enviadas pelo cliente.

Este documento foi gerado automaticamente pelo StreetCore OS.
"""


def gerar_pdf_texto(titulo, texto, nome_arquivo):
    buffer = io.BytesIO()

    if canvas is None:
        buffer.write(texto.encode("utf-8"))
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=nome_arquivo.replace(".pdf", ".txt"), mimetype="text/plain")

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, titulo[:80])
    y -= 35
    c.setFont("Helvetica", 11)

    for linha in texto.split("\n"):
        if y < 60:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = height - 50
        c.drawString(50, y, linha[:95])
        y -= 17

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=nome_arquivo, mimetype="application/pdf")


def criar_templates_padrao():
    padroes = [
        ("Post Venda", "post", "🔥 Sua marca precisa aparecer! Personalizados Street Graff: camisetas, adesivos, canecas e brindes. Chama no direct."),
        ("Follow-up Cliente", "mensagem", "Oi! Passando para saber se você quer fechar seu orçamento com a Street Graff hoje."),
        ("Story Oferta", "story", "Tela 1: Quer personalizar sua marca?\\nTela 2: Camisetas, adesivos, canecas e brindes\\nTela 3: Chama no direct."),
        ("Contrato Simples", "contrato", "Contrato simples de prestação de serviço com pagamento via PIX e prazo de 5 dias úteis.")
    ]
    criados = 0
    for nome, tipo, conteudo in padroes:
        existe = sql("SELECT id FROM templates WHERE nome=?", (nome,), True)
        if not existe:
            inserir("templates", "nome, tipo, conteudo", (nome, tipo, conteudo))
            criados += 1
    return f"Templates padrão verificados. Novos criados: {criados}"


def luxury_resumo():
    receita, despesa, lucro = financeiro()
    return f"""💎 V44 LUXURY SAAS PRO

Status do sistema:
✅ Visual ChatGPT Premium
✅ Painel SaaS
✅ Templates
✅ Contratos
✅ Agenda
✅ Status de pedido
✅ Portal cliente
✅ Chat IA
✅ PDF
✅ Backup
✅ Kanban
✅ Pipeline
✅ Automação

Financeiro:
Receita: R$ {receita:.2f}
Despesa: R$ {despesa:.2f}
Lucro: R$ {lucro:.2f}

Operação:
Leads: {contar('leads')}
Pedidos: {contar('pedidos')}
Propostas: {contar('propostas')}
Contratos: {contar('contratos')}
Templates: {contar('templates')}
Agenda: {contar('agenda')}

Próximas ações:
1. Criar templates da sua marca.
2. Usar agenda para organizar entregas.
3. Gerar contratos em PDF.
4. Usar status público para clientes.
5. Criar painel multiempresa na próxima versão.
"""


@app.route("/luxury")
def luxury_page():
    if not login_required():
        return redirect("/login")
    return layout(f"""
    <h1>💎 V44 Luxury SaaS Pro</h1>
    <div class="card"><pre>{luxury_resumo()}</pre></div>
    <div class="grid">
        <div class="card"><h2>Templates</h2><p>Modelos prontos para posts, stories e mensagens.</p><a href="/templates">Abrir</a></div>
        <div class="card"><h2>Contratos</h2><p>Gere contrato e PDF profissional.</p><a href="/contratos">Abrir</a></div>
        <div class="card"><h2>Agenda</h2><p>Organize entregas, tarefas e datas.</p><a href="/agenda">Abrir</a></div>
        <div class="card"><h2>Status Pedido</h2><p>Atualize e acompanhe pedidos.</p><a href="/status-pedido">Abrir</a></div>
    </div>
    """)


@app.route("/templates", methods=["GET", "POST"])
def templates_page():
    if not login_required():
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "padrao":
            msg = criar_templates_padrao()
        else:
            inserir("templates", "nome, tipo, conteudo", (
                request.form.get("nome", ""),
                request.form.get("tipo", ""),
                request.form.get("conteudo", "")
            ))
            msg = "Template criado."

    dados = listar("templates", 100)
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td><pre>{d[3]}</pre></td><td>{d[4]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>🧩 Biblioteca de Templates</h1>
    <div class="card">
        <p>{msg}</p>
        <form method="POST">
            <input type="hidden" name="acao" value="criar">
            <input name="nome" placeholder="Nome do template">
            <select name="tipo">
                <option>post</option>
                <option>story</option>
                <option>reels</option>
                <option>mensagem</option>
                <option>contrato</option>
                <option>proposta</option>
            </select>
            <textarea name="conteudo" placeholder="Conteúdo do template"></textarea>
            <button>Criar template</button>
        </form>
        <form method="POST" style="margin-top:10px">
            <input type="hidden" name="acao" value="padrao">
            <button>Criar templates padrão</button>
        </form>
    </div>
    <table>
        <tr><th>ID</th><th>Nome</th><th>Tipo</th><th>Conteúdo</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/contratos", methods=["GET", "POST"])
def contratos_page():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        cliente = request.form.get("cliente", "")
        servico = request.form.get("servico", "")
        valor = numero_float(request.form.get("valor"), 0)
        resposta = gerar_contrato_texto(cliente, servico, valor)
        inserir("contratos", "cliente, servico, valor, texto", (cliente, servico, valor, resposta))

    dados = listar("contratos", 50)
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>R$ {numero_float(d[3]):.2f}</td><td><a href='/contrato-pdf/{d[0]}'>PDF</a></td><td>{d[5]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>📄 Contratos</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Cliente">
            <textarea name="servico" placeholder="Serviço contratado"></textarea>
            <input name="valor" placeholder="Valor">
            <button>Gerar contrato</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    <table>
        <tr><th>ID</th><th>Cliente</th><th>Serviço</th><th>Valor</th><th>PDF</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/contrato-pdf/<int:item_id>")
def contrato_pdf(item_id):
    if not login_required():
        return redirect("/login")

    dados = sql("SELECT cliente, servico, valor, texto FROM contratos WHERE id=?", (item_id,), True)
    if not dados:
        return "Contrato não encontrado."

    cliente, servico, valor, texto = dados[0]
    return gerar_pdf_texto("Contrato Street Graff", texto, f"contrato_{cliente}.pdf")


@app.route("/agenda", methods=["GET", "POST"])
def agenda_page():
    if not login_required():
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        inserir("agenda", "titulo, data, hora, status", (
            request.form.get("titulo", ""),
            request.form.get("data", ""),
            request.form.get("hora", ""),
            request.form.get("status", "pendente")
        ))
        msg = "Evento criado."

    dados = listar("agenda", 100)
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td><td>{d[5]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>📅 Agenda Visual</h1>
    <div class="card">
        <p>{msg}</p>
        <form method="POST">
            <input name="titulo" placeholder="Título">
            <input name="data" placeholder="Data Ex: 2026-05-20">
            <input name="hora" placeholder="Hora Ex: 15:00">
            <select name="status">
                <option>pendente</option>
                <option>feito</option>
                <option>cancelado</option>
            </select>
            <button>Criar evento</button>
        </form>
    </div>
    <table>
        <tr><th>ID</th><th>Título</th><th>Data</th><th>Hora</th><th>Status</th><th>Criado</th></tr>
        {linhas}
    </table>
    """)


@app.route("/status-pedido", methods=["GET", "POST"])
def status_pedido_page():
    if not login_required():
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        codigo = request.form.get("codigo") or criar_codigo_cliente()
        inserir("status_pedidos", "codigo, cliente, pedido, status, observacao", (
            codigo,
            request.form.get("cliente", ""),
            request.form.get("pedido", ""),
            request.form.get("status", "recebido"),
            request.form.get("observacao", "")
        ))
        msg = f"Status criado/registrado. Código: {codigo}"

    dados = listar("status_pedidos", 100)
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td><td>{d[5]}</td><td>{d[6]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>📦 Status de Pedido</h1>
    <div class="card">
        <p>{msg}</p>
        <form method="POST">
            <input name="codigo" placeholder="Código existente ou deixe vazio">
            <input name="cliente" placeholder="Cliente">
            <input name="pedido" placeholder="Pedido">
            <select name="status">
                <option>recebido</option>
                <option>em_producao</option>
                <option>pronto</option>
                <option>enviado</option>
                <option>entregue</option>
            </select>
            <input name="observacao" placeholder="Observação">
            <button>Salvar status</button>
        </form>
    </div>
    <table>
        <tr><th>ID</th><th>Código</th><th>Cliente</th><th>Pedido</th><th>Status</th><th>Obs</th><th>Data</th></tr>
        {linhas}
    </table>
    """)


@app.route("/acompanhar")
def acompanhar_publico():
    codigo = request.args.get("codigo", "")
    dados = sql("SELECT codigo,cliente,pedido,status,observacao,criado_em FROM status_pedidos WHERE codigo=? ORDER BY id DESC LIMIT 1", (codigo,), True)

    if not dados:
        return """
        <html><body style="font-family:Arial;padding:30px">
        <h1>Acompanhar pedido</h1>
        <form>
            <input name="codigo" placeholder="Código do pedido" style="padding:12px;width:100%">
            <button style="padding:12px;margin-top:10px">Buscar</button>
        </form>
        <p>Pedido não encontrado.</p>
        </body></html>
        """

    d = dados[0]
    return f"""
    <html><body style="font-family:Arial;padding:30px">
    <h1>Status do Pedido</h1>
    <p><strong>Código:</strong> {d[0]}</p>
    <p><strong>Cliente:</strong> {d[1]}</p>
    <p><strong>Pedido:</strong> {d[2]}</p>
    <p><strong>Status:</strong> {d[3]}</p>
    <p><strong>Observação:</strong> {d[4]}</p>
    <p><strong>Atualizado:</strong> {d[5]}</p>
    </body></html>
    """


async def luxury_cmd(update, context):
    await send(update, luxury_resumo())

iniciar_banco()

threading.Thread(target=scheduler_loop, daemon=True).start()
threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
