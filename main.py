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


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v36-autonomous-empire")
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
        valor REAL,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "produtos": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        preco REAL,
        descricao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "estoque": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        quantidade INTEGER,
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
        valor REAL,
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
    "workflows": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        gatilho TEXT,
        acao TEXT,
        status TEXT DEFAULT 'ativo',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "voz": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        arquivo TEXT,
        transcricao TEXT,
        resposta TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "imagem_jobs": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT,
        prompt TEXT,
        status TEXT DEFAULT 'prompt_criado',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "video_jobs": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tema TEXT,
        roteiro TEXT,
        status TEXT DEFAULT 'roteiro_criado',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "empresas": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        nicho TEXT,
        status TEXT DEFAULT 'ativa',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "analytics": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        valor TEXT,
        observacao TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """,
    "pipeline": "id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,etapa TEXT,valor REAL DEFAULT 0,observacao TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "oportunidades": "id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,produto TEXT,valor REAL DEFAULT 0,probabilidade INTEGER DEFAULT 50,status TEXT DEFAULT 'aberta',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "auditoria": "id INTEGER PRIMARY KEY AUTOINCREMENT,acao TEXT,detalhes TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "ideias": "id INTEGER PRIMARY KEY AUTOINCREMENT,tema TEXT,ideia TEXT,status TEXT DEFAULT 'nova',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "rotinas": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,descricao TEXT,status TEXT DEFAULT 'ativa',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "eventos": "id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT,data TEXT,status TEXT DEFAULT 'pendente',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "cliente_portal": "id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,pedido TEXT,status TEXT DEFAULT 'recebido',codigo TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "erros": "id INTEGER PRIMARY KEY AUTOINCREMENT,rota TEXT,erro TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "configuracoes": "id INTEGER PRIMARY KEY AUTOINCREMENT,chave TEXT,valor TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "logs": """
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mensagem TEXT,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    """
}

SAFE_TABLES = list(TABLES.keys())

MIGRATIONS = {
    "leads": {"temperatura": "TEXT DEFAULT 'frio'"},
    "estoque": {"minimo": "INTEGER DEFAULT 5"},
    "tarefas": {"prioridade": "TEXT DEFAULT 'normal'"},
    "pedidos": {"valor": "REAL DEFAULT 0"},
    "conteudos": {"status": "TEXT DEFAULT 'rascunho'"},
    "propostas": {"status": "TEXT DEFAULT 'aberta'"},
}


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


def iniciar_banco():
    for nome, schema in TABLES.items():
        sql(f"CREATE TABLE IF NOT EXISTS {nome} ({schema})")

    for tabela, colunas in MIGRATIONS.items():
        existentes = [c[1] for c in sql(f"PRAGMA table_info({tabela})", fetch=True)]
        for coluna, tipo in colunas.items():
            if coluna not in existentes:
                try:
                    sql(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
                except Exception:
                    pass

    if not sql("SELECT * FROM usuarios WHERE usuario=?", (ADMIN_USER,), True):
        sql(
            "INSERT INTO usuarios (usuario, senha, nivel) VALUES (?, ?, ?)",
            (ADMIN_USER, ADMIN_PASS, "admin")
        )

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
            sql(
                "INSERT INTO agentes (nome, funcao, ultima_resposta) VALUES (?, ?, ?)",
                (nome, funcao, "Aguardando primeira execução.")
            )

    print("✅ StreetCore OS V40 QUANTUM ENTERPRISE CORE iniciado.")


def inserir(tabela, campos, valores):
    q = ",".join(["?"] * len(valores))
    sql(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)


def listar(tabela, limite=200):
    if tabela not in SAFE_TABLES:
        return []
    return sql(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT ?", (limite,), True)


def contar(tabela):
    return sql(f"SELECT COUNT(*) FROM {tabela}", fetch=True)[0][0]


def log(msg):
    inserir("logs", "mensagem", (str(msg),))


def financeiro():
    receita = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'", fetch=True)[0][0] or 0
    despesa = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'", fetch=True)[0][0] or 0
    lucro = receita - despesa
    return receita, despesa, lucro


def login_required():
    return session.get("ok") is True


def is_admin():
    return session.get("nivel") == "admin"

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



def permissao_minima(nivel_necessario):
    ordem = {"operador": 1, "vendedor": 2, "producao": 2, "financeiro": 2, "admin": 9}
    atual = session.get("nivel", "operador")
    return ordem.get(atual, 0) >= ordem.get(nivel_necessario, 1)


def registrar_erro(rota, erro):
    try:
        inserir("erros", "rota, erro", (str(rota), str(erro)))
    except Exception:
        pass


def status_badge(status):
    status = str(status or "").lower()
    cores = {
        "novo": "#00ff88",
        "pendente": "#ffaa00",
        "aberta": "#ffaa00",
        "aguardando": "#ffaa00",
        "finalizado": "#00ccff",
        "fechado": "#00ff88",
        "perdido": "#ff5555",
        "cancelado": "#ff5555",
        "quente": "#ff5555",
        "morno": "#ffaa00",
        "frio": "#00ccff",
    }
    cor = cores.get(status, "#888")
    return f"<span style='background:{cor};color:#000;padding:5px 9px;border-radius:8px;font-weight:bold'>{status}</span>"


def tabela_segura(tabela):
    return tabela in SAFE_TABLES

def limpar_nome(nome):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", nome or "arquivo")
def texto_limpo(valor, padrao=""):
    try:
        valor = "" if valor is None else str(valor).strip()
        return valor if valor else padrao
    except Exception:
        return padrao


def dinheiro_br(valor):
    try:
        return f"R$ {float(valor):.2f}"
    except Exception:
        return "R$ 0.00"



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
        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False
        }).encode("utf-8")

        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=35) as res:
            data = json.loads(res.read().decode("utf-8"))
            return data.get("response", "")

    except Exception:
        return ""


def memoria_salvar(chave, valor):
    inserir("memoria", "chave, valor", (chave, valor))


def memoria_buscar(chave):
    dados = sql(
        "SELECT valor FROM memoria WHERE chave LIKE ? ORDER BY id DESC LIMIT 5",
        (f"%{chave}%",),
        True
    )
    if not dados:
        return ""
    return "\n".join([d[0] for d in dados])


def post(tema):
    prompt = f"""
Crie um post de Instagram para a Street Graff.
Tema: {tema}
Produtos: camisetas, adesivos, canecas, panfletos e brindes.
Tom: jovem, direto, street, vendedor.
Inclua CTA e hashtags.
"""
    ia = ollama(prompt)
    if ia:
        return ia

    return f"""🔥 POST PRONTO - {tema.upper()}

Sua marca precisa aparecer com presença.
A Street Graff cria camisetas, adesivos, canecas, panfletos e brindes personalizados.

📲 Chama no direct e peça seu orçamento.
Pagamento via PIX.

#streetgraff #personalizados #camisetaspersonalizadas"""


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
    texto = f"""
{post(tema)}

---

{story(tema)}

---

{reels(tema)}

✅ Ação:
1. Postar hoje às 18h.
2. Subir stories em 3 etapas.
3. Fazer reels com bastidor.
4. Salvar leads.
5. Chamar clientes no direct.
"""
    inserir("campanhas", "tema, texto, status", (tema, texto, "planejada"))
    return texto


def valor_orcamento(desc):
    t = desc.lower()
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

    arte = 20 if "arte" in t or "design" in t else 0
    urgencia = 30 if "urgente" in t else 0

    return base * qtd + arte + urgencia


def gerar_proposta(cliente, desc):
    valor = valor_orcamento(desc)
    texto = f"""🧾 PROPOSTA COMERCIAL STREET GRAFF

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
    return texto


def contrato(cliente, servico, valor):
    return f"""📄 CONTRATO SIMPLES

Contratante: {cliente}
Contratada: Street Graff
Serviço: {servico}
Valor: R$ {valor}

Condições:
1. Pagamento via PIX.
2. Produção em até 5 dias úteis após confirmação.
3. Alterações após aprovação podem gerar custo extra.
4. Produção inicia após pagamento e confirmação final."""


def faq(pergunta):
    p = pergunta.lower()

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
    if "panfleto" in p:
        return "Fazemos panfletos personalizados para divulgação."
    if "brinde" in p:
        return "Fazemos brindes personalizados conforme o pedido."

    ia = ollama(f"Responda como atendente da Street Graff: {pergunta}")
    if ia:
        return ia

    return "Fazemos camisetas, adesivos, canecas, panfletos e brindes personalizados."


def plano():
    return """✅ PLANO NEURAL DO DIA

1. Ver leads novos.
2. Responder clientes.
3. Criar campanha de venda.
4. Gerar post + story + reels.
5. Aprovar conteúdo pendente.
6. Atualizar pedidos.
7. Conferir produção.
8. Conferir estoque.
9. Registrar receitas e despesas.
10. Gerar propostas para leads quentes.
11. Consultar uploads/conhecimento.
12. Rodar automações.
13. Fazer backup.
14. Fechar pelo menos 1 venda."""


def relatorio():
    receita, despesa, lucro = financeiro()
    linhas = []

    for tabela in [
        "pedidos", "leads", "clientes", "propostas", "produtos", "estoque",
        "producao", "tarefas", "campanhas", "conteudos", "documentos",
        "conhecimento", "uploads", "atendimentos", "automacoes",
        "agentes", "instagram_queue"
    ]:
        linhas.append(f"{tabela}: {contar(tabela)}")

    return "📊 RELATÓRIO NEURAL EMPIRE V35\n\n" + "\n".join(linhas) + f"""

Receita: R$ {receita:.2f}
Despesa: R$ {despesa:.2f}
Lucro: R$ {lucro:.2f}

Decisão:
✅ captar leads;
✅ gerar campanha;
✅ aprovar posts;
✅ criar propostas;
✅ acompanhar produção;
✅ rodar automações;
✅ proteger dados com backup."""


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

    if not blocos:
        return "Nenhum resultado encontrado."
    return "\n\n".join(blocos)


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


def agente_responder(nome, pergunta):
    dados = sql("SELECT funcao FROM agentes WHERE nome=?", (nome,), True)
    funcao = dados[0][0] if dados else "Agente geral"
    contexto = relatorio()

    prompt = f"""
Você é o agente {nome}.
Função: {funcao}

Contexto atual da operação:
{contexto}

Pergunta/comando:
{pergunta}

Responda de forma prática, direta e operacional.
"""
    ia = ollama(prompt)

    if not ia:
        ia = f"""🤖 {nome}

Função: {funcao}

Recomendação:
1. Verificar dados atuais.
2. Criar ação prática.
3. Registrar resultado.
4. Acompanhar execução.

Comando recebido:
{pergunta}"""

    sql("UPDATE agentes SET ultima_resposta=? WHERE nome=?", (ia, nome))
    return ia


def conselho_multiagentes(comando):
    agentes = [
        "CEO IA", "Vendas IA", "Marketing IA", "Atendimento IA",
        "Financeiro IA", "Produção IA", "Social Media IA"
    ]
    respostas = []
    for ag in agentes:
        respostas.append(f"### {ag}\n{agente_responder(ag, comando)}")
    return "\n\n".join(respostas)


def rodar_automacoes():
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    inserir("tarefas", "titulo, status, prioridade", (f"Revisar leads novos - {agora}", "pendente", "alta"))
    inserir("notificacoes", "mensagem, status", (f"Rodar campanha diária - {agora}", "nova"))

    texto_post = post("Street Graff")

    inserir("conteudos", "tema, tipo, texto, status", ("Street Graff", "post_auto", texto_post, "rascunho"))
    inserir("instagram_queue", "tipo, conteudo, legenda, status", ("post", texto_post, "Legenda gerada automaticamente.", "aguardando_aprovacao"))
    inserir("automacoes", "nome, acao, status", ("auto_diaria", f"Executada em {agora}", "ativa"))

    return "Automações executadas: tarefa, notificação, post e fila Instagram criados."


def scheduler_loop():
    ultima_execucao = None

    while True:
        try:
            agora = datetime.now()
            if agora.hour == 9 and ultima_execucao != agora.date():
                rodar_automacoes()
                ultima_execucao = agora.date()
        except Exception as e:
            log(f"Erro scheduler: {e}")

        time.sleep(60)




def gerar_prompt_imagem(tema):
    prompt = f"""Arte publicitária profissional para Street Graff sobre {tema}, estilo urbano, alto contraste, visual streetwear, fundo preto, detalhes brancos, produto em destaque, composição premium para Instagram, sem texto pequeno, qualidade de anúncio."""
    inserir("imagem_jobs", "tema, prompt, status", (tema, prompt, "prompt_criado"))
    return prompt


def gerar_roteiro_video(tema):
    roteiro = f"""🎥 ROTEIRO VÍDEO IA - {tema.upper()}

0-2s: Gancho forte: \"Sua marca ainda passa despercebida?\"
3-6s: Mostrar produto personalizado da Street Graff.
7-11s: Mostrar bastidor/produção/detalhe.
12-16s: Mostrar resultado final.
17-20s: CTA: \"Chama no direct e peça seu orçamento.\"

Estilo: TikTok/Reels, cortes rápidos, música urbana, legenda grande, energia de venda."""
    inserir("video_jobs", "tema, roteiro, status", (tema, roteiro, "roteiro_criado"))
    return roteiro


def operador_ia(comando):
    analise = conselho_multiagentes(comando)
    tema = comando or "Street Graff"
    texto_post = post(tema)
    proposta_auto = gerar_proposta("Lead automático", tema)
    inserir("tarefas", "titulo, status, prioridade", (f"Executar operador IA: {tema}", "pendente", "alta"))
    inserir("conteudos", "tema, tipo, texto, status", (tema, "operador_post", texto_post, "rascunho"))
    inserir("instagram_queue", "tipo, conteudo, legenda, status", ("post", texto_post, "Legenda criada pelo Operador IA", "aguardando_aprovacao"))
    return f"""⚡ OPERADOR IA EXECUTADO

Comando: {comando}

Ações criadas:
✅ tarefa operacional
✅ post em rascunho
✅ fila Instagram
✅ análise multiagentes

--- ANÁLISE ---
{analise}

--- PROPOSTA BASE ---
{proposta_auto}"""


def criar_workflow_padrao():
    inserir("workflows", "nome, gatilho, acao, status", (
        "Novo lead para proposta",
        "novo_lead",
        "criar_proposta + criar_tarefa_followup + criar_conteudo",
        "ativo"
    ))
    return "Workflow padrão criado: novo lead → proposta → follow-up → conteúdo."


def executar_workflows():
    leads = sql("SELECT id,nome,origem,temperatura FROM leads WHERE temperatura IN ('quente','morno') ORDER BY id DESC LIMIT 5", fetch=True)
    total = 0
    for lead in leads:
        lead_id, nome, origem, temp = lead
        desc = f"Orçamento personalizado para {nome} vindo de {origem}"
        texto = gerar_proposta(nome, desc)
        inserir("propostas", "cliente, descricao, valor, texto", (nome, desc, valor_orcamento(desc), texto))
        inserir("tarefas", "titulo, status, prioridade", (f"Follow-up com {nome}", "pendente", "alta"))
        total += 1
    return f"Workflows executados. Leads processados: {total}"


def gerar_analytics():
    receita, despesa, lucro = financeiro()
    pedidos = contar("pedidos")
    leads = contar("leads")
    propostas = contar("propostas")
    taxa = round((pedidos / leads) * 100, 2) if leads else 0
    texto = f"Receita R$ {receita:.2f}; Despesa R$ {despesa:.2f}; Lucro R$ {lucro:.2f}; Leads {leads}; Pedidos {pedidos}; Propostas {propostas}; Conversão estimada {taxa}%"
    inserir("analytics", "tipo, valor, observacao", ("resumo", str(lucro), texto))
    return f"📈 ANALYTICS IA\n\n{texto}\n\nSugestão: gerar campanha, seguir leads mornos/quentes e revisar estoque."

def layout(conteudo):
    menu = [
        ("Dashboard", "/"),
        ("Criar", "/criar"),
        ("Neural Center", "/neural"),
        ("Quantum", "/quantum"),
        ("Executivo", "/executivo"),
        ("Kanban Leads", "/kanban-leads"),
        ("Kanban Produção", "/kanban-producao"),
        ("Portal Cliente", "/portal-cliente"),
        ("Erros", "/erros"),
        ("Export Completo", "/export-completo"),
        ("Master V40", "/master"),
        ("Ultra Infinity", "/ultra"),
        ("Pipeline", "/pipeline"),
        ("Oportunidades", "/oportunidades"),
        ("Auditoria", "/auditoria"),
        ("Ideias IA", "/ideias-ia"),
        ("Rotinas", "/rotinas"),
        ("Alertas", "/alertas"),
        ("Follow-up", "/followup"),
        ("Singularity", "/singularity"),
        ("Workflow Vendas", "/workflow-vendas"),
        ("Funil", "/funil"),
        ("Decisão Máxima", "/decisao-maxima"),
        ("Multiagentes", "/multiagentes"),
        ("Conteúdo IA", "/conteudo"),
        ("Aprovação Posts", "/aprovacoes"),
        ("Instagram Queue", "/instagram"),
        ("Operador IA", "/operador"),
        ("Workflows", "/workflows"),
        ("Voz IA", "/voz"),
        ("Imagem IA", "/imagem-ia"),
        ("Vídeo IA", "/video-ia"),
        ("Analytics IA", "/analytics"),
        ("Multiempresa", "/empresas"),
        ("Propostas", "/propostas"),
        ("PDF Proposta", "/pdf-proposta"),
        ("Atendimento", "/atendimento"),
        ("Upload", "/upload"),
        ("Busca", "/buscar"),
        ("Financeiro", "/financeiro"),
        ("Relatório", "/relatorio"),
        ("Automações", "/automacoes"),
        ("Usuários", "/usuarios"),
        ("Modo Cliente", "/cliente"),
        ("API Info", "/api/info"),
        ("Backup", "/backup"),
        ("Restaurar", "/restore")
    ]

    tables = [
        "pedidos", "leads", "clientes", "produtos", "estoque",
        "producao", "tarefas", "campanhas", "conteudos",
        "documentos", "conhecimento", "uploads", "atendimentos",
        "fornecedores", "notificacoes", "metas", "automacoes",
        "memoria", "agentes", "instagram_queue", "workflows", "voz", "imagem_jobs", "video_jobs", "empresas", "analytics", "logs"
    ]

    links = "".join([f"<a href='{url}'>{nome}</a>" for nome, url in menu])
    links += "<hr>" + "".join([f"<a href='/table/{t}'>{t.title()}</a>" for t in tables])

    return f"""
<html>
<head>
<title>StreetCore V40 Singularity Empire</title>
<style>
body{{margin:0;background:#050505;color:#fff;font-family:Arial;}}
.sidebar{{position:fixed;top:0;left:0;bottom:0;width:315px;background:#0b0b0b;border-right:1px solid #222;padding:24px;overflow:auto;}}
.sidebar h2{{color:#00ff88;}}
.sidebar a{{display:block;color:white;text-decoration:none;margin:11px 0;}}
.sidebar a:hover{{color:#00ff88;}}
.main{{margin-left:365px;padding:30px;}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:18px;}}
.card{{background:#111;border:1px solid #333;border-radius:18px;padding:22px;margin-bottom:18px;}}
.big{{color:#00ff88;font-size:34px;font-weight:bold;}}
input,select,textarea{{padding:12px;border-radius:10px;border:0;margin:6px 0;width:100%;background:#1c1c1c;color:white;}}
textarea{{min-height:170px;}}
button{{padding:12px 18px;border:0;border-radius:10px;background:#00ff88;font-weight:bold;cursor:pointer;}}
table{{width:100%;border-collapse:collapse;background:#111;}}
th,td{{padding:12px;border-bottom:1px solid #333;vertical-align:top;}}
a{{color:#00ff88;}}
pre{{white-space:pre-wrap;}}
.bar{{background:#00ff88;height:18px;border-radius:10px;}}
@media print{{
.sidebar{{display:none;}}
.main{{margin-left:0;}}
body{{background:white;color:black;}}
.card{{border:1px solid #999;background:white;color:black;}}
}}
</style>
</head>
<body>
<div class="sidebar">
<h2>🔥 StreetCore V40</h2>
{links}
<a href="/logout">Sair</a>
</div>
<div class="main">
{conteudo}
</div>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    erro = ""

    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        user = sql(
            "SELECT usuario, nivel FROM usuarios WHERE usuario=? AND senha=?",
            (usuario, senha),
            True
        )

        if user:
            session["ok"] = True
            session["usuario"] = user[0][0]
            session["nivel"] = user[0][1]
            return redirect("/")

        erro = "<p style='color:red'>Login incorreto</p>"

    return f"""
<body style="background:#050505;color:white;font-family:Arial;display:flex;align-items:center;justify-content:center;height:100vh">
<div style="background:#111;padding:40px;border-radius:20px;width:330px">
<h1>🔥 StreetCore V40</h1>
{erro}
<form method="POST">
<input name="usuario" placeholder="Usuário" style="width:100%;padding:14px;margin-bottom:12px">
<input name="senha" type="password" placeholder="Senha" style="width:100%;padding:14px;margin-bottom:12px">
<button style="width:100%;padding:14px;background:#00ff88;border:0;border-radius:10px;font-weight:bold">Entrar</button>
</form>
<p>admin / streetcore</p>
</div>
</body>
"""


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/")
def home():
    if not login_required():
        return redirect("/login")

    receita, despesa, lucro = financeiro()
    cards = ""

    for tabela in [
        "pedidos", "leads", "clientes", "propostas", "conteudos",
        "uploads", "produtos", "estoque", "producao", "tarefas",
        "atendimentos", "agentes", "instagram_queue"
    ]:
        cards += f"""
        <div class="card">
            <h2>{tabela.title()}</h2>
            <div class="big">{contar(tabela)}</div>
        </div>
        """

    cards += f"""
    <div class="card"><h2>Receita</h2><div class="big">R$ {receita:.2f}</div></div>
    <div class="card"><h2>Lucro</h2><div class="big">R$ {lucro:.2f}</div></div>
    """

    grafico = f"""
    <div class="card">
        <h2>Gráfico rápido</h2>
        <p>Receita</p><div class="bar" style="width:{min(receita / 10, 100)}%"></div>
        <p>Despesa</p><div class="bar" style="width:{min(despesa / 10, 100)}%"></div>
        <p>Lucro</p><div class="bar" style="width:{min(max(lucro, 0) / 10, 100)}%"></div>
    </div>
    """

    return layout(f"""
    <h1>🔥 STREETCORE OS V40 QUANTUM ENTERPRISE CORE FREE</h1>
    <p>ERP + CRM + IA + Multiagentes + Automação + Ollama + Webhook.</p>
    <div class="grid">{cards}</div>
    {grafico}
    <div class="card"><pre>{plano()}</pre></div>
    """)


@app.route("/health")
def health():
    return jsonify({
        "status": "online",
        "version": "V40 QUANTUM ENTERPRISE CORE FREE",
        "webhook": bool(WEBHOOK_URL),
        "ollama": USE_OLLAMA,
        "ollama_url": bool(OLLAMA_URL)
    })


@app.route("/neural", methods=["GET", "POST"])
def neural():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        comando = request.form.get("comando", "")
        resposta = conselho_multiagentes(comando)

    return layout(f"""
    <h1>🧠 Neural Center</h1>
    <div class="card">
        <form method="POST">
            <input name="comando" placeholder="Ex: como vender mais camisetas hoje?">
            <button>Analisar com multiagentes</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    """)


@app.route("/multiagentes", methods=["GET", "POST"])
def multiagentes():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        agente = request.form.get("agente")
        pergunta = request.form.get("pergunta")
        resposta = agente_responder(agente, pergunta)

    agentes = sql("SELECT nome FROM agentes ORDER BY id", fetch=True)
    opcoes = "".join([f"<option value='{a[0]}'>{a[0]}</option>" for a in agentes])

    return layout(f"""
    <h1>🤖 Multiagentes IA</h1>
    <div class="card">
        <form method="POST">
            <select name="agente">{opcoes}</select>
            <textarea name="pergunta" placeholder="Digite a missão para o agente"></textarea>
            <button>Executar agente</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    """)


@app.route("/conteudo", methods=["GET", "POST"])
def conteudo():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        tema = request.form.get("tema", "Street Graff")
        tipo = request.form.get("tipo")

        if tipo == "campanha":
            resultado = campanha(tema)
        elif tipo == "reels":
            resultado = reels(tema)
        elif tipo == "story":
            resultado = story(tema)
        else:
            resultado = post(tema)

        inserir("conteudos", "tema, tipo, texto, status", (tema, tipo, resultado, "rascunho"))

    return layout(f"""
    <h1>🤖 Conteúdo IA</h1>
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


@app.route("/aprovacoes")
def aprovacoes():
    if not login_required():
        return redirect("/login")

    dados = sql("""
        SELECT id, tema, tipo, texto, status, criado_em
        FROM conteudos
        ORDER BY id DESC
        LIMIT 100
    """, fetch=True)

    linhas = "".join([
        f"""
        <tr>
            <td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td>
            <td><pre>{d[3]}</pre></td><td>{d[4]}</td>
            <td><a href="/aprovar/{d[0]}">Aprovar</a></td>
        </tr>
        """
        for d in dados
    ])

    return layout(f"""
    <h1>✅ Aprovação de Posts</h1>
    <table>
        <tr><th>ID</th><th>Tema</th><th>Tipo</th><th>Texto</th><th>Status</th><th>Ação</th></tr>
        {linhas}
    </table>
    """)


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
    linhas = "".join([
        f"<tr><td>{d[0]}</td><td>{d[1]}</td><td><pre>{d[2]}</pre></td><td>{d[3]}</td><td>{d[4]}</td><td>{d[5]}</td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>📲 Instagram Queue</h1>
    <p>Fila semi-automática: gere, aprove e poste manualmente ou integre API depois.</p>
    <table>
        <tr><th>ID</th><th>Tipo</th><th>Conteúdo</th><th>Legenda</th><th>Status</th><th>Data</th></tr>
        {linhas}
    </table>
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
        inserir("propostas", "cliente, descricao, valor, texto", (cliente, descricao, valor_orcamento(descricao), resultado))

    return layout(f"""
    <h1>🧾 Propostas</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Cliente">
            <textarea name="descricao" placeholder="Descrição do pedido"></textarea>
            <button>Gerar proposta</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    """)


@app.route("/pdf-proposta", methods=["GET", "POST"])
def pdf_proposta():
    if not login_required():
        return redirect("/login")

    if request.method == "POST":
        cliente = request.form.get("cliente")
        descricao = request.form.get("descricao")
        buffer, tipo = gerar_pdf_proposta(cliente, descricao)

        if tipo == "pdf":
            return send_file(buffer, as_attachment=True, download_name="proposta_streetgraff.pdf", mimetype="application/pdf")

        return send_file(buffer, as_attachment=True, download_name="proposta_streetgraff.txt", mimetype="text/plain")

    return layout("""
    <h1>📄 Gerar PDF de Proposta</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Cliente">
            <textarea name="descricao" placeholder="Descrição do pedido"></textarea>
            <button>Gerar PDF</button>
        </form>
    </div>
    """)


@app.route("/atendimento", methods=["GET", "POST"])
def atendimento():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        cliente = request.form.get("cliente", "cliente")
        pergunta = request.form.get("pergunta", "")
        resposta = faq(pergunta)
        inserir("atendimentos", "cliente, pergunta, resposta", (cliente, pergunta, resposta))

    return layout(f"""
    <h1>💬 Atendimento IA</h1>
    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Cliente">
            <textarea name="pergunta" placeholder="Pergunta do cliente"></textarea>
            <button>Responder</button>
        </form>
    </div>
    <div class="card"><pre>{resposta}</pre></div>
    """)


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

    return layout(f"""
    <h1>📎 Upload TXT/PDF</h1>
    <div class="card">
        <p>{msg}</p>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="arquivo">
            <button>Enviar</button>
        </form>
    </div>
    <pre>{listar("uploads", 20)}</pre>
    """)


@app.route("/buscar", methods=["GET", "POST"])
def buscar_web():
    if not login_required():
        return redirect("/login")

    resultado = ""

    if request.method == "POST":
        resultado = buscar(request.form.get("termo", ""))

    return layout(f"""
    <h1>🔎 Busca Inteligente</h1>
    <div class="card">
        <form method="POST">
            <input name="termo" placeholder="Buscar em pedidos, leads, uploads, conhecimento...">
            <button>Buscar</button>
        </form>
    </div>
    <div class="card"><pre>{resultado}</pre></div>
    """)


@app.route("/automacoes", methods=["GET", "POST"])
def automacoes():
    if not login_required():
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        msg = rodar_automacoes()

    return layout(f"""
    <h1>⚙️ Automações</h1>
    <div class="card">
        <form method="POST">
            <button>Rodar automações agora</button>
        </form>
    </div>
    <div class="card"><pre>{msg}</pre></div>
    <pre>{listar("automacoes")}</pre>
    """)


@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    if not login_required():
        return redirect("/login")
    if not is_admin():
        return "Apenas admin."

    msg = ""

    if request.method == "POST":
        try:
            inserir("usuarios", "usuario, senha, nivel", (request.form.get("usuario"), request.form.get("senha"), request.form.get("nivel")))
            msg = "Usuário criado."
        except Exception as e:
            msg = f"Erro: {e}"

    return layout(f"""
    <h1>👤 Usuários</h1>
    <div class="card">
        <p>{msg}</p>
        <form method="POST">
            <input name="usuario" placeholder="Usuário">
            <input name="senha" placeholder="Senha">
            <select name="nivel">
                <option value="admin">admin</option>
                <option value="operador">operador</option>
            </select>
            <button>Criar</button>
        </form>
    </div>
    <pre>{listar("usuarios")}</pre>
    """)


@app.route("/cliente")
def cliente_publico():
    return """
<html>
<body style="background:#050505;color:white;font-family:Arial;padding:30px">
<h1>🔥 Street Graff</h1>
<p>Camisetas, adesivos, canecas, panfletos e brindes personalizados.</p>
<p>Pagamento somente via PIX.</p>
<p>Prazo: 5 dias úteis + transporte.</p>
<h2>Peça orçamento</h2>
<form action="/cliente-orcamento" method="POST">
<input name="cliente" placeholder="Seu nome" style="padding:12px;width:100%;margin:6px">
<textarea name="descricao" placeholder="O que você quer?" style="padding:12px;width:100%;height:120px;margin:6px"></textarea>
<button style="padding:12px;background:#00ff88;border:0;border-radius:10px">Enviar</button>
</form>
</body>
</html>
"""


@app.route("/cliente-orcamento", methods=["POST"])
def cliente_orcamento():
    cliente = request.form.get("cliente")
    descricao = request.form.get("descricao")
    texto = gerar_proposta(cliente, descricao)

    inserir("leads", "nome, origem, temperatura", (cliente, "modo_cliente", "quente"))
    inserir("propostas", "cliente, descricao, valor, texto", (cliente, descricao, valor_orcamento(descricao), texto))

    return f"<pre>{texto}</pre><a href='/cliente'>Voltar</a>"



@app.route("/operador", methods=["GET", "POST"])
def operador():
    if not login_required():
        return redirect("/login")
    resposta = ""
    if request.method == "POST":
        resposta = operador_ia(request.form.get("comando", ""))
    return layout(f"""
    <h1>⚡ Operador IA Autônomo</h1>
    <div class="card"><form method="POST"><input name="comando" placeholder="Ex: vender mais camisetas hoje"><button>Executar Operador IA</button></form></div>
    <div class="card"><pre>{resposta}</pre></div>
    """)


@app.route("/workflows", methods=["GET", "POST"])
def workflows():
    if not login_required():
        return redirect("/login")
    msg = ""
    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "criar":
            msg = criar_workflow_padrao()
        elif acao == "executar":
            msg = executar_workflows()
    return layout(f"""
    <h1>🔁 Workflows Automáticos</h1>
    <div class="card">
        <form method="POST"><button name="acao" value="criar">Criar workflow padrão</button> <button name="acao" value="executar">Executar workflows agora</button></form>
    </div>
    <div class="card"><pre>{msg}</pre></div>
    <pre>{listar('workflows')}</pre>
    """)


@app.route("/voz", methods=["GET", "POST"])
def voz_page():
    if not login_required():
        return redirect("/login")
    msg = ""
    if request.method == "POST":
        texto = request.form.get("texto", "")
        resposta = faq(texto)
        inserir("voz", "arquivo, transcricao, resposta", ("texto_manual", texto, resposta))
        msg = resposta
    return layout(f"""
    <h1>🎙️ Voz IA</h1>
    <p>Modo gratuito: registra texto/transcrição. Áudio real pode ser conectado depois com Whisper local.</p>
    <div class="card"><form method="POST"><textarea name="texto" placeholder="Digite ou cole uma transcrição de áudio"></textarea><button>Responder</button></form></div>
    <div class="card"><pre>{msg}</pre></div>
    <pre>{listar('voz')}</pre>
    """)


@app.route("/imagem-ia", methods=["GET", "POST"])
def imagem_ia():
    if not login_required():
        return redirect("/login")
    prompt = ""
    if request.method == "POST":
        prompt = gerar_prompt_imagem(request.form.get("tema", "Street Graff"))
    return layout(f"""
    <h1>🎨 Imagem IA</h1>
    <p>Gera prompt pronto para Stable Diffusion, Leonardo, Bing Image Creator ou outra IA grátis.</p>
    <div class="card"><form method="POST"><input name="tema" placeholder="Tema da arte"><button>Gerar prompt</button></form></div>
    <div class="card"><pre>{prompt}</pre></div>
    <pre>{listar('imagem_jobs')}</pre>
    """)


@app.route("/video-ia", methods=["GET", "POST"])
def video_ia():
    if not login_required():
        return redirect("/login")
    roteiro = ""
    if request.method == "POST":
        roteiro = gerar_roteiro_video(request.form.get("tema", "Street Graff"))
    return layout(f"""
    <h1>🎬 Vídeo IA</h1>
    <p>Gera roteiro/prompt para CapCut, TikTok, Canva, Runway ou IA de vídeo gratuita.</p>
    <div class="card"><form method="POST"><input name="tema" placeholder="Tema do vídeo"><button>Gerar roteiro</button></form></div>
    <div class="card"><pre>{roteiro}</pre></div>
    <pre>{listar('video_jobs')}</pre>
    """)


@app.route("/analytics", methods=["GET", "POST"])
def analytics_page():
    if not login_required():
        return redirect("/login")
    res = ""
    if request.method == "POST":
        res = gerar_analytics()
    return layout(f"""
    <h1>📈 Analytics IA</h1>
    <div class="card"><form method="POST"><button>Gerar análise agora</button></form></div>
    <div class="card"><pre>{res}</pre></div>
    <pre>{listar('analytics')}</pre>
    """)


@app.route("/empresas", methods=["GET", "POST"])
def empresas():
    if not login_required():
        return redirect("/login")
    msg = ""
    if request.method == "POST":
        inserir("empresas", "nome, nicho, status", (request.form.get("nome"), request.form.get("nicho"), "ativa"))
        msg = "Empresa criada."
    return layout(f"""
    <h1>🏢 Multiempresa</h1>
    <div class="card"><p>{msg}</p><form method="POST"><input name="nome" placeholder="Nome da empresa"><input name="nicho" placeholder="Nicho"><button>Criar empresa</button></form></div>
    <pre>{listar('empresas')}</pre>
    """)

@app.route("/financeiro")
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


@app.route("/relatorio")
def relatorio_web():
    if not login_required():
        return redirect("/login")

    return layout(f"""
    <h1>📊 Relatório Neural Empire</h1>
    <div class="card"><pre>{relatorio()}</pre></div>
    """)


@app.route("/table/<tabela>")
def table(tabela):
    if not login_required():
        return redirect("/login")

    if tabela not in SAFE_TABLES:
        return "Tabela não permitida"

    dados = listar(tabela, 1000)
    linhas = "".join([
        "<tr>" + "".join([f"<td>{x}</td>" for x in d]) + f"<td><a href='/delete/{tabela}/{d[0]}'>Excluir</a></td></tr>"
        for d in dados
    ])

    return layout(f"""
    <h1>{tabela.title()}</h1>
    <a href="/export/{tabela}">Exportar CSV</a>
    <table>{linhas}</table>
    """)


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

    rows = listar(tabela, 10000)
    output = io.StringIO()
    writer = csv.writer(output)

    for row in rows:
        writer.writerow(row)

    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename={tabela}.csv"})


@app.route("/backup")
def backup():
    if not login_required():
        return redirect("/login")

    nome = f"backup_v35_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    destino = os.path.join(BACKUP_FOLDER, nome)
    shutil.copy(DB_PATH, destino)

    with open(destino, "rb") as f:
        data = f.read()

    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition": f"attachment;filename={nome}"})


@app.route("/restore", methods=["GET", "POST"])
def restore():
    if not login_required():
        return redirect("/login")
    if not is_admin():
        return "Apenas admin."

    msg = ""

    if request.method == "POST":
        file = request.files.get("backup")
        if file and file.filename.endswith(".db"):
            safety = os.path.join(BACKUP_FOLDER, f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            shutil.copy(DB_PATH, safety)
            file.save(DB_PATH)
            iniciar_banco()
            msg = "Backup restaurado. Backup de segurança criado antes da restauração."

    return layout(f"""
    <h1>♻️ Restaurar Backup</h1>
    <div class="card">
        <p>{msg}</p>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="backup">
            <button>Restaurar</button>
        </form>
    </div>
    """)


@app.route("/api/info")
def api_info():
    return jsonify({
        "version": "V40 QUANTUM ENTERPRISE CORE FREE",
        "api_key_header": "X-API-Key",
        "tables": SAFE_TABLES
    })


def api_auth():
    return request.headers.get("X-API-Key") == API_KEY


@app.route("/api/relatorio")
def api_relatorio():
    if not api_auth():
        return jsonify({"erro": "API key inválida"}), 403
    return jsonify({"relatorio": relatorio()})


@app.route("/api/table/<tabela>")
def api_table(tabela):
    if not api_auth():
        return jsonify({"erro": "API key inválida"}), 403
    if tabela not in SAFE_TABLES:
        return jsonify({"erro": "tabela inválida"}), 400
    return jsonify({"dados": listar(tabela)})


@app.route("/api/create/<tabela>", methods=["POST"])
def api_create(tabela):
    if not api_auth():
        return jsonify({"erro": "API key inválida"}), 403

    data = request.json or {}

    try:
        if tabela == "pedidos":
            inserir("pedidos", "nome, cliente, valor", (data.get("nome"), data.get("cliente"), float(data.get("valor", 0))))
        elif tabela == "leads":
            inserir("leads", "nome, origem, temperatura", (data.get("nome"), data.get("origem", "api"), data.get("temperatura", "frio")))
        else:
            return jsonify({"erro": "criação permitida apenas para pedidos/leads"}), 400

        return jsonify({"status": "criado"})

    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    if not telegram_app or not telegram_loop:
        return "bot indisponível", 503

    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), telegram_loop)

    return "ok"


async def send(update, texto):
    await update.message.reply_text(str(texto)[:3900])


async def start_cmd(update, context):
    await send(update,
        "🔥 STREETCORE V40 QUANTUM ENTERPRISE CORE\n\n"
        "/neural vender mais hoje\n"
        "/agentes campanha de camisetas\n"
        "/relatorio\n"
        "/pedido camiseta joao\n"
        "/lead maria instagram\n"
        "/proposta joao 10 camisetas\n"
        "/receita 100\n"
        "/despesa 50\n"
        "/financeiro\n"
        "/post camisetas\n"
        "/campanha street graff\n"
        "/buscar joao"
    )


async def neural_cmd(update, context):
    await send(update, conselho_multiagentes(" ".join(context.args)))


async def agentes_cmd(update, context):
    await send(update, conselho_multiagentes(" ".join(context.args)))


async def op_cmd(update, context):
    await send(update, operador_ia(" ".join(context.args)))


async def imagem_cmd(update, context):
    await send(update, gerar_prompt_imagem(" ".join(context.args) or "Street Graff"))


async def video_cmd(update, context):
    await send(update, gerar_roteiro_video(" ".join(context.args) or "Street Graff"))


async def workflow_cmd(update, context):
    await send(update, executar_workflows())


async def analytics_cmd(update, context):
    await send(update, gerar_analytics())


async def relatorio_cmd(update, context):
    await send(update, relatorio())


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
    inserir("leads", "nome, origem, temperatura", (context.args[0] if context.args else "", " ".join(context.args[1:]) or "telegram", "morno"))
    await send(update, "🎯 Lead criado.")


async def proposta_cmd(update, context):
    cliente = context.args[0] if context.args else "cliente"
    descricao = " ".join(context.args[1:]) or "pedido"
    texto = gerar_proposta(cliente, descricao)

    inserir("propostas", "cliente, descricao, valor, texto", (cliente, descricao, valor_orcamento(descricao), texto))
    await send(update, texto)


async def receita_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    inserir("financeiro", "tipo, valor, descricao", ("receita", valor, "telegram"))
    await send(update, f"💰 Receita R$ {valor:.2f}")


async def despesa_cmd(update, context):
    valor = float(context.args[0].replace(",", "."))
    inserir("financeiro", "tipo, valor, descricao", ("despesa", valor, "telegram"))
    await send(update, f"💸 Despesa R$ {valor:.2f}")


async def financeiro_cmd(update, context):
    receita, despesa, lucro = financeiro()
    await send(update, f"""
💵 FINANCEIRO

Receita: R$ {receita:.2f}
Despesa: R$ {despesa:.2f}
Lucro: R$ {lucro:.2f}
""")




async def receber_voz(update, context):
    voice = update.message.voice
    nome = f"voz_{datetime.now().strftime('%Y%m%d_%H%M%S')}.ogg"
    path = os.path.join(UPLOAD_FOLDER, nome)
    arquivo = await context.bot.get_file(voice.file_id)
    await arquivo.download_to_drive(path)
    resposta = "Áudio recebido e salvo. Para transcrição real, conecte Whisper local depois."
    inserir("voz", "arquivo, transcricao, resposta", (nome, "transcricao_pendente", resposta))
    await send(update, resposta)

async def receber_documento(update, context):
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
    mensagem = update.message.text
    log(mensagem)
    memoria_salvar("mensagem_usuario", mensagem)
    await send(update, faq(mensagem))


async def telegram_main():
    global telegram_app, telegram_loop

    telegram_loop = asyncio.get_event_loop()
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    comandos = {
        "start": start_cmd,
        "op": op_cmd,
        "imagem": imagem_cmd,
        "video": video_cmd,
        "workflow": workflow_cmd,
        "analytics": analytics_cmd,
        "neural": neural_cmd,
        "agentes": agentes_cmd,
        "relatorio": relatorio_cmd,
        "pedido": pedido_cmd,
        "lead": lead_cmd,
        "proposta": proposta_cmd,
        "receita": receita_cmd,
        "despesa": despesa_cmd,
        "financeiro": financeiro_cmd,
        "post": post_cmd,
        "campanha": campanha_cmd,
        "buscar": buscar_cmd,
        "singularity": singularity_cmd,
        "funil": funil_cmd,
        "workflow": workflow_cmd
    }

    for nome, funcao in comandos.items():
        telegram_app.add_handler(CommandHandler(nome, funcao))
    for nome, funcao in {
        "quantum": quantum_cmd,
        "executivo": executivo_cmd,
        "kanban": kanban_cmd
    }.items():
        telegram_app.add_handler(CommandHandler(nome, funcao))
    for nome, funcao in {
        "ultra": ultra_cmd,
        "pipeline": pipeline_cmd,
        "oportunidade": oportunidades_cmd,
        "organizar": organizar_cmd,
        "ideias_ultra": ideias_ultra_cmd,
        "proposta_avancada": proposta_avancada_cmd
    }.items():
        telegram_app.add_handler(CommandHandler(nome, funcao))
    for nome, funcao in {
        "master": master_cmd,
        "diagnostico": diagnostico_cmd,
        "followup": followup_cmd
    }.items():
        telegram_app.add_handler(CommandHandler(nome, funcao))

    telegram_app.add_handler(MessageHandler(filters.VOICE, receber_voz))
    telegram_app.add_handler(MessageHandler(filters.Document.ALL, receber_documento))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V35...")

    await telegram_app.initialize()
    await telegram_app.start()

    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(f"{WEBHOOK_URL.rstrip('/')}/telegram-webhook")
        print("✅ Telegram WEBHOOK ativo V35")
    else:
        await telegram_app.updater.start_polling()
        print("✅ Telegram POLLING ativo V35")

    await asyncio.Event().wait()


def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())




@app.errorhandler(Exception)
def tratar_erro_global(e):
    try:
        registrar_erro(request.path, e)
    except Exception:
        pass

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
# V40 QUANTUM ENTERPRISE CORE EXTRA
# =========================

def workflow_vendas(cliente, descricao):
    valor = valor_orcamento(descricao)
    texto = gerar_proposta(cliente, descricao)

    inserir("leads", "nome, origem, temperatura", (cliente, "workflow_vendas", "quente"))
    inserir("propostas", "cliente, descricao, valor, texto", (cliente, descricao, valor, texto))
    inserir("tarefas", "titulo, status, prioridade", (f"Follow-up com {cliente}", "pendente", "alta"))
    inserir("notificacoes", "mensagem, status", (f"Novo workflow de venda criado para {cliente}", "nova"))

    return f"""🔥 WORKFLOW DE VENDAS EXECUTADO

Cliente: {cliente}
Pedido: {descricao}
Valor estimado: R$ {valor:.2f}

Ações feitas:
✅ lead quente criado
✅ proposta criada
✅ tarefa de follow-up criada
✅ notificação criada

PROPOSTA:
{texto}
"""


def operador_total(comando):
    comando_lower = comando.lower()

    if "vender" in comando_lower or "campanha" in comando_lower:
        tema = comando.replace("vender", "").replace("campanha", "").strip() or "Street Graff"
        texto = campanha(tema)
        inserir("tarefas", "titulo, status, prioridade", (f"Executar campanha: {tema}", "pendente", "alta"))
        return f"🚀 Operador criou campanha e tarefa:\n\n{texto}"

    if "relatorio" in comando_lower or "analisar" in comando_lower:
        return conselho_multiagentes(comando)

    if "backup" in comando_lower:
        return "Use o botão Backup no painel para baixar o banco com segurança."

    return f"""🤖 OPERADOR SINGULARITY

Comando recebido:
{comando}

Plano sugerido:
1. Criar campanha se o objetivo for venda.
2. Criar proposta se houver cliente.
3. Criar tarefa de follow-up.
4. Conferir financeiro.
5. Atualizar produção.
6. Rodar automações.
"""


def funil_vendas():
    try:
        frio = sql("SELECT COUNT(*) FROM leads WHERE temperatura='frio'", fetch=True)[0][0]
        morno = sql("SELECT COUNT(*) FROM leads WHERE temperatura='morno'", fetch=True)[0][0]
        quente = sql("SELECT COUNT(*) FROM leads WHERE temperatura='quente'", fetch=True)[0][0]
    except Exception:
        frio = morno = quente = 0

    abertas = contar("propostas")
    pedidos = contar("pedidos")

    return f"""📈 FUNIL DE VENDAS

Leads frios: {frio}
Leads mornos: {morno}
Leads quentes: {quente}
Propostas: {abertas}
Pedidos: {pedidos}

Ação recomendada:
✅ transformar leads quentes em propostas
✅ fazer follow-up dos mornos
✅ criar campanha para gerar novos leads
"""


@app.route("/singularity", methods=["GET", "POST"])
def singularity_center():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        comando = request.form.get("comando", "")
        resposta = operador_total(comando)

    return layout(f"""
    <h1>👑 V40 Quantum Enterprise Center</h1>

    <div class="card">
        <form method="POST">
            <input name="comando" placeholder="Ex: vender mais camisetas hoje">
            <button>Executar Operador</button>
        </form>
    </div>

    <div class="card">
        <pre>{resposta}</pre>
    </div>
    """)


@app.route("/workflow-vendas", methods=["GET", "POST"])
def workflow_vendas_page():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        cliente = request.form.get("cliente", "cliente")
        descricao = request.form.get("descricao", "pedido")
        resposta = workflow_vendas(cliente, descricao)

    return layout(f"""
    <h1>⚡ Workflow de Vendas</h1>

    <div class="card">
        <form method="POST">
            <input name="cliente" placeholder="Nome do cliente">
            <textarea name="descricao" placeholder="Descrição do pedido"></textarea>
            <button>Executar workflow</button>
        </form>
    </div>

    <div class="card">
        <pre>{resposta}</pre>
    </div>
    """)


@app.route("/funil")
def funil_page():
    if not login_required():
        return redirect("/login")

    return layout(f"""
    <h1>📈 Funil de Vendas</h1>
    <div class="card">
        <pre>{funil_vendas()}</pre>
    </div>
    """)


@app.route("/decisao-maxima")
def decisao_maxima():
    if not login_required():
        return redirect("/login")

    analise = conselho_multiagentes("Analise a operação inteira e diga as próximas ações mais importantes.")

    return layout(f"""
    <h1>🧠 Decisão Máxima</h1>
    <div class="card">
        <pre>{analise}</pre>
    </div>
    """)


# Comandos extras V40 no Telegram
async def singularity_cmd(update, context):
    await send(update, operador_total(" ".join(context.args)))


async def funil_cmd(update, context):
    await send(update, funil_vendas())


async def workflow_cmd(update, context):
    if len(context.args) < 2:
        await send(update, "Use: /workflow cliente descricao_do_pedido")
        return

    cliente = context.args[0]
    descricao = " ".join(context.args[1:])
    await send(update, workflow_vendas(cliente, descricao))



@app.errorhandler(Exception)
def tratar_erro_global(e):
    try:
        registrar_erro(request.path, e)
    except Exception:
        pass

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
# V40 QUANTUM ENTERPRISE EXTRA
# =========================

def diagnostico_sistema():
    receita, despesa, lucro = financeiro()
    problemas = []

    try:
        estoque_baixo = sql("SELECT item, quantidade, minimo FROM estoque WHERE quantidade <= minimo LIMIT 20", fetch=True)
    except Exception:
        estoque_baixo = []

    if estoque_baixo:
        problemas.append("Estoque baixo: " + "; ".join([f"{x[0]} ({x[1]}/{x[2]})" for x in estoque_baixo]))

    leads_quentes = sql("SELECT COUNT(*) FROM leads WHERE temperatura='quente'", fetch=True)[0][0]
    propostas_abertas = contar("propostas")
    tarefas_pendentes = sql("SELECT COUNT(*) FROM tarefas WHERE status='pendente'", fetch=True)[0][0]

    return f"""🧠 DIAGNÓSTICO MASTER V40

Receita: R$ {receita:.2f}
Despesa: R$ {despesa:.2f}
Lucro: R$ {lucro:.2f}

Leads quentes: {leads_quentes}
Propostas abertas: {propostas_abertas}
Tarefas pendentes: {tarefas_pendentes}

Alertas:
{chr(10).join(problemas) if problemas else "Nenhum alerta crítico encontrado."}

Próximas ações:
✅ fazer follow-up dos leads quentes
✅ revisar propostas abertas
✅ criar campanha de vendas
✅ verificar produção e estoque
"""


def plano_master_automatico():
    diag = diagnostico_sistema()
    acao = campanha("Street Graff personalizados")
    inserir("tarefas", "titulo, status, prioridade", ("Executar plano master V40", "pendente", "alta"))
    inserir("notificacoes", "mensagem, status", ("Plano Master V40 criado automaticamente.", "nova"))
    return f"""🚀 PLANO MASTER AUTOMÁTICO CRIADO

{diag}

Campanha preparada:

{acao}
"""


def followup_leads():
    leads = sql("SELECT id, nome, origem, temperatura FROM leads ORDER BY id DESC LIMIT 20", fetch=True)
    if not leads:
        return "Nenhum lead encontrado para follow-up."

    linhas = []
    for lead in leads:
        lead_id, nome, origem, temp = lead
        texto = f"Follow-up com {nome} ({temp}) vindo de {origem}"
        inserir("tarefas", "titulo, status, prioridade", (texto, "pendente", "alta" if temp == "quente" else "normal"))
        linhas.append(f"✅ {texto}")

    return "📞 FOLLOW-UP CRIADO\n\n" + "\n".join(linhas)


@app.route("/master", methods=["GET", "POST"])
def master_center():
    if not login_required():
        return redirect("/login")

    resposta = ""

    if request.method == "POST":
        acao = request.form.get("acao")
        if acao == "diagnostico":
            resposta = diagnostico_sistema()
        elif acao == "plano":
            resposta = plano_master_automatico()
        elif acao == "followup":
            resposta = followup_leads()
        elif acao == "automacoes":
            resposta = rodar_automacoes()
        else:
            resposta = conselho_multiagentes("Analise a operação inteira e gere o plano mais avançado possível.")

    return layout(f"""
    <h1>👑 V40 Quantum Enterprise Center</h1>

    <div class="card">
        <form method="POST">
            <select name="acao">
                <option value="diagnostico">Diagnóstico completo</option>
                <option value="plano">Criar plano master automático</option>
                <option value="followup">Criar follow-up de leads</option>
                <option value="automacoes">Rodar automações</option>
                <option value="multiagentes">Conselho multiagentes</option>
            </select>
            <button>Executar</button>
        </form>
    </div>

    <div class="card">
        <pre>{resposta}</pre>
    </div>
    """)


@app.route("/alertas")
def alertas_page():
    if not login_required():
        return redirect("/login")

    return layout(f"""
    <h1>🚨 Alertas Inteligentes</h1>
    <div class="card">
        <pre>{diagnostico_sistema()}</pre>
    </div>
    """)


@app.route("/followup")
def followup_page():
    if not login_required():
        return redirect("/login")

    resultado = followup_leads()

    return layout(f"""
    <h1>📞 Follow-up Automático</h1>
    <div class="card">
        <pre>{resultado}</pre>
    </div>
    """)


async def master_cmd(update, context):
    await send(update, plano_master_automatico())


async def diagnostico_cmd(update, context):
    await send(update, diagnostico_sistema())


async def followup_cmd(update, context):
    await send(update, followup_leads())


@app.route("/criar", methods=["GET", "POST"])
def criar():
    if not login_required():
        return redirect("/login")

    msg = ""

    if request.method == "POST":
        tipo = (request.form.get("tipo") or "").strip()
        nome = (request.form.get("nome") or "").strip()
        extra = (request.form.get("extra") or "").strip()
        valor = (request.form.get("valor") or "").strip()

        try:
            if tipo == "pedido":
                if not nome:
                    msg = "Digite o nome do pedido."
                else:
                    inserir("pedidos", "nome, cliente, valor", (nome, extra, numero_float(valor, 0)))
                    msg = "Pedido criado com sucesso."

            elif tipo == "lead":
                if not nome:
                    msg = "Digite o nome do lead."
                else:
                    inserir("leads", "nome, origem, temperatura", (nome, extra or "painel", "morno"))
                    msg = "Lead criado com sucesso."

            elif tipo == "cliente":
                if not nome:
                    msg = "Digite o nome do cliente."
                else:
                    inserir("clientes", "nome, contato, historico", (nome, extra, "Criado no painel"))
                    msg = "Cliente criado com sucesso."

            elif tipo == "produto":
                if not nome:
                    msg = "Digite o nome do produto."
                else:
                    inserir("produtos", "nome, preco, descricao", (nome, numero_float(valor, 0), extra))
                    msg = "Produto criado com sucesso."

            elif tipo == "estoque":
                if not nome:
                    msg = "Digite o item do estoque."
                else:
                    inserir("estoque", "item, quantidade, minimo", (nome, numero_int(valor, 0), 5))
                    msg = "Estoque criado com sucesso."

            elif tipo == "producao":
                if not nome:
                    msg = "Digite o item da produção."
                else:
                    inserir("producao", "item, cliente, status", (nome, extra, "aguardando"))
                    msg = "Produção criada com sucesso."

            elif tipo == "tarefa":
                if not nome:
                    msg = "Digite a tarefa."
                else:
                    inserir("tarefas", "titulo, status, prioridade", (nome, "pendente", extra or "normal"))
                    msg = "Tarefa criada com sucesso."

            elif tipo == "receita":
                inserir("financeiro", "tipo, valor, descricao", ("receita", numero_float(valor, 0), nome or "Receita pelo painel"))
                msg = "Receita criada com sucesso."

            elif tipo == "despesa":
                inserir("financeiro", "tipo, valor, descricao", ("despesa", numero_float(valor, 0), nome or "Despesa pelo painel"))
                msg = "Despesa criada com sucesso."

            elif tipo == "fornecedor":
                if not nome:
                    msg = "Digite o nome do fornecedor."
                else:
                    inserir("fornecedores", "nome, contato", (nome, extra))
                    msg = "Fornecedor criado com sucesso."

            elif tipo == "meta":
                if not nome:
                    msg = "Digite a meta."
                else:
                    inserir("metas", "nome, valor, status", (nome, valor or extra, "ativa"))
                    msg = "Meta criada com sucesso."

            elif tipo == "notificacao":
                if not nome:
                    msg = "Digite a notificação."
                else:
                    inserir("notificacoes", "mensagem, status", (nome, "nova"))
                    msg = "Notificação criada com sucesso."

            else:
                msg = "Escolha um tipo válido."

        except Exception as e:
            msg = f"Erro ao criar: {e}"

        try:
            log(f"Criar painel V40: {tipo} | {nome} | {msg}")
        except Exception:
            pass

    return layout(f"""
    <h1>➕ Criar Registro — V40 corrigido, blindado e empresarial</h1>

    <div class="card">
        <p>{msg}</p>

        <form method="POST">
            <label>Tipo</label>
            <select name="tipo">
                <option value="pedido">Pedido</option>
                <option value="lead">Lead</option>
                <option value="cliente">Cliente</option>
                <option value="produto">Produto</option>
                <option value="estoque">Estoque</option>
                <option value="producao">Produção</option>
                <option value="tarefa">Tarefa</option>
                <option value="receita">Receita</option>
                <option value="despesa">Despesa</option>
                <option value="fornecedor">Fornecedor</option>
                <option value="meta">Meta</option>
                <option value="notificacao">Notificação</option>
            </select>

            <label>Nome / descrição</label>
            <input name="nome" placeholder="Ex: camiseta personalizada">

            <label>Extra</label>
            <input name="extra" placeholder="Cliente, origem, contato, prioridade ou descrição">

            <label>Valor / quantidade</label>
            <input name="valor" placeholder="Ex: 100 ou 10">

            <button>Criar</button>
        </form>
    </div>
    """)

iniciar_banco()

threading.Thread(target=scheduler_loop, daemon=True).start()
threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
