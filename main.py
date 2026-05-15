import os, re, io, csv, json, shutil, sqlite3, threading, asyncio, urllib.request
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
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v34-omnisystem")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")
API_KEY = os.getenv("STREETCORE_API_KEY", "streetcore-api")
DB_PATH = os.getenv("DB_PATH", "streetcore_master.db")
UPLOAD_FOLDER = "uploads"
BACKUP_FOLDER = "backups"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
USE_OLLAMA = os.getenv("USE_OLLAMA", "false").lower() == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)
app.secret_key = SECRET_KEY
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(BACKUP_FOLDER, exist_ok=True)

telegram_app = None
telegram_loop = None

TABLES = {
    "usuarios": "id INTEGER PRIMARY KEY AUTOINCREMENT,usuario TEXT UNIQUE,senha TEXT,nivel TEXT DEFAULT 'admin',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "pedidos": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,cliente TEXT,status TEXT DEFAULT 'novo',valor REAL DEFAULT 0,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "leads": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,origem TEXT,status TEXT DEFAULT 'novo',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "clientes": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,contato TEXT,historico TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "financeiro": "id INTEGER PRIMARY KEY AUTOINCREMENT,tipo TEXT,valor REAL,descricao TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "produtos": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,preco REAL,descricao TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "estoque": "id INTEGER PRIMARY KEY AUTOINCREMENT,item TEXT,quantidade INTEGER,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "producao": "id INTEGER PRIMARY KEY AUTOINCREMENT,item TEXT,cliente TEXT,status TEXT DEFAULT 'aguardando',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "tarefas": "id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT,status TEXT DEFAULT 'pendente',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "campanhas": "id INTEGER PRIMARY KEY AUTOINCREMENT,tema TEXT,texto TEXT,status TEXT DEFAULT 'planejada',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "conteudos": "id INTEGER PRIMARY KEY AUTOINCREMENT,tema TEXT,tipo TEXT,texto TEXT,status TEXT DEFAULT 'rascunho',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "propostas": "id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,descricao TEXT,valor REAL,texto TEXT,status TEXT DEFAULT 'aberta',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "documentos": "id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT,tipo TEXT,texto TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "conhecimento": "id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT,texto TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "uploads": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,tipo TEXT,texto TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "atendimentos": "id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,pergunta TEXT,resposta TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "fornecedores": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,contato TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "notificacoes": "id INTEGER PRIMARY KEY AUTOINCREMENT,mensagem TEXT,status TEXT DEFAULT 'nova',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "metas": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,valor TEXT,status TEXT DEFAULT 'ativa',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "automacoes": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,acao TEXT,status TEXT DEFAULT 'ativa',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "logs": "id INTEGER PRIMARY KEY AUTOINCREMENT,mensagem TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
}

SAFE_TABLES = list(TABLES.keys())

MIGRATIONS = {
    "pedidos": {"cliente": "TEXT", "valor": "REAL DEFAULT 0"},
    "conteudos": {"status": "TEXT DEFAULT 'rascunho'"},
    "propostas": {"status": "TEXT DEFAULT 'aberta'"},
}

def db():
    return sqlite3.connect(DB_PATH)

def sql(q, p=(), fetch=False):
    con = db()
    cur = con.cursor()
    cur.execute(q, p)
    data = cur.fetchall() if fetch else None
    con.commit()
    con.close()
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
        sql("INSERT INTO usuarios (usuario,senha,nivel) VALUES (?,?,?)", (ADMIN_USER, ADMIN_PASS, "admin"))

    print("✅ StreetCore OS V34 OMNISYSTEM iniciado.")

def inserir(tabela, campos, valores):
    q = ",".join(["?"] * len(valores))
    sql(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)

def listar(tabela, limit=200):
    if tabela not in SAFE_TABLES:
        return []
    return sql(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT ?", (limit,), True)

def contar(tabela):
    return sql(f"SELECT COUNT(*) FROM {tabela}", fetch=True)[0][0]

def log(msg):
    inserir("logs", "mensagem", (str(msg),))

def financeiro():
    receita = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'", fetch=True)[0][0] or 0
    despesa = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'", fetch=True)[0][0] or 0
    return receita, despesa, receita - despesa

def login_required():
    return session.get("ok") is True

def is_admin():
    return session.get("nivel") == "admin"

def limpar_nome(nome):
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", nome or "arquivo")

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
    if not USE_OLLAMA:
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
        with urllib.request.urlopen(req, timeout=25) as res:
            data = json.loads(res.read().decode("utf-8"))
            return data.get("response", "")
    except Exception as e:
        return f"Ollama indisponível: {e}"

def post(tema):
    ia = ollama(f"Crie um post de Instagram para Street Graff sobre {tema}.")
    if ia:
        return ia
    return f"""🔥 POST PRONTO - {tema.upper()}

Sua marca precisa aparecer com presença.
A Street Graff cria camisetas, adesivos, canecas, panfletos e brindes personalizados.

📲 Chama no direct e peça seu orçamento.
Pagamento via PIX.

#streetgraff #personalizados #camisetaspersonalizadas #adesivospersonalizados #canecaspersonalizadas"""

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
    return f"{post(tema)}\n\n---\n\n{story(tema)}\n\n---\n\n{reels(tema)}\n\n✅ Ação: postar hoje às 18h, salvar leads e chamar clientes no direct."

def valor_orcamento(desc):
    t = desc.lower()
    base = 35
    if "camiseta" in t: base = 45
    if "caneca" in t: base = 30
    if "adesivo" in t: base = 8
    if "panfleto" in t: base = 80
    if "brinde" in t: base = 20
    qtd = next((int(x) for x in t.replace(",", " ").split() if x.isdigit()), 1)
    return base * qtd + (20 if "arte" in t or "design" in t else 0) + (30 if "urgente" in t else 0)

def gerar_proposta(cliente, desc):
    v = valor_orcamento(desc)
    return f"""PROPOSTA COMERCIAL STREET GRAFF

Cliente: {cliente}
Solicitação: {desc}

Incluso:
- atendimento personalizado;
- produção sob medida;
- revisão básica;
- personalização conforme pedido.

Valor estimado: R$ {v:.2f}
Prazo: 5 dias úteis + transporte.
Pagamento: somente via PIX.

Para confirmar, envie arte/referência e quantidade final."""

def contrato(cliente, servico, valor):
    return f"""CONTRATO SIMPLES

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
    if "prazo" in p: return "Prazo padrão: 5 dias úteis de produção + transporte."
    if "pagamento" in p or "pix" in p: return "Pagamento somente via PIX."
    if "orçamento" in p or "orcamento" in p: return "Informe produto, quantidade, tamanho e se já possui arte."
    if "camiseta" in p: return "Fazemos camisetas personalizadas. Valor depende da quantidade e arte."
    if "caneca" in p: return "Fazemos canecas personalizadas sob encomenda."
    if "adesivo" in p: return "Fazemos adesivos personalizados em vários tamanhos."
    return "Fazemos camisetas, adesivos, canecas, panfletos e brindes personalizados."

def plano():
    return """✅ PLANO OMNISYSTEM DO DIA

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
13. Fazer backup e fechar vendas."""

def relatorio():
    r, d, l = financeiro()
    linhas = [f"{t}: {contar(t)}" for t in [
        "pedidos","leads","clientes","propostas","produtos","estoque",
        "producao","tarefas","campanhas","conteudos","documentos",
        "conhecimento","uploads","atendimentos","automacoes"
    ]]
    return "📊 RELATÓRIO OMNISYSTEM V34\n\n" + "\n".join(linhas) + f"""

Receita: R$ {r:.2f}
Despesa: R$ {d:.2f}
Lucro: R$ {l:.2f}

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
        "leads": "nome LIKE ? OR origem LIKE ?",
        "clientes": "nome LIKE ? OR contato LIKE ? OR historico LIKE ?",
        "propostas": "cliente LIKE ? OR descricao LIKE ? OR texto LIKE ?",
        "documentos": "titulo LIKE ? OR texto LIKE ?",
        "conhecimento": "titulo LIKE ? OR texto LIKE ?",
        "uploads": "nome LIKE ? OR texto LIKE ?"
    }
    for t, where in pesquisas.items():
        params = tuple([like] * where.count("?"))
        dados = sql(f"SELECT * FROM {t} WHERE {where} LIMIT 20", params, True)
        if dados:
            blocos.append(f"{t.upper()}:\n" + "\n".join(map(str, dados)))
    return "\n\n".join(blocos) if blocos else "Nenhum resultado encontrado."

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
    hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
    inserir("tarefas", "titulo,status", (f"Revisar leads - {hoje}", "pendente"))
    inserir("notificacoes", "mensagem,status", (f"Rodar campanha diária - {hoje}", "nova"))
    inserir("conteudos", "tema,tipo,texto,status", ("Street Graff", "post_auto", post("Street Graff"), "rascunho"))
    return "Automações executadas: tarefa, notificação e post em rascunho criados."

def layout(c):
    menu = [
        ("Dashboard", "/"), ("Criar", "/criar"), ("OmniCore", "/omnicore"),
        ("Conteúdo IA", "/conteudo"), ("Aprovação Posts", "/aprovacoes"),
        ("Propostas", "/propostas"), ("PDF Proposta", "/pdf-proposta"),
        ("Atendimento", "/atendimento"), ("Upload", "/upload"),
        ("Busca", "/buscar"), ("Financeiro", "/financeiro"),
        ("Relatório", "/relatorio"), ("Automações", "/automacoes"),
        ("Usuários", "/usuarios"), ("Modo Cliente", "/cliente"),
        ("API Info", "/api/info"), ("Backup", "/backup"), ("Restaurar", "/restore")
    ]
    tables = ["pedidos","leads","clientes","produtos","estoque","producao","tarefas","campanhas","conteudos","documentos","conhecimento","uploads","atendimentos","fornecedores","notificacoes","metas","automacoes","logs"]
    links = "".join([f"<a href='{u}'>{n}</a>" for n,u in menu])
    links += "<hr>" + "".join([f"<a href='/table/{t}'>{t.title()}</a>" for t in tables])
    return f"""
<html><head><title>StreetCore V34 OMNISYSTEM</title>
<style>
body{{margin:0;background:#050505;color:#fff;font-family:Arial}}
.sidebar{{position:fixed;top:0;left:0;bottom:0;width:305px;background:#0b0b0b;border-right:1px solid #222;padding:24px;overflow:auto}}
.sidebar h2{{color:#00ff88}} .sidebar a{{display:block;color:white;text-decoration:none;margin:11px 0}} .sidebar a:hover{{color:#00ff88}}
.main{{margin-left:355px;padding:30px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:18px}}
.card{{background:#111;border:1px solid #333;border-radius:18px;padding:22px;margin-bottom:18px}} .big{{color:#00ff88;font-size:34px;font-weight:bold}}
input,select,textarea{{padding:12px;border-radius:10px;border:0;margin:6px 0;width:100%;background:#1c1c1c;color:white}} textarea{{min-height:170px}}
button{{padding:12px 18px;border:0;border-radius:10px;background:#00ff88;font-weight:bold;cursor:pointer}}
table{{width:100%;border-collapse:collapse;background:#111}} th,td{{padding:12px;border-bottom:1px solid #333;vertical-align:top}} a{{color:#00ff88}} pre{{white-space:pre-wrap}}
.bar{{background:#00ff88;height:18px;border-radius:10px}}
@media print{{.sidebar{{display:none}}.main{{margin-left:0}}body{{background:white;color:black}}.card{{border:1px solid #999;background:white;color:black}}}}
</style></head>
<body><div class="sidebar"><h2>🔥 StreetCore V34</h2>{links}<a href='/logout'>Sair</a></div><div class="main">{c}</div></body></html>"""

@app.route("/login", methods=["GET","POST"])
def login():
    erro = ""
    if request.method == "POST":
        u = request.form.get("usuario")
        s = request.form.get("senha")
        user = sql("SELECT usuario,nivel FROM usuarios WHERE usuario=? AND senha=?", (u, s), True)
        if user:
            session["ok"] = True
            session["usuario"] = user[0][0]
            session["nivel"] = user[0][1]
            return redirect("/")
        erro = "<p style='color:red'>Login incorreto</p>"
    return f"""<body style="background:#050505;color:white;font-family:Arial;display:flex;align-items:center;justify-content:center;height:100vh">
<div style="background:#111;padding:40px;border-radius:20px;width:330px"><h1>🔥 StreetCore V34</h1>{erro}
<form method="POST"><input name="usuario" placeholder="Usuário" style="width:100%;padding:14px;margin-bottom:12px">
<input name="senha" type="password" placeholder="Senha" style="width:100%;padding:14px;margin-bottom:12px">
<button style="width:100%;padding:14px;background:#00ff88;border:0;border-radius:10px;font-weight:bold">Entrar</button></form>
<p>admin / streetcore</p></div></body>"""

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
def home():
    if not login_required(): return redirect("/login")
    r,d,l = financeiro()
    cards = "".join([f"<div class='card'><h2>{t.title()}</h2><div class='big'>{contar(t)}</div></div>" for t in ["pedidos","leads","clientes","propostas","conteudos","uploads","produtos","estoque","producao","tarefas","atendimentos"]])
    cards += f"<div class='card'><h2>Receita</h2><div class='big'>R$ {r:.2f}</div></div><div class='card'><h2>Lucro</h2><div class='big'>R$ {l:.2f}</div></div>"
    grafico = f"""
    <div class='card'><h2>Gráfico rápido</h2>
    <p>Receita</p><div class='bar' style='width:{min(r/10,100)}%'></div>
    <p>Despesa</p><div class='bar' style='width:{min(d/10,100)}%'></div>
    <p>Lucro</p><div class='bar' style='width:{min(max(l,0)/10,100)}%'></div>
    </div>
    """
    return layout(f"<h1>🔥 STREETCORE OS V34 OMNISYSTEM FREE</h1><div class='grid'>{cards}</div>{grafico}<div class='card'><pre>{plano()}</pre></div>")

@app.route("/health")
def health():
    return jsonify({"status":"online","version":"V34 OMNISYSTEM FREE","webhook":bool(WEBHOOK_URL),"ollama":USE_OLLAMA})

@app.route("/omnicore", methods=["GET","POST"])
def omnicore():
    if not login_required(): return redirect("/login")
    resp = ""
    if request.method == "POST":
        comando = request.form.get("comando","")
        ia = ollama(f"Analise esta operação da Street Graff: {comando}\n\n{relatorio()}") if USE_OLLAMA else ""
        resp = ia or f"🧠 OMNICORE ANALYSIS\n\nComando: {comando}\n\n{relatorio()}\n\n{plano()}"
    return layout(f"<h1>🧠 OmniCore</h1><div class='card'><form method='POST'><input name='comando' placeholder='O que devo analisar?'><button>Analisar</button></form></div><div class='card'><pre>{resp}</pre></div>")

@app.route("/criar", methods=["GET","POST"])
def criar():
    if not login_required(): return redirect("/login")
    msg = ""
    if request.method == "POST":
        tipo, nome, extra, valor = request.form.get("tipo"), request.form.get("nome"), request.form.get("extra"), request.form.get("valor")
        try:
            if tipo == "pedido": inserir("pedidos","nome,cliente,valor",(nome,extra,float(valor or 0)))
            elif tipo == "lead": inserir("leads","nome,origem",(nome,extra or "painel"))
            elif tipo == "cliente": inserir("clientes","nome,contato,historico",(nome,extra,"Criado no painel"))
            elif tipo == "produto": inserir("produtos","nome,preco,descricao",(nome,float(valor or 0),extra))
            elif tipo == "estoque": inserir("estoque","item,quantidade",(nome,int(valor or 0)))
            elif tipo == "producao": inserir("producao","item,cliente",(nome,extra))
            elif tipo == "tarefa": inserir("tarefas","titulo",(nome,))
            elif tipo == "receita": inserir("financeiro","tipo,valor,descricao",("receita",float(valor or 0),nome))
            elif tipo == "despesa": inserir("financeiro","tipo,valor,descricao",("despesa",float(valor or 0),nome))
            msg = f"{tipo} criado com sucesso."
        except Exception as e:
            msg = f"Erro: {e}"
        log(f"Criar: {tipo} {nome}")
    return layout(f"""<h1>➕ Criar Registro</h1><div class='card'><p>{msg}</p><form method='POST'>
<select name='tipo'><option>pedido</option><option>lead</option><option>cliente</option><option>produto</option><option>estoque</option><option>producao</option><option>tarefa</option><option>receita</option><option>despesa</option></select>
<input name='nome' placeholder='Nome/descrição'><input name='extra' placeholder='Cliente/origem/contato/descrição'><input name='valor' placeholder='Valor ou quantidade'><button>Criar</button></form></div>""")

@app.route("/conteudo", methods=["GET","POST"])
def conteudo():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        tema, tipo = request.form.get("tema","Street Graff"), request.form.get("tipo")
        res = campanha(tema) if tipo == "campanha" else reels(tema) if tipo == "reels" else story(tema) if tipo == "story" else post(tema)
        inserir("conteudos","tema,tipo,texto,status",(tema,tipo,res,"rascunho"))
    return layout(f"<h1>🤖 Conteúdo IA</h1><div class='card'><form method='POST'><input name='tema' placeholder='Tema'><select name='tipo'><option>post</option><option>story</option><option>reels</option><option>campanha</option></select><button>Gerar</button></form></div><div class='card'><textarea>{res}</textarea></div>")

@app.route("/aprovacoes")
def aprovacoes():
    if not login_required(): return redirect("/login")
    dados = sql("SELECT id,tema,tipo,texto,status,criado_em FROM conteudos ORDER BY id DESC LIMIT 100", fetch=True)
    linhas = "".join([f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td><pre>{d[3]}</pre></td><td>{d[4]}</td><td><a href='/aprovar/{d[0]}'>Aprovar</a></td></tr>" for d in dados])
    return layout(f"<h1>✅ Aprovação de Posts</h1><table>{linhas}</table>")

@app.route("/aprovar/<int:item_id>")
def aprovar(item_id):
    if not login_required(): return redirect("/login")
    sql("UPDATE conteudos SET status='aprovado' WHERE id=?", (item_id,))
    return redirect("/aprovacoes")

@app.route("/propostas", methods=["GET","POST"])
def propostas():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente, desc = request.form.get("cliente"), request.form.get("descricao")
        res = gerar_proposta(cliente, desc)
        inserir("propostas","cliente,descricao,valor,texto",(cliente,desc,valor_orcamento(desc),res))
    return layout(f"<h1>🧾 Propostas</h1><div class='card'><form method='POST'><input name='cliente' placeholder='Cliente'><textarea name='descricao'></textarea><button>Gerar</button></form></div><div class='card'><pre>{res}</pre></div>")

@app.route("/pdf-proposta", methods=["GET","POST"])
def pdf_proposta():
    if not login_required(): return redirect("/login")
    if request.method == "POST":
        cliente = request.form.get("cliente")
        desc = request.form.get("descricao")
        buffer, tipo = gerar_pdf_proposta(cliente, desc)
        if tipo == "pdf":
            return send_file(buffer, as_attachment=True, download_name="proposta_streetgraff.pdf", mimetype="application/pdf")
        return send_file(buffer, as_attachment=True, download_name="proposta_streetgraff.txt", mimetype="text/plain")
    return layout("<h1>📄 Gerar PDF de Proposta</h1><div class='card'><form method='POST'><input name='cliente' placeholder='Cliente'><textarea name='descricao' placeholder='Descrição'></textarea><button>Gerar PDF</button></form></div>")

@app.route("/atendimento", methods=["GET","POST"])
def atendimento():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente, pergunta = request.form.get("cliente","cliente"), request.form.get("pergunta","")
        res = faq(pergunta)
        inserir("atendimentos","cliente,pergunta,resposta",(cliente,pergunta,res))
    return layout(f"<h1>💬 Atendimento IA</h1><div class='card'><form method='POST'><input name='cliente'><textarea name='pergunta'></textarea><button>Responder</button></form></div><div class='card'><pre>{res}</pre></div>")

@app.route("/upload", methods=["GET","POST"])
def upload():
    if not login_required(): return redirect("/login")
    msg = ""
    if request.method == "POST":
        file = request.files.get("arquivo")
        if file:
            nome = limpar_nome(file.filename)
            path = os.path.join(UPLOAD_FOLDER, nome)
            file.save(path)
            texto = extrair_arquivo(path)
            inserir("uploads","nome,tipo,texto",(nome, nome.split(".")[-1].lower(), texto[:12000]))
            inserir("conhecimento","titulo,texto",(f"Upload: {nome}", texto[:12000]))
            msg = f"Arquivo salvo e lido: {nome}"
    return layout(f"<h1>📎 Upload TXT/PDF</h1><div class='card'><p>{msg}</p><form method='POST' enctype='multipart/form-data'><input type='file' name='arquivo'><button>Enviar</button></form></div><pre>{listar('uploads', 20)}</pre>")

@app.route("/buscar", methods=["GET","POST"])
def buscar_web():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        res = buscar(request.form.get("termo",""))
    return layout(f"<h1>🔎 Busca Inteligente</h1><div class='card'><form method='POST'><input name='termo'><button>Buscar</button></form></div><div class='card'><pre>{res}</pre></div>")

@app.route("/automacoes", methods=["GET","POST"])
def automacoes():
    if not login_required(): return redirect("/login")
    msg = ""
    if request.method == "POST":
        msg = rodar_automacoes()
    return layout(f"<h1>⚙️ Automações</h1><div class='card'><form method='POST'><button>Rodar automações agora</button></form></div><div class='card'><pre>{msg}</pre></div><pre>{listar('automacoes')}</pre>")

@app.route("/usuarios", methods=["GET","POST"])
def usuarios():
    if not login_required(): return redirect("/login")
    if not is_admin(): return "Apenas admin."
    msg = ""
    if request.method == "POST":
        try:
            inserir("usuarios","usuario,senha,nivel",(request.form.get("usuario"), request.form.get("senha"), request.form.get("nivel")))
            msg = "Usuário criado."
        except Exception as e:
            msg = f"Erro: {e}"
    return layout(f"<h1>👤 Usuários</h1><div class='card'><p>{msg}</p><form method='POST'><input name='usuario' placeholder='Usuário'><input name='senha' placeholder='Senha'><select name='nivel'><option>admin</option><option>operador</option></select><button>Criar</button></form></div><pre>{listar('usuarios')}</pre>")

@app.route("/cliente")
def cliente_publico():
    return """
<html><body style="background:#050505;color:white;font-family:Arial;padding:30px">
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
</body></html>"""

@app.route("/cliente-orcamento", methods=["POST"])
def cliente_orcamento():
    cliente = request.form.get("cliente")
    desc = request.form.get("descricao")
    txt = gerar_proposta(cliente, desc)
    inserir("leads","nome,origem",(cliente,"modo_cliente"))
    inserir("propostas","cliente,descricao,valor,texto",(cliente,desc,valor_orcamento(desc),txt))
    return f"<pre>{txt}</pre><a href='/cliente'>Voltar</a>"

@app.route("/financeiro")
def financeiro_web():
    if not login_required(): return redirect("/login")
    r,d,l=financeiro()
    return layout(f"<h1>💵 Financeiro</h1><div class='grid'><div class='card'><h2>Receita</h2><div class='big'>R$ {r:.2f}</div></div><div class='card'><h2>Despesa</h2><div class='big'>R$ {d:.2f}</div></div><div class='card'><h2>Lucro</h2><div class='big'>R$ {l:.2f}</div></div></div>")

@app.route("/relatorio")
def relatorio_web():
    if not login_required(): return redirect("/login")
    return layout(f"<h1>📊 Relatório Omnisystem</h1><div class='card'><pre>{relatorio()}</pre></div>")

@app.route("/table/<tabela>")
def table(tabela):
    if not login_required(): return redirect("/login")
    if tabela not in SAFE_TABLES: return "Tabela não permitida"
    dados = listar(tabela, 1000)
    linhas = "".join(["<tr>" + "".join([f"<td>{x}</td>" for x in d]) + f"<td><a href='/delete/{tabela}/{d[0]}'>Excluir</a></td></tr>" for d in dados])
    return layout(f"<h1>{tabela.title()}</h1><a href='/export/{tabela}'>Exportar CSV</a><table>{linhas}</table>")

@app.route("/delete/<tabela>/<int:item_id>")
def delete(tabela, item_id):
    if not login_required(): return redirect("/login")
    if not is_admin(): return "Apenas admin."
    if tabela in SAFE_TABLES:
        sql(f"DELETE FROM {tabela} WHERE id=?", (item_id,))
    return redirect(f"/table/{tabela}")

@app.route("/export/<tabela>")
def export(tabela):
    if not login_required(): return redirect("/login")
    if tabela not in SAFE_TABLES: return "Tabela não permitida"
    rows = listar(tabela, 10000)
    output = io.StringIO()
    writer = csv.writer(output)
    for row in rows:
        writer.writerow(row)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":f"attachment;filename={tabela}.csv"})

@app.route("/backup")
def backup():
    if not login_required(): return redirect("/login")
    nome = f"backup_v34_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    destino = os.path.join(BACKUP_FOLDER, nome)
    shutil.copy(DB_PATH, destino)
    with open(destino, "rb") as f:
        data = f.read()
    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition":f"attachment;filename={nome}"})

@app.route("/restore", methods=["GET","POST"])
def restore():
    if not login_required(): return redirect("/login")
    if not is_admin(): return "Apenas admin."
    msg = ""
    if request.method == "POST":
        file = request.files.get("backup")
        if file and file.filename.endswith(".db"):
            safety = os.path.join(BACKUP_FOLDER, f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
            shutil.copy(DB_PATH, safety)
            file.save(DB_PATH)
            iniciar_banco()
            msg = "Backup restaurado. Um backup de segurança foi criado antes."
    return layout(f"<h1>♻️ Restaurar Backup</h1><div class='card'><p>{msg}</p><form method='POST' enctype='multipart/form-data'><input type='file' name='backup'><button>Restaurar</button></form></div>")

@app.route("/api/info")
def api_info():
    return jsonify({"version":"V34 OMNISYSTEM FREE","api_key_header":"X-API-Key","tables":SAFE_TABLES})

def api_auth():
    return request.headers.get("X-API-Key") == API_KEY

@app.route("/api/relatorio")
def api_relatorio():
    if not api_auth(): return jsonify({"erro":"API key inválida"}), 403
    return jsonify({"relatorio":relatorio()})

@app.route("/api/table/<tabela>")
def api_table(tabela):
    if not api_auth(): return jsonify({"erro":"API key inválida"}), 403
    if tabela not in SAFE_TABLES: return jsonify({"erro":"tabela inválida"}), 400
    return jsonify({"dados":listar(tabela)})

@app.route("/api/create/<tabela>", methods=["POST"])
def api_create(tabela):
    if not api_auth(): return jsonify({"erro":"API key inválida"}), 403
    data = request.json or {}
    try:
        if tabela == "pedidos":
            inserir("pedidos","nome,cliente,valor",(data.get("nome"), data.get("cliente"), float(data.get("valor",0))))
        elif tabela == "leads":
            inserir("leads","nome,origem",(data.get("nome"), data.get("origem","api")))
        else:
            return jsonify({"erro":"criação permitida apenas para pedidos/leads"}), 400
        return jsonify({"status":"criado"})
    except Exception as e:
        return jsonify({"erro":str(e)}), 500

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    if not telegram_app or not telegram_loop:
        return "bot indisponível", 503
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    asyncio.run_coroutine_threadsafe(telegram_app.process_update(update), telegram_loop)
    return "ok"

async def send(update, txt):
    await update.message.reply_text(str(txt)[:3900])

async def start_cmd(update, context):
    await send(update, "🔥 STREETCORE V34 OMNISYSTEM\n/omni vender mais\n/relatorio\n/pedido camiseta joao\n/lead maria instagram\n/proposta joao 10 camisetas\n/receita 100\n/despesa 50\n/financeiro\n/post camisetas\n/campanha street graff\n/buscar joao")

async def omni_cmd(update, context): await send(update, f"🧠 OMNISYSTEM\n\n{relatorio()}\n\n{plano()}")
async def relatorio_cmd(update, context): await send(update, relatorio())
async def post_cmd(update, context): await send(update, post(" ".join(context.args) or "Street Graff"))
async def campanha_cmd(update, context): await send(update, campanha(" ".join(context.args) or "Street Graff"))
async def buscar_cmd(update, context): await send(update, buscar(" ".join(context.args)))

async def pedido_cmd(update, context):
    inserir("pedidos","nome,cliente",(context.args[0] if context.args else "", " ".join(context.args[1:])))
    await send(update, "📦 Pedido criado.")

async def lead_cmd(update, context):
    inserir("leads","nome,origem",(context.args[0] if context.args else "", " ".join(context.args[1:]) or "telegram"))
    await send(update, "🎯 Lead criado.")

async def proposta_cmd(update, context):
    cliente = context.args[0] if context.args else "cliente"
    desc = " ".join(context.args[1:]) or "pedido"
    txt = gerar_proposta(cliente, desc)
    inserir("propostas","cliente,descricao,valor,texto",(cliente,desc,valor_orcamento(desc),txt))
    await send(update, txt)

async def receita_cmd(update, context):
    v = float(context.args[0].replace(",", "."))
    inserir("financeiro","tipo,valor,descricao",("receita",v,"telegram"))
    await send(update, f"💰 Receita R$ {v:.2f}")

async def despesa_cmd(update, context):
    v = float(context.args[0].replace(",", "."))
    inserir("financeiro","tipo,valor,descricao",("despesa",v,"telegram"))
    await send(update, f"💸 Despesa R$ {v:.2f}")

async def financeiro_cmd(update, context):
    r,d,l = financeiro()
    await send(update, f"Receita: R$ {r:.2f}\nDespesa: R$ {d:.2f}\nLucro: R$ {l:.2f}")

async def receber_documento(update, context):
    doc = update.message.document
    nome = limpar_nome(doc.file_name)
    path = os.path.join(UPLOAD_FOLDER, nome)
    arquivo = await context.bot.get_file(doc.file_id)
    await arquivo.download_to_drive(path)
    texto = extrair_arquivo(path)
    inserir("uploads","nome,tipo,texto",(nome, nome.split(".")[-1].lower(), texto[:12000]))
    inserir("conhecimento","titulo,texto",(f"Telegram upload: {nome}", texto[:12000]))
    await send(update, f"✅ Arquivo salvo e lido: {nome}\n\nPrévia:\n{texto[:1000]}")

async def responder(update, context):
    log(update.message.text)
    await send(update, faq(update.message.text))

async def telegram_main():
    global telegram_app, telegram_loop
    telegram_loop = asyncio.get_event_loop()
    telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

    commands = {
        "start": start_cmd, "omni": omni_cmd, "relatorio": relatorio_cmd,
        "pedido": pedido_cmd, "lead": lead_cmd, "proposta": proposta_cmd,
        "receita": receita_cmd, "despesa": despesa_cmd, "financeiro": financeiro_cmd,
        "post": post_cmd, "campanha": campanha_cmd, "buscar": buscar_cmd
    }

    for n,f in commands.items():
        telegram_app.add_handler(CommandHandler(n, f))

    telegram_app.add_handler(MessageHandler(filters.Document.ALL, receber_documento))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))

    print("🔥 Telegram iniciando V34...")
    await telegram_app.initialize()
    await telegram_app.start()

    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(f"{WEBHOOK_URL.rstrip('/')}/telegram-webhook")
        print("✅ Telegram WEBHOOK ativo V34")
    else:
        await telegram_app.updater.start_polling()
        print("✅ Telegram POLLING ativo V34")

    await asyncio.Event().wait()

def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())

iniciar_banco()
threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
