import os, sqlite3, threading, asyncio, json
from datetime import datetime
from flask import Flask, jsonify, request, redirect, session, Response
from telegram.ext import Application, CommandHandler, MessageHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY", "streetcore-v32-hypercore")
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "streetcore")
API_KEY = os.getenv("STREETCORE_API_KEY", "streetcore-api")
DB_PATH = os.getenv("DB_PATH", "streetcore_master.db")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não encontrado.")

app = Flask(__name__)
app.secret_key = SECRET_KEY

TABLES = {
    "pedidos": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,cliente TEXT,status TEXT DEFAULT 'novo',valor REAL DEFAULT 0,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "leads": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,origem TEXT,status TEXT DEFAULT 'novo',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "clientes": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,contato TEXT,historico TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "financeiro": "id INTEGER PRIMARY KEY AUTOINCREMENT,tipo TEXT,valor REAL,descricao TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "produtos": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,preco REAL,descricao TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "estoque": "id INTEGER PRIMARY KEY AUTOINCREMENT,item TEXT,quantidade INTEGER,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "producao": "id INTEGER PRIMARY KEY AUTOINCREMENT,item TEXT,cliente TEXT,status TEXT DEFAULT 'aguardando',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "tarefas": "id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT,status TEXT DEFAULT 'pendente',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "campanhas": "id INTEGER PRIMARY KEY AUTOINCREMENT,tema TEXT,texto TEXT,status TEXT DEFAULT 'planejada',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "conteudos": "id INTEGER PRIMARY KEY AUTOINCREMENT,tema TEXT,tipo TEXT,texto TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "propostas": "id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,descricao TEXT,valor REAL,texto TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "documentos": "id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT,tipo TEXT,texto TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "conhecimento": "id INTEGER PRIMARY KEY AUTOINCREMENT,titulo TEXT,texto TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "atendimentos": "id INTEGER PRIMARY KEY AUTOINCREMENT,cliente TEXT,pergunta TEXT,resposta TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "fornecedores": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,contato TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "notificacoes": "id INTEGER PRIMARY KEY AUTOINCREMENT,mensagem TEXT,status TEXT DEFAULT 'nova',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "metas": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,valor TEXT,status TEXT DEFAULT 'ativa',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "automacoes": "id INTEGER PRIMARY KEY AUTOINCREMENT,nome TEXT,acao TEXT,status TEXT DEFAULT 'ativa',criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    "logs": "id INTEGER PRIMARY KEY AUTOINCREMENT,mensagem TEXT,criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
}

SAFE_TABLES = list(TABLES.keys())


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
    print("✅ StreetCore OS V32 HyperCore Supreme iniciado.")


def inserir(tabela, campos, valores):
    q = ",".join(["?"] * len(valores))
    sql(f"INSERT INTO {tabela} ({campos}) VALUES ({q})", valores)


def listar(tabela, limit=150):
    if tabela not in SAFE_TABLES:
        return []
    return sql(f"SELECT * FROM {tabela} ORDER BY id DESC LIMIT ?", (limit,), True)


def contar(tabela):
    return sql(f"SELECT COUNT(*) FROM {tabela}", fetch=True)[0][0]


def log(msg):
    inserir("logs", "mensagem", (msg,))


def financeiro():
    r = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='receita'", fetch=True)[0][0] or 0
    d = sql("SELECT SUM(valor) FROM financeiro WHERE tipo='despesa'", fetch=True)[0][0] or 0
    return r, d, r - d


def login_required():
    return session.get("ok") is True


def post(tema):
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
    return f"""🧾 PROPOSTA COMERCIAL STREET GRAFF

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
    if "prazo" in p: return "Prazo padrão: 5 dias úteis de produção + transporte."
    if "pagamento" in p or "pix" in p: return "Pagamento somente via PIX."
    if "orçamento" in p or "orcamento" in p: return "Informe produto, quantidade, tamanho e se já possui arte."
    if "camiseta" in p: return "Fazemos camisetas personalizadas. Valor depende da quantidade e arte."
    if "caneca" in p: return "Fazemos canecas personalizadas sob encomenda."
    if "adesivo" in p: return "Fazemos adesivos personalizados em vários tamanhos."
    return "Fazemos camisetas, adesivos, canecas, panfletos e brindes personalizados."


def plano():
    return """✅ PLANO SUPREMO DO DIA

1. Ver leads novos.
2. Responder clientes.
3. Criar campanha de venda.
4. Gerar post + story + reels.
5. Atualizar pedidos.
6. Conferir produção.
7. Conferir estoque.
8. Registrar receitas e despesas.
9. Gerar propostas para leads quentes.
10. Fazer backup e fechar vendas."""


def relatorio():
    r, d, l = financeiro()
    linhas = [f"{t}: {contar(t)}" for t in ["pedidos","leads","clientes","propostas","produtos","estoque","producao","tarefas","campanhas","conteudos","documentos","conhecimento","atendimentos","automacoes"]]
    return "📊 RELATÓRIO HYPERCORE V32\n\n" + "\n".join(linhas) + f"\n\nReceita: R$ {r:.2f}\nDespesa: R$ {d:.2f}\nLucro: R$ {l:.2f}\n\nDecisão: captar leads, gerar campanha, criar propostas e acompanhar produção."


def buscar(termo):
    like = f"%{termo}%"
    blocos = []
    pesquisas = {
        "pedidos": "nome LIKE ? OR cliente LIKE ?",
        "leads": "nome LIKE ? OR origem LIKE ?",
        "clientes": "nome LIKE ? OR contato LIKE ? OR historico LIKE ?",
        "propostas": "cliente LIKE ? OR descricao LIKE ? OR texto LIKE ?",
        "documentos": "titulo LIKE ? OR texto LIKE ?",
        "conhecimento": "titulo LIKE ? OR texto LIKE ?"
    }
    for t, where in pesquisas.items():
        params = tuple([like] * where.count("?"))
        dados = sql(f"SELECT * FROM {t} WHERE {where} LIMIT 20", params, True)
        if dados:
            blocos.append(f"{t.upper()}:\n" + "\n".join(map(str, dados)))
    return "\n\n".join(blocos) if blocos else "Nenhum resultado encontrado."


def layout(c):
    menu = ["dashboard:/","criar:/criar","omega:/omega","conteúdo:/conteudo","propostas:/propostas","atendimento:/atendimento","busca:/buscar","financeiro:/financeiro","relatório:/relatorio","backup:/backup"]
    tables = ["pedidos","leads","clientes","produtos","estoque","producao","tarefas","campanhas","conteudos","documentos","conhecimento","atendimentos","fornecedores","notificacoes","metas","automacoes","logs"]
    links = "".join([f"<a href='{url}'>{name}</a>" for x in menu for name,url in [x.split(":")]])
    links += "<hr>" + "".join([f"<a href='/table/{t}'>{t.title()}</a>" for t in tables])
    return f"""
<html><head><title>StreetCore V32</title>
<style>
body{{margin:0;background:#050505;color:#fff;font-family:Arial}}
.sidebar{{position:fixed;top:0;left:0;bottom:0;width:285px;background:#0b0b0b;border-right:1px solid #222;padding:24px;overflow:auto}}
.sidebar h2{{color:#00ff88}} .sidebar a{{display:block;color:white;text-decoration:none;margin:11px 0}} .sidebar a:hover{{color:#00ff88}}
.main{{margin-left:335px;padding:30px}} .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:18px}}
.card{{background:#111;border:1px solid #333;border-radius:18px;padding:22px;margin-bottom:18px}} .big{{color:#00ff88;font-size:34px;font-weight:bold}}
input,select,textarea{{padding:12px;border-radius:10px;border:0;margin:6px 0;width:100%;background:#1c1c1c;color:white}} textarea{{min-height:170px}}
button{{padding:12px 18px;border:0;border-radius:10px;background:#00ff88;font-weight:bold;cursor:pointer}}
table{{width:100%;border-collapse:collapse;background:#111}} th,td{{padding:12px;border-bottom:1px solid #333;vertical-align:top}} a{{color:#00ff88}} pre{{white-space:pre-wrap}}
</style></head>
<body><div class="sidebar"><h2>🔥 StreetCore V32</h2>{links}<a href='/logout'>Sair</a></div><div class="main">{c}</div></body></html>"""


@app.route("/login", methods=["GET","POST"])
def login():
    erro = ""
    if request.method == "POST":
        if request.form.get("usuario") == ADMIN_USER and request.form.get("senha") == ADMIN_PASS:
            session["ok"] = True
            return redirect("/")
        erro = "<p style='color:red'>Login incorreto</p>"
    return f"""<body style="background:#050505;color:white;font-family:Arial;display:flex;align-items:center;justify-content:center;height:100vh">
<div style="background:#111;padding:40px;border-radius:20px;width:330px"><h1>🔥 StreetCore V32</h1>{erro}
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
    cards = "".join([f"<div class='card'><h2>{t.title()}</h2><div class='big'>{contar(t)}</div></div>" for t in ["pedidos","leads","clientes","propostas","produtos","estoque","producao","tarefas","campanhas","atendimentos"]])
    cards += f"<div class='card'><h2>Receita</h2><div class='big'>R$ {r:.2f}</div></div><div class='card'><h2>Lucro</h2><div class='big'>R$ {l:.2f}</div></div>"
    return layout(f"<h1>🚀 STREETCORE OS V32 HYPERCORE SUPREME</h1><div class='grid'>{cards}</div><div class='card'><pre>{plano()}</pre></div>")


@app.route("/health")
def health():
    return jsonify({"status":"online","version":"V32 HyperCore Supreme"})


@app.route("/omega", methods=["GET","POST"])
def omega():
    if not login_required(): return redirect("/login")
    resp = ""
    if request.method == "POST":
        resp = f"🧠 ANÁLISE HYPERCORE\n\nComando: {request.form.get('comando')}\n\n{relatorio()}\n\n{plano()}"
    return layout(f"<h1>🧠 Omega HyperCore</h1><div class='card'><form method='POST'><input name='comando' placeholder='O que devo analisar?'><button>Analisar</button></form></div><div class='card'><pre>{resp}</pre></div>")


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
        inserir("conteudos","tema,tipo,texto",(tema,tipo,res))
    return layout(f"<h1>🤖 Conteúdo IA</h1><div class='card'><form method='POST'><input name='tema' placeholder='Tema'><select name='tipo'><option>post</option><option>story</option><option>reels</option><option>campanha</option></select><button>Gerar</button></form></div><div class='card'><textarea>{res}</textarea></div>")


@app.route("/propostas", methods=["GET","POST"])
def propostas():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente, desc = request.form.get("cliente"), request.form.get("descricao")
        res = gerar_proposta(cliente, desc)
        inserir("propostas","cliente,descricao,valor,texto",(cliente,desc,valor_orcamento(desc),res))
    return layout(f"<h1>🧾 Propostas</h1><div class='card'><form method='POST'><input name='cliente' placeholder='Cliente'><textarea name='descricao'></textarea><button>Gerar</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/atendimento", methods=["GET","POST"])
def atendimento():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        cliente, pergunta = request.form.get("cliente","cliente"), request.form.get("pergunta","")
        res = faq(pergunta)
        inserir("atendimentos","cliente,pergunta,resposta",(cliente,pergunta,res))
    return layout(f"<h1>💬 Atendimento IA</h1><div class='card'><form method='POST'><input name='cliente'><textarea name='pergunta'></textarea><button>Responder</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/buscar", methods=["GET","POST"])
def buscar_web():
    if not login_required(): return redirect("/login")
    res = ""
    if request.method == "POST":
        res = buscar(request.form.get("termo",""))
    return layout(f"<h1>🔎 Busca Geral</h1><div class='card'><form method='POST'><input name='termo'><button>Buscar</button></form></div><div class='card'><pre>{res}</pre></div>")


@app.route("/financeiro")
def financeiro_web():
    if not login_required(): return redirect("/login")
    r,d,l=financeiro()
    return layout(f"<h1>💵 Financeiro</h1><div class='grid'><div class='card'><h2>Receita</h2><div class='big'>R$ {r:.2f}</div></div><div class='card'><h2>Despesa</h2><div class='big'>R$ {d:.2f}</div></div><div class='card'><h2>Lucro</h2><div class='big'>R$ {l:.2f}</div></div></div>")


@app.route("/relatorio")
def relatorio_web():
    if not login_required(): return redirect("/login")
    return layout(f"<h1>📊 Relatório Supremo</h1><div class='card'><pre>{relatorio()}</pre></div>")


@app.route("/table/<tabela>")
def table(tabela):
    if not login_required(): return redirect("/login")
    if tabela not in SAFE_TABLES: return "Tabela não permitida"
    dados = listar(tabela)
    linhas = "".join(["<tr>" + "".join([f"<td>{x}</td>" for x in d]) + f"<td><a href='/delete/{tabela}/{d[0]}'>Excluir</a></td></tr>" for d in dados])
    return layout(f"<h1>{tabela.title()}</h1><a href='/export/{tabela}'>Exportar CSV</a><table>{linhas}</table>")


@app.route("/delete/<tabela>/<int:item_id>")
def delete(tabela, item_id):
    if not login_required(): return redirect("/login")
    if tabela in SAFE_TABLES:
        sql(f"DELETE FROM {tabela} WHERE id=?", (item_id,))
    return redirect(f"/table/{tabela}")


@app.route("/export/<tabela>")
def export(tabela):
    if not login_required(): return redirect("/login")
    if tabela not in SAFE_TABLES: return "Tabela não permitida"
    rows = listar(tabela, 10000)
    csv = "\n".join([",".join([str(x).replace(",", " ") for x in r]) for r in rows])
    return Response(csv, mimetype="text/csv", headers={"Content-Disposition":f"attachment;filename={tabela}.csv"})


@app.route("/backup")
def backup():
    if not login_required(): return redirect("/login")
    with open(DB_PATH, "rb") as f: data = f.read()
    return Response(data, mimetype="application/octet-stream", headers={"Content-Disposition":f"attachment;filename=backup_v32_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"})


@app.route("/api/info")
def api_info():
    return jsonify({"version":"V32 HyperCore Supreme","api_key_header":"X-API-Key","tables":SAFE_TABLES})


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


async def send(update, txt):
    await update.message.reply_text(txt[:3900])


async def start_cmd(update, context):
    await send(update, "🔥 STREETCORE V32 HYPERCORE\n/supreme vender mais\n/relatorio\n/pedido camiseta joao\n/lead maria instagram\n/proposta joao 10 camisetas\n/receita 100\n/despesa 50\n/financeiro\n/post camisetas\n/campanha street graff\n/buscar joao")


async def supreme_cmd(update, context): await send(update, f"🧠 HYPERCORE\n\n{relatorio()}\n\n{plano()}")
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


async def responder(update, context):
    log(update.message.text)
    await send(update, faq(update.message.text))


async def telegram_main():
    bot = Application.builder().token(TELEGRAM_TOKEN).build()
    commands = {
        "start": start_cmd, "supreme": supreme_cmd, "relatorio": relatorio_cmd,
        "pedido": pedido_cmd, "lead": lead_cmd, "proposta": proposta_cmd,
        "receita": receita_cmd, "despesa": despesa_cmd, "financeiro": financeiro_cmd,
        "post": post_cmd, "campanha": campanha_cmd, "buscar": buscar_cmd
    }
    for n,f in commands.items():
        bot.add_handler(CommandHandler(n, f))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
    print("🔥 Telegram iniciando V32...")
    await bot.initialize()
    await bot.start()
    await bot.updater.start_polling()
    print("✅ Telegram ONLINE V32")
    await asyncio.Event().wait()


def run_telegram():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(telegram_main())


iniciar_banco()
threading.Thread(target=run_telegram, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
