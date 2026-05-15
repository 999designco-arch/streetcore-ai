import os, sqlite3, threading, asyncio, json
from datetime import datetime
from flask import Flask, jsonify, request, redirect, session, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v31")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")
API_KEY = os.getenv("STREETCORE_API_KEY", "streetcore-api")
DB_PATH = os.getenv("DB_PATH", "streetcore_v30.db")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)
app.secret_key = SECRET_KEY


def db():
    return sqlite3.connect(DB_PATH)


def iniciar_banco():
    conn = db()
    cur = conn.cursor()

    tables = [
        """CREATE TABLE IF NOT EXISTS pedidos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, cliente TEXT, status TEXT DEFAULT 'novo', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, origem TEXT, status TEXT DEFAULT 'novo', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, contato TEXT, historico TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS financeiro (id INTEGER PRIMARY KEY AUTOINCREMENT, tipo TEXT, valor REAL, descricao TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY AUTOINCREMENT, mensagem TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS conteudos (id INTEGER PRIMARY KEY AUTOINCREMENT, tema TEXT, tipo TEXT, texto TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS campanhas (id INTEGER PRIMARY KEY AUTOINCREMENT, tema TEXT, texto TEXT, status TEXT DEFAULT 'planejada', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS tarefas (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, status TEXT DEFAULT 'pendente', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS producao (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, cliente TEXT, status TEXT DEFAULT 'aguardando', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, quantidade INTEGER, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS fornecedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, contato TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS notificacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, mensagem TEXT, status TEXT DEFAULT 'nova', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS documentos (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, tipo TEXT, texto TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS conhecimento (id INTEGER PRIMARY KEY AUTOINCREMENT, titulo TEXT, texto TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS propostas (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, descricao TEXT, valor REAL, texto TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS atendimentos (id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT, pergunta TEXT, resposta TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS produtos (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, preco REAL, descricao TEXT, criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, valor TEXT, status TEXT DEFAULT 'ativa', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS automacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, acao TEXT, status TEXT DEFAULT 'ativa', criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    ]

    for t in tables:
        cur.execute(t)

    conn.commit()
    conn.close()
    print("✅ Banco V31 OMEGA SUPREME iniciado.")


def sql(query, params=(), fetch=False):
    conn = db()
    cur = conn.cursor()
    cur.execute(query, params)
    data = cur.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data


def insert(tabela, campos, valores):
    q = ",".join(["?"] * len(valores))
    sql(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)


def listar(tabela):
    return sql(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT 100", fetch=True)


def contar(tabela):
    return sql(f"SELECT COUNT(*) FROM {tabela}", fetch=True)[0][0]


def log(msg):
    insert("logs", "mensagem", (msg,))


def financeiro():
    receita = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'", fetch=True)[0][0] or 0
    despesa = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'", fetch=True)[0][0] or 0
    return receita, despesa, receita - despesa


def login_required():
    return session.get("logado") is True


def gerar_post(tema):
    return f"""🔥 POST - {tema.upper()}

Sua marca precisa aparecer com presença.
A Street Graff cria camisetas, adesivos, canecas, panfletos e brindes personalizados.

📲 Chama no direct e peça seu orçamento.

#streetgraff #personalizados #camisetaspersonalizadas #adesivospersonalizados"""


def gerar_story(tema):
    return f"""📲 STORY - {tema.upper()}

Tela 1: Sua marca ainda está invisível?
Tela 2: Personalizados com estilo urbano.
Tela 3: Camisetas, adesivos, canecas, panfletos e brindes.
Tela 4: Chama no direct e peça seu orçamento."""


def gerar_reels(tema):
    return f"""🎬 REELS - {tema.upper()}

Gancho: Sua marca precisa aparecer mais?
Cena 1: Produto personalizado.
Cena 2: Bastidor da produção.
Cena 3: Resultado final.
CTA: Chama no direct."""


def gerar_campanha(tema):
    return f"{gerar_post(tema)}\n\n---\n\n{gerar_story(tema)}\n\n---\n\n{gerar_reels(tema)}"


def calcular_orcamento(desc):
    t = desc.lower()
    base = 35
    if "camiseta" in t: base = 45
    if "caneca" in t: base = 30
    if "adesivo" in t: base = 8
    if "panfleto" in t: base = 80
    if "brinde" in t: base = 20
    qtd = 1
    for p in t.replace(",", " ").split():
        if p.isdigit():
            qtd = int(p)
            break
    return base * qtd + (20 if "arte" in t else 0) + (30 if "urgente" in t else 0)


def proposta(cliente, desc):
    valor = calcular_orcamento(desc)
    return f"""🧾 PROPOSTA STREET GRAFF

Cliente: {cliente}
Pedido: {desc}

Valor estimado: R$ {valor:.2f}
Prazo: 5 dias úteis + transporte.
Pagamento: somente PIX.

Para confirmar, envie arte/referência e quantidade final."""


def faq(pergunta):
    p = pergunta.lower()
    if "prazo" in p: return "Prazo padrão: 5 dias úteis + transporte."
    if "pix" in p or "pagamento" in p: return "Pagamento somente via PIX."
    if "orçamento" in p or "orcamento" in p: return "Informe produto, quantidade, tamanho e se já possui arte."
    return "Fazemos camisetas, adesivos, canecas, panfletos e brindes personalizados."


def relatorio():
    r, d, l = financeiro()
    return f"""📊 RELATÓRIO V31 OMEGA SUPREME

Pedidos: {contar('pedidos')}
Leads: {contar('leads')}
Clientes: {contar('clientes')}
Propostas: {contar('propostas')}
Campanhas: {contar('campanhas')}
Produtos: {contar('produtos')}
Tarefas: {contar('tarefas')}
Produção: {contar('producao')}
Estoque: {contar('estoque')}

Receita: R$ {r:.2f}
Despesa: R$ {d:.2f}
Lucro: R$ {l:.2f}

Decisão:
✅ captar leads
✅ gerar campanha
✅ criar propostas
✅ atualizar produção
✅ fechar vendas"""


def plano():
    return """✅ PLANO SUPREMO DO DIA

1. Ver leads novos
2. Responder clientes
3. Criar campanha
4. Fazer post + story + reels
5. Atualizar pedidos
6. Conferir produção
7. Registrar financeiro
8. Criar propostas
9. Fazer backup
10. Fechar venda"""


def layout(c):
    return f"""
<html>
<head>
<title>StreetCore V31</title>
<style>
body{{margin:0;background:#050505;color:white;font-family:Arial}}
.sidebar{{position:fixed;top:0;left:0;bottom:0;width:285px;background:#0b0b0b;border-right:1px solid #222;padding:24px;overflow:auto}}
.sidebar h2{{color:#00ff88}}
.sidebar a{{display:block;color:white;text-decoration:none;margin:12px 0}}
.sidebar a:hover{{color:#00ff88}}
.main{{margin-left:335px;padding:30px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}}
.card{{background:#111;border:1px solid #333;border-radius:18px;padding:22px;margin-bottom:18px}}
.big{{color:#00ff88;font-size:36px;font-weight:bold}}
input,select,textarea{{padding:12px;border-radius:10px;border:0;margin:6px 0;width:100%;background:#1c1c1c;color:white}}
textarea{{min-height:170px}}
button{{padding:12px 18px;border:0;border-radius:10px;background:#00ff88;font-weight:bold;cursor:pointer}}
table{{width:100%;border-collapse:collapse;background:#111;border-radius:14px;overflow:hidden}}
th,td{{padding:12px;border-bottom:1px solid #333;text-align:left;vertical-align:top}}
a{{color:#00ff88}} pre{{white-space:pre-wrap}}
</style>
</head>
<body>
<div class="sidebar">
<h2>🔥 StreetCore V31</h2>
<a href="/">Dashboard</a>
<a href="/omega">Omega Center</a>
<a href="/criar">Criar</a>
<a href="/conteudo">Conteúdo IA</a>
<a href="/propostas">Propostas</a>
<a href="/atendimento">Atendimento</a>
<a href="/table/pedidos">Pedidos</a>
<a href="/table/leads">Leads</a>
<a href="/table/clientes">Clientes</a>
<a href="/table/produtos">Produtos</a>
<a href="/table/tarefas">Tarefas</a>
<a href="/table/producao">Produção</a>
<a href="/table/estoque">Estoque</a>
<a href="/financeiro-web">Financeiro</a>
<a href="/relatorio-web">Relatório</a>
<a href="/api/info">API Info</a>
<a href="/backup">Backup</a>
<a href="/logout">Sair</a>
</div>
<div class="main">{c}</div>
</body>
</html>
"""


@app.route("/")
def home():
    if not login_required(): return redirect("/login")
    r, d, l = financeiro()
    cards = ""
    for t in ["pedidos","leads","clientes","propostas","campanhas","produtos","tarefas","producao","estoque"]:
        cards += f"<div class='card'><h2>{t.title()}</h2><div class='big'>{contar(t)}</div></div>"
    cards += f"<div class='card'><h2>Receita</h2><div class='big'>R$ {r:.2f}</div></div>"
    cards += f"<div class='card'><h2>Lucro</h2><div class='big'>R$ {l:.2f}</div></div>"
    return layout(f"<h1>🔥 STREETCORE OS V31 OMEGA SUPREME</h1><div class='grid'>{cards}</div><div class='card'><pre>{plano()}</pre></div>")


@app.route("/login", methods=["GET","POST"])
def login():
    erro = ""
    if request.method == "POST":
        if request.form.get("usuario") == ADMIN_USER and request.form.get("senha") == ADMIN_PASS:
            session["logado"] = True
            return redirect("/")
        erro = "<p style='color:red'>Login incorreto</p>"
    return f"""<body style="background:#050505;color:white;font-family:Arial;display:flex;justify-content:center;align-items:center;height:100vh">
<div style="background:#111;padding:40px;border-radius:20px;width:330px">
<h1>🔥 StreetCore V31</h1>{erro}
<form method="POST">
<input name="usuario" placeholder="Usuário" style="width:100%;padding:14px;margin-bottom:12px">
<input name="senha" type="password" placeholder="Senha" style="width:100%;padding:14px;margin-bottom:12px">
<button style="width:100%;padding:14px;background:#00ff88;border:0;border-radius:10px;font-weight:bold">Entrar</button>
</form><p>admin / streetcore</p></div></body>"""


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/health")
def health():
    return jsonify({"status":"online","version":"V31 OMEGA SUPREME"})


@app.route("/omega", methods=["GET","POST"])
def omega():
    if not login_required(): return redirect("/login")
    resp = ""
    if request.method == "POST":
        comando = request.form.get("comando","")
        resp = f"🧠 OMEGA CENTER\n\nComando: {comando}\n\n{relatorio()}\n\n{plano()}"
    return layout(f"""<h1>👑 Omega Center</h1><div class='card'><form method='POST'><input name='comando' placeholder='O que devo analisar?'><button>Analisar</button></form></div><div class='card'><pre>{resp}</pre></div>""")


@app.route("/criar", methods=["GET","POST"])
def criar():
    if not login_required(): return redirect("/login")
    msg = ""
    if request.method == "POST":
        tipo = request.form.get("tipo")
        nome = request.form.get("nome")
        extra = request.form.get("extra")
        valor = request.form.get("valor")
        if tipo == "pedido": insert("pedidos","nome,cliente",(nome,extra)); msg="Pedido criado"
        if tipo == "lead": insert("leads","nome,origem",(nome,extra)); msg="Lead criado"
        if tipo == "cliente": insert("clientes","nome,contato,historico",(nome,extra,"Criado no painel")); msg="Cliente criado"
        if tipo == "produto": insert("produtos","nome,preco,descricao",(nome,float(valor or 0),extra)); msg="Produto criado"
        if tipo == "tarefa": insert("tarefas","titulo",(nome,)); msg="Tarefa criada"
        if tipo == "producao": insert("producao","item,cliente",(nome,extra)); msg="Produção criada"
        if tipo == "estoque": insert("estoque","item,quantidade",(nome,int(valor or 0))); msg="Estoque atualizado"
        if tipo == "receita": insert("financeiro","tipo,valor,descricao",("receita",float(valor or 0),nome)); msg="Receita criada"
        if tipo == "despesa": insert("financeiro","tipo,valor,descricao",("despesa",float(valor or 0),nome)); msg="Despesa criada"
        log(f"Criado via painel: {tipo} {nome}")
    return layout(f"""<h1>➕ Criar</h1><div class='card'><p>{msg}</p><form method='POST'>
<select name='tipo'><option>pedido</option><option>lead</option><option>cliente</option><option>produto</option><option>tarefa</option><option>producao</option><option>estoque</option><option>receita</option><option>despesa</option></select>
<input name='nome' placeholder='Nome/descrição'><input name='extra' placeholder='Cliente/origem/contato/descrição'><input name='valor' placeholder='Valor ou quantidade'><button>Criar</button></form></div>""")


@app.route("/conteudo", methods=["GET","POST"])
def conteudo():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        tema = request.form.get("tema","Street Graff")
        tipo = request.form.get("tipo")
        res = gerar_campanha(tema) if tipo == "campanha" else gerar_post(tema)
        insert("conteudos","tema,tipo,texto",(tema,tipo,res))
    return layout(f"<h1>🤖 Conteúdo IA</h1><div class='card'><form method='POST'><input name='tema' placeholder='Tema'><select name='tipo'><option>post</option><option>campanha</option></select><button>Gerar</button></form></div><div class='card'><textarea>{res}</textarea></div>")


@app.route("/propostas", methods=["GET","POST"])
def propostas():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente = request.form.get("cliente")
        desc = request.form.get("descricao")
        res = proposta(cliente, desc)
        insert("propostas","cliente,descricao,valor,texto",(cliente,desc,calcular_orcamento(desc),res))
    return layout(f"<h1>🧾 Propostas</h1><div class='card'><form method='POST'><input name='cliente' placeholder='Cliente'><textarea name='descricao'></textarea><button>Gerar</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/atendimento", methods=["GET","POST"])
def atendimento():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente = request.form.get("cliente","cliente")
        pergunta = request.form.get("pergunta","")
        res = faq(pergunta)
        insert("atendimentos","cliente,pergunta,resposta",(cliente,pergunta,res))
    return layout(f"<h1>💬 Atendimento</h1><div class='card'><form method='POST'><input name='cliente'><textarea name='pergunta'></textarea><button>Responder</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/table/<tabela>")
def tabela(tabela):
    if not login_required(): return redirect("/login")
    permitidas = ["pedidos","leads","clientes","produtos","tarefas","producao","estoque","fornecedores","notificacoes","logs","campanhas","conteudos","propostas","atendimentos"]
    if tabela not in permitidas: return "Tabela não permitida"
    dados = listar(tabela)
    linhas = "".join(["<tr>"+"".join([f"<td>{x}</td>" for x in d])+f"<td><a href='/delete/{tabela}/{d[0]}'>Excluir</a></td></tr>" for d in dados])
    return layout(f"<h1>{tabela.title()}</h1><a href='/export/{tabela}'>Exportar CSV</a><table>{linhas}</table>")


@app.route("/delete/<tabela>/<int:id>")
def delete(tabela, id):
    if not login_required(): return redirect("/login")
    sql(f"DELETE FROM {tabela} WHERE id=?", (id,))
    return redirect(f"/table/{tabela}")


@app.route("/financeiro-web")
def financeiro_web():
    if not login_required(): return redirect("/login")
    r,d,l=financeiro()
    return layout(f"<h1>💵 Financeiro</h1><div class='grid'><div class='card'><h2>Receita</h2><div class='big'>R$ {r:.2f}</div></div><div class='card'><h2>Despesa</h2><div class='big'>R$ {d:.2f}</div></div><div class='card'><h2>Lucro</h2><div class='big'>R$ {l:.2f}</div></div></div>")


@app.route("/relatorio-web")
def relatorio_web():
    if not login_required(): return redirect("/login")
    return layout(f"<h1>📊 Relatório</h1><div class='card'><pre>{relatorio()}</pre></div>")


@app.route("/export/<tabela>")
def export(tabela):
    if not login_required(): return redirect("/login")
    dados = listar(tabela)
    csv = "\n".join([",".join(map(lambda x: str(x).replace(",", " "), d)) for d in dados])
    return Response(csv, mimetype="text/csv", headers={"Content-Disposition":f"attachment;filename={tabela}.csv"})


@app.route("/backup")
def backup():
    if not login_required(): return redirect("/login")
    with open(DB_PATH,"rb") as f: data=f.read()
    nome=f"backup_v31_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition":f"attachment;filename={nome}"})


@app.route("/api/info")
def api_info():
    return jsonify({"api_key_header":"X-API-Key","endpoints":["/api/relatorio","/api/table/<tabela>"]})


def api_ok():
    return request.headers.get("X-API-Key") == API_KEY


@app.route("/api/relatorio")
def api_relatorio():
    if not api_ok(): return jsonify({"erro":"API key inválida"}), 403
    return jsonify({"relatorio":relatorio()})


@app.route("/api/table/<tabela>")
def api_table(tabela):
    if not api_ok(): return jsonify({"erro":"API key inválida"}), 403
    return jsonify({"dados":listar(tabela)})


async def send(update, txt):
    await update.message.reply_text(txt)


async def start(update, context):
    await send(update, "🔥 V31 OMEGA SUPREME\n/supreme vender mais\n/relatorio\n/pedido camiseta joao\n/lead maria instagram\n/proposta joao 10 camisetas\n/receita 100\n/despesa 50\n/financeiro\n/post camisetas\n/campanha street graff")


async def supreme_cmd(update, context): await send(update, f"👑 OMEGA\n\n{relatorio()}\n\n{plano()}")
async def relatorio_cmd(update, context): await send(update, relatorio())
async def post_cmd(update, context): await send(update, gerar_post(" ".join(context.args) or "Street Graff"))
async def campanha_cmd(update, context): await send(update, gerar_campanha(" ".join(context.args) or "Street Graff"))
async def financeiro_cmd(update, context):
    r,d,l=financeiro()
    await send(update, f"Receita R$ {r:.2f}\nDespesa R$ {d:.2f}\nLucro R$ {l:.2f}")


async def pedido_cmd(update, context):
    insert("pedidos","nome,cliente",(context.args[0] if context.args else "", " ".join(context.args[1:])))
    await send(update, "📦 Pedido criado.")


async def lead_cmd(update, context):
    insert("leads","nome,origem",(context.args[0] if context.args else "", " ".join(context.args[1:]) or "telegram"))
    await send(update, "🎯 Lead criado.")


async def proposta_cmd(update, context):
    cliente = context.args[0] if context.args else "cliente"
    desc = " ".join(context.args[1:]) or "pedido"
    txt = proposta(cliente, desc)
    insert("propostas","cliente,descricao,valor,texto",(cliente,desc,calcular_orcamento(desc),txt))
    await send(update, txt)


async def receita_cmd(update, context):
    v=float(context.args[0].replace(",", "."))
    insert("financeiro","tipo,valor,descricao",("receita",v,"telegram"))
    await send(update, f"💰 Receita R$ {v:.2f}")


async def despesa_cmd(update, context):
    v=float(context.args[0].replace(",", "."))
    insert("financeiro","tipo,valor,descricao",("despesa",v,"telegram"))
    await send(update, f"💸 Despesa R$ {v:.2f}")


async def responder(update, context):
    log(update.message.text)
    await send(update, faq(update.message.text))


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()
    comandos = {
        "start": start, "supreme": supreme_cmd, "relatorio": relatorio_cmd,
        "pedido": pedido_cmd, "lead": lead_cmd, "proposta": proposta_cmd,
        "receita": receita_cmd, "despesa": despesa_cmd, "financeiro": financeiro_cmd,
        "post": post_cmd, "campanha": campanha_cmd
    }
    for n,f in comandos.items(): bot.add_handler(CommandHandler(n,f))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("🔥 Telegram iniciando V31...")
    await bot.initialize(); await bot.start(); await bot.updater.start_polling()
    print("✅ Telegram ONLINE V31")
    await asyncio.Event().wait()


def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())


iniciar_banco()
threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
