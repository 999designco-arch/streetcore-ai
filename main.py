import os, sqlite3, urllib.parse, threading, math, json, secrets, csv, io
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from telegram.ext import ApplicationBuilder, CommandHandler
from groq import Groq
from pypdf import PdfReader

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "streetcore123")
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = Groq(api_key=GROQ_API_KEY)
conn = sqlite3.connect("streetcore_v9.db", check_same_thread=False)
cursor = conn.cursor()

TABLES = [
"CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT,plan TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,content TEXT,vector TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,project_id INTEGER,task TEXT,status TEXT,priority TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS projects(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,description TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,agent TEXT,prompt TEXT,response TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,filename TEXT,content TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,platform TEXT,theme TEXT,content TEXT,status TEXT,scheduled_date TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS videos(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,theme TEXT,script TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS workflows(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,trigger_text TEXT,steps TEXT,status TEXT,last_run TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS gallery(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,type TEXT,prompt TEXT,url TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS analytics(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,event TEXT,data TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,email TEXT,phone TEXT,stage TEXT,notes TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS content_calendar(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,title TEXT,platform TEXT,publish_date TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS pages(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,type TEXT,title TEXT,html TEXT,created_at TEXT)"
]

for t in TABLES:
    cursor.execute(t)
conn.commit()

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def uid():
    return session.get("user_id", 1)

def ensure_admin():
    row = cursor.execute("SELECT id FROM users WHERE email=?", ("admin@streetcore.ai",)).fetchone()
    if not row:
        cursor.execute(
            "INSERT INTO users(name,email,password,role,plan,created_at) VALUES(?,?,?,?,?,?)",
            ("Admin", "admin@streetcore.ai", generate_password_hash(ADMIN_PASSWORD), "admin", "god", now())
        )
        conn.commit()

ensure_admin()

MASTER_PROMPT = """
Você é StreetCore OS V9 — AI Company Operating System.
Responda sempre em português.
Use ferramentas gratuitas ou plano grátis como padrão.
Aja como CEO, CMO, CTO, diretor criativo, growth hacker, engenheiro de automação,
copywriter, social media, vendedor, product manager e operador executivo.
Explique passo a passo, como se estivesse fazendo pelo usuário.
Nunca execute ações sensíveis sem aprovação humana.
"""

AGENTS = {
    "ceo": "CEO Agent: estratégia, monetização, escala, priorização e negócios digitais.",
    "marketing": "Marketing Agent: branding, copy, viralização, funis, conteúdo e crescimento.",
    "dev": "Dev Agent: Python, APIs, SaaS, automação, banco, deploy e arquitetura.",
    "design": "Design Agent: direção criativa, cyberpunk premium, logos, imagens e identidade visual.",
    "video": "Video Agent: roteiros, cenas, prompts de vídeo, Reels, Shorts e anúncios.",
    "automation": "Automation Agent: workflows, processos, produtividade e sistemas automáticos.",
    "sales": "Sales Agent: oferta, vendas, objeções, WhatsApp, fechamento e monetização.",
    "finance": "Finance Agent: preço, planos, custos, margem e lucro.",
    "ops": "Ops Agent: processos, tarefas, execução, rotina e produtividade."
}

SENSITIVE = ["publicar", "postar agora", "enviar", "apagar", "deletar", "comprar", "pagar", "contratar", "cancelar", "transferir"]

def log_event(event, data="", user_id=None):
    cursor.execute("INSERT INTO analytics(user_id,event,data,created_at) VALUES(?,?,?,?)", (user_id or uid(), event, data, now()))
    conn.commit()

def text_vector(text, size=128):
    vec = [0.0] * size
    for w in text.lower().split():
        vec[hash(w) % size] += 1.0
    norm = math.sqrt(sum(x*x for x in vec)) or 1
    return [x / norm for x in vec]

def cosine(a, b):
    return sum(x*y for x, y in zip(a, b))

def save_memory(content, user_id=None):
    user_id = user_id or uid()
    cursor.execute(
        "INSERT INTO memory(user_id,content,vector,created_at) VALUES(?,?,?,?)",
        (user_id, content, json.dumps(text_vector(content)), now())
    )
    conn.commit()

def vector_search(query, user_id=None, limit=6):
    user_id = user_id or uid()
    qv = text_vector(query)
    rows = cursor.execute("SELECT content,vector FROM memory WHERE user_id=?", (user_id,)).fetchall()
    scored = []
    for content, v in rows:
        try:
            scored.append((cosine(qv, json.loads(v)), content))
        except:
            pass
    scored.sort(reverse=True)
    return [x[1] for x in scored[:limit]]

def ask_ai(prompt, role="ceo", user_id=None):
    user_id = user_id or uid()
    memories = "\n".join(vector_search(prompt, user_id))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT},
            {"role": "system", "content": AGENTS.get(role, "")},
            {"role": "system", "content": "MEMÓRIA:\n" + memories},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=3500
    )
    result = response.choices[0].message.content
    cursor.execute("INSERT INTO history(user_id,agent,prompt,response,created_at) VALUES(?,?,?,?,?)", (user_id, role, prompt, result, now()))
    conn.commit()
    log_event("ai_response", role, user_id)
    return result

def image_url(prompt):
    return "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)

def needs_approval(text):
    return any(x in text.lower() for x in SENSITIVE)

def count_table(table):
    return cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id=?", (uid(),)).fetchone()[0]

def read_file(filename, path):
    content = ""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(path)
        for p in reader.pages:
            try:
                content += p.extract_text() + "\n"
            except:
                pass
    elif filename.lower().endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    return content[:60000]

def create_project_from_goal(goal, user_id):
    plan = ask_ai(f"Crie um projeto operacional completo para: {goal}. Inclua objetivo, roadmap, tarefas e prioridades.", "ops", user_id)
    cursor.execute("INSERT INTO projects(user_id,name,description,status,created_at) VALUES(?,?,?,?,?)", (user_id, goal[:80], plan, "ativo", now()))
    project_id = cursor.lastrowid
    tasks_prompt = ask_ai(f"Liste 10 tarefas práticas e curtas para executar este projeto: {goal}. Apenas lista numerada.", "ops", user_id)
    for line in tasks_prompt.split("\n"):
        clean = line.strip(" -0123456789.").strip()
        if len(clean) > 5:
            cursor.execute("INSERT INTO tasks(user_id,project_id,task,status,priority,created_at) VALUES(?,?,?,?,?,?)", (user_id, project_id, clean, "pendente", "alta", now()))
    conn.commit()
    return plan

def debate_agents(goal, user_id):
    final = ""
    for role in ["ceo", "marketing", "sales", "dev", "automation", "design", "finance", "ops"]:
        result = ask_ai(f"Analise este objetivo pelo seu ponto de vista e entregue plano objetivo: {goal}", role, user_id)
        final += f"\n\n## {role.upper()}\n\n{result}"
    synthesis = ask_ai(f"Com base nestas análises dos agentes, crie uma decisão final integrada:\n{final}", "ceo", user_id)
    return final + "\n\n# DECISÃO FINAL INTEGRADA\n\n" + synthesis

def generate_landing_html(title, offer):
    html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body{{margin:0;background:#07070a;color:white;font-family:Arial}}
section{{padding:70px 10%;}}
.hero{{background:linear-gradient(135deg,#07070a,#2b0055);min-height:70vh;display:flex;flex-direction:column;justify-content:center}}
h1{{font-size:54px;max-width:900px}}
p{{font-size:20px;line-height:1.6;color:#ddd;max-width:850px}}
.cta{{display:inline-block;background:#9333ea;color:white;padding:18px 28px;border-radius:14px;text-decoration:none;font-weight:bold;margin-top:20px}}
.card{{background:#111827;border:1px solid #333;border-radius:18px;padding:24px;margin:15px 0}}
</style>
</head>
<body>
<section class="hero">
<h1>{title}</h1>
<p>{offer}</p>
<a class="cta" href="#">Quero começar agora</a>
</section>
<section>
<h2>Por que isso funciona?</h2>
<div class="card">Sistema simples, direto e criado para gerar resultado.</div>
<div class="card">Oferta clara, promessa forte e execução prática.</div>
<div class="card">Estrutura pronta para captar leads e vender.</div>
</section>
<section>
<h2>Próximo passo</h2>
<p>Entre em contato e receba uma análise personalizada.</p>
<a class="cta" href="#">Solicitar diagnóstico</a>
</section>
</body>
</html>
"""
    return html

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

# TELEGRAM

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore OS V9 online. Digite /menu")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE OS V9

/completo ideia
/debate ideia
/ceo /marketing /dev /design /video /auto /sales /finance /ops

/criar_empresa ideia
/criar_saas ideia
/criar_campanha ideia
/criar_funil ideia
/criar_marca ideia
/criar_produto ideia
/criar_landing ideia
/criar_site ideia
/criar_projeto ideia

/post instagram tema
/social30 tema
/videoai tema
/workflow objetivo
/copiloto objetivo

/salvar memória
/buscar termo
/tarefa texto
/status
""")

async def status(update, context):
    text = "🚀 STREETCORE OS V9\n\n"
    for t in ["memory","tasks","projects","posts","videos","workflows","leads","content_calendar","pages","gallery"]:
        total = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        text += f"{t}: {total}\n"
    await update.message.reply_text(text)

async def generic_agent(update, context, role):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Digite algo.")
        return
    await send_long(update, ask_ai(prompt, role, 1))

async def completo(update, context):
    prompt = " ".join(context.args)
    await send_long(update, debate_agents(prompt, 1))

async def debate(update, context):
    await completo(update, context)

async def ceo(u,c): await generic_agent(u,c,"ceo")
async def marketing(u,c): await generic_agent(u,c,"marketing")
async def dev(u,c): await generic_agent(u,c,"dev")
async def design(u,c): await generic_agent(u,c,"design")
async def video_cmd(u,c): await generic_agent(u,c,"video")
async def auto(u,c): await generic_agent(u,c,"automation")
async def sales(u,c): await generic_agent(u,c,"sales")
async def finance(u,c): await generic_agent(u,c,"finance")
async def ops(u,c): await generic_agent(u,c,"ops")

async def creator(update, context, kind):
    idea = " ".join(context.args)
    prompts = {
        "empresa": "Crie uma empresa IA completa com operação, oferta, funil, produto, público e plano de 30 dias.",
        "saas": "Crie um SaaS completo com MVP, telas, stack grátis, features, pricing, roadmap e landing.",
        "campanha": "Crie campanha viral completa com posts, vídeos, calendário, CTA e funil.",
        "funil": "Crie funil completo com isca, landing, sequência, oferta, WhatsApp e automação.",
        "marca": "Crie branding completo com nome, manifesto, paleta, tom de voz e identidade.",
        "produto": "Crie produto digital premium com promessa, módulos, bônus, preço e lançamento."
    }
    await send_long(update, ask_ai(prompts[kind] + "\n\nIdeia:\n" + idea, "ceo", 1))

async def criar_empresa(u,c): await creator(u,c,"empresa")
async def criar_saas(u,c): await creator(u,c,"saas")
async def criar_campanha(u,c): await creator(u,c,"campanha")
async def criar_funil(u,c): await creator(u,c,"funil")
async def criar_marca(u,c): await creator(u,c,"marca")
async def criar_produto(u,c): await creator(u,c,"produto")

async def criar_landing(update, context):
    idea = " ".join(context.args)
    copy = ask_ai(f"Crie headline e oferta para landing page sobre: {idea}", "marketing", 1)
    html = generate_landing_html(idea[:60], copy[:900])
    cursor.execute("INSERT INTO pages(user_id,type,title,html,created_at) VALUES(?,?,?,?,?)", (1, "landing", idea[:80], html, now()))
    conn.commit()
    await update.message.reply_text("✅ Landing page criada e salva no painel em Pages/Sites.")

async def criar_site(update, context):
    await criar_landing(update, context)

async def criar_projeto(update, context):
    goal = " ".join(context.args)
    plan = create_project_from_goal(goal, 1)
    await send_long(update, plan)

async def tarefa(update, context):
    text = " ".join(context.args)
    cursor.execute("INSERT INTO tasks(user_id,project_id,task,status,priority,created_at) VALUES(?,?,?,?,?,?)", (1, None, text, "pendente", "normal", now()))
    conn.commit()
    await update.message.reply_text("✅ tarefa salva")

async def salvar(update, context):
    save_memory(" ".join(context.args), 1)
    await update.message.reply_text("🧠 memória salva")

async def buscar(update, context):
    q = " ".join(context.args)
    results = vector_search(q, 1, 8)
    await send_long(update, "\n\n".join(results) if results else "Nada encontrado.")

async def post(update, context):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Use: /post instagram tema")
        return
    platform = args[0]
    theme = " ".join(args[1:])
    content = ask_ai(f"Crie post para {platform}: {theme}. Inclua legenda, CTA, hashtags e ideia visual.", "marketing", 1)
    cursor.execute("INSERT INTO posts(user_id,platform,theme,content,status,scheduled_date,created_at) VALUES(?,?,?,?,?,?,?)", (1, platform, theme, content, "rascunho", "", now()))
    conn.commit()
    await send_long(update, content)

async def social30(update, context):
    theme = " ".join(context.args)
    plan = ask_ai(f"Crie calendário de 30 posts para: {theme}. Para cada: título, plataforma, legenda curta, CTA.", "marketing", 1)
    for i in range(1, 31):
        cursor.execute("INSERT INTO content_calendar(user_id,title,platform,publish_date,status,created_at) VALUES(?,?,?,?,?,?)", (1, f"Post {i} - {theme[:30]}", "Instagram/TikTok", f"Dia {i}", "planejado", now()))
    conn.commit()
    await send_long(update, plan)

async def videoai(update, context):
    theme = " ".join(context.args)
    script = ask_ai(f"Crie vídeo IA completo sobre: {theme}. Inclua roteiro, cenas, prompts, narração e edição.", "video", 1)
    cursor.execute("INSERT INTO videos(user_id,theme,script,status,created_at) VALUES(?,?,?,?,?)", (1, theme, script, "roteiro", now()))
    conn.commit()
    await send_long(update, script)

async def workflow(update, context):
    text = " ".join(context.args)
    steps = ask_ai(f"Crie workflow automático realista e gratuito para: {text}. Inclua gatilho, etapas, aprovação e execução.", "automation", 1)
    cursor.execute("INSERT INTO workflows(user_id,name,trigger_text,steps,status,last_run,created_at) VALUES(?,?,?,?,?,?,?)", (1, text, text, steps, "ativo", "", now()))
    conn.commit()
    await send_long(update, steps)

async def copiloto(update, context):
    goal = " ".join(context.args)
    response = ask_ai(f"Atue como copiloto operacional para: {goal}. Crie plano semanal, tarefas, prioridades, automações e riscos.", "ops", 1)
    await send_long(update, response)

# WEB

web = Flask(__name__)
web.secret_key = os.getenv("FLASK_SECRET", "streetcore-v9-" + secrets.token_hex(8))

CSS = """
<style>
*{box-sizing:border-box;font-family:Arial}body{margin:0;background:#050510;color:white;min-height:100vh}a{text-decoration:none;color:white}
.app{display:flex;min-height:100vh}.sidebar{width:280px;background:#0d0d18;padding:20px;border-right:1px solid #222}
.logo{font-size:26px;font-weight:bold;color:#a855f7}.status{font-size:12px;opacity:.7;margin:12px 0 20px}
.nav a{display:block;padding:13px;background:#151525;margin-bottom:9px;border-radius:12px}.nav a:hover{background:#222240}
.main{flex:1}.top{height:70px;background:#0d0d18;border-bottom:1px solid #222;display:flex;align-items:center;justify-content:space-between;padding:0 20px}
.content{padding:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
.card{background:#111827;border:1px solid #333;border-radius:18px;padding:18px}.big{font-size:36px;font-weight:bold;color:#a855f7}
.chat{height:calc(100vh - 245px);overflow:auto;display:flex;flex-direction:column;gap:14px;padding:15px}.msg{padding:15px;border-radius:16px;white-space:pre-wrap;line-height:1.5;max-width:900px}
.ai{background:#111827;border:1px solid #333}.user{background:#1f1f35;align-self:flex-end}.bottom{padding:14px;background:#0d0d18;border-top:1px solid #222;display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:10px}input,select,textarea{width:100%;padding:14px;border:0;border-radius:12px;background:#151525;color:white}
button{padding:14px 18px;border:0;border-radius:12px;background:#9333ea;color:white;font-weight:bold;cursor:pointer}.upload{background:#2563eb}
table{width:100%;border-collapse:collapse;background:#111827;border-radius:12px;overflow:hidden}td,th{padding:12px;border-bottom:1px solid #333;text-align:left;vertical-align:top}
.login{max-width:450px;margin:80px auto;background:#111827;padding:30px;border-radius:20px;border:1px solid #333}
.pipeline{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.stage{background:#111827;padding:14px;border-radius:16px;min-height:300px}.lead{background:#1f1f35;padding:12px;border-radius:12px;margin-bottom:10px}
@media(max-width:900px){.app{flex-direction:column}.sidebar{width:100%}.row{flex-direction:column}.pipeline{grid-template-columns:1fr}.chat{height:55vh}}
</style>
"""

def logged():
    return session.get("user_id")

def require_login():
    return bool(logged())

def current_name():
    if not logged(): return "Usuário"
    row = cursor.execute("SELECT name FROM users WHERE id=?", (uid(),)).fetchone()
    return row[0] if row else "Usuário"

def layout(title, body):
    return f"""
<!doctype html><html><head><title>{title}</title><meta name="viewport" content="width=device-width, initial-scale=1">{CSS}</head>
<body><div class="app"><div class="sidebar"><div class="logo">🔥 StreetCore OS</div><div class="status">V9 AI EXECUTION SYSTEM<br>{current_name()}</div>
<div class="nav">
<a href="/">Dashboard</a><a href="/chat">Chat IA</a><a href="/command">Command Center</a><a href="/projects">Projetos</a><a href="/calendar">Calendário</a><a href="/crm">CRM</a>
<a href="/posts">Posts</a><a href="/videos">Vídeos</a><a href="/workflows">Workflows</a><a href="/pages">Sites/Landings</a><a href="/memory">Memória</a><a href="/files">Arquivos</a>
<a href="/analytics-page">Analytics</a><a href="/logout">Sair</a></div></div>
<div class="main"><div class="top"><b>{title}</b><span>StreetCore OS V9</span></div><div class="content">{body}</div></div></div></body></html>
"""

@web.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        row = cursor.execute("SELECT id,password FROM users WHERE email=?", (email,)).fetchone()
        if row and check_password_hash(row[1], password):
            session["user_id"] = row[0]
            return redirect("/")
    return f"""<!doctype html><html><head><title>Login</title>{CSS}</head><body><div class="login">
<h1>🔥 StreetCore OS V9</h1><form method="POST">
<input name="email" value="admin@streetcore.ai"><br><br><input name="password" type="password" placeholder="Senha"><br><br><button>Entrar</button>
</form><p>Senha padrão: streetcore123</p></div></body></html>"""

@web.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@web.route("/")
def dashboard():
    if not require_login(): return redirect("/login")
    cards = ""
    for t in ["projects","tasks","posts","videos","workflows","leads","content_calendar","pages","memory","analytics"]:
        cards += f"<div class='card'><h3>{t}</h3><div class='big'>{count_table(t)}</div></div>"
    return layout("Dashboard Executivo", f"<div class='grid'>{cards}</div>")

@web.route("/chat")
def chat():
    if not require_login(): return redirect("/login")
    return layout("Chat IA", """
<div class="card"><div class="chat" id="chat"><div class="msg ai">🔥 StreetCore OS V9 online.</div></div>
<div class="bottom"><div class="row"><select id="agent">
<option value="ceo">CEO</option><option value="marketing">Marketing</option><option value="dev">Dev</option><option value="design">Design</option><option value="video">Video</option><option value="automation">Automation</option><option value="sales">Sales</option><option value="finance">Finance</option><option value="ops">Ops</option>
</select><input id="prompt" placeholder="Digite sua ideia..."><button onclick="sendMessage()">Enviar</button></div>
<div class="row"><input type="file" id="file"><button class="upload" onclick="uploadFile()">Upload IA</button></div></div></div>
<script>
function add(cls,text){document.getElementById('chat').innerHTML+=`<div class="msg ${cls}">${text}</div>`;document.getElementById('chat').scrollTop=999999}
async function sendMessage(){const text=document.getElementById('prompt').value;const agent=document.getElementById('agent').value;if(!text)return;add('user',text);document.getElementById('prompt').value='';const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:text,agent:agent})});const d=await r.json();add('ai',d.response)}
async function uploadFile(){const f=document.getElementById('file').files[0];if(!f){alert('Escolha um arquivo');return}const fd=new FormData();fd.append('file',f);const r=await fetch('/upload',{method:'POST',body:fd});const d=await r.json();add('ai',d.response)}
</script>""")

@web.route("/command")
def command():
    if not require_login(): return redirect("/login")
    return layout("Command Center", """
<div class="grid">
<div class="card"><h3>Criar Empresa IA</h3><button onclick="cmd('empresa')">Executar</button></div>
<div class="card"><h3>Criar SaaS</h3><button onclick="cmd('saas')">Executar</button></div>
<div class="card"><h3>Criar Campanha</h3><button onclick="cmd('campanha')">Executar</button></div>
<div class="card"><h3>Criar Projeto</h3><button onclick="cmd('projeto')">Executar</button></div>
<div class="card"><h3>Social 30 Posts</h3><button onclick="cmd('social30')">Executar</button></div>
<div class="card"><h3>Landing Page</h3><button onclick="cmd('landing')">Executar</button></div>
</div><br><div class="card"><input id="idea" placeholder="Digite sua ideia..."><br><br><div id="out" class="msg ai">Resultado aparecerá aqui.</div></div>
<script>
async function cmd(type){const idea=document.getElementById('idea').value||'empresa IA';document.getElementById('out').innerText='Gerando...';const r=await fetch('/command-api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:type,idea:idea})});const d=await r.json();document.getElementById('out').innerText=d.response}
</script>""")

def table_page(title, table, columns):
    if not require_login(): return redirect("/login")
    rows = cursor.execute(f"SELECT {','.join(columns)} FROM {table} WHERE user_id=? ORDER BY id DESC LIMIT 100", (uid(),)).fetchall()
    head = "".join([f"<th>{c}</th>" for c in columns])
    body = ""
    for r in rows:
        body += "<tr>" + "".join([f"<td>{str(x)[:500]}</td>" for x in r]) + "</tr>"
    return layout(title, f"<div class='card'><a href='/export/{table}'><button>Exportar CSV</button></a><br><br><table><tr>{head}</tr>{body}</table></div>")

@web.route("/projects")
def projects(): return table_page("Projetos", "projects", ["id","name","status","created_at"])
@web.route("/posts")
def posts_page(): return table_page("Posts", "posts", ["id","platform","theme","status","scheduled_date","created_at"])
@web.route("/videos")
def videos_page(): return table_page("Vídeos", "videos", ["id","theme","status","created_at"])
@web.route("/workflows")
def workflows_page(): return table_page("Workflows", "workflows", ["id","name","status","last_run","created_at"])
@web.route("/pages")
def pages_page(): return table_page("Sites/Landings", "pages", ["id","type","title","created_at"])
@web.route("/memory")
def memory_page(): return table_page("Memória", "memory", ["id","content","created_at"])
@web.route("/files")
def files_page(): return table_page("Arquivos", "files", ["id","filename","created_at"])
@web.route("/analytics-page")
def analytics_page(): return table_page("Analytics", "analytics", ["id","event","data","created_at"])

@web.route("/calendar")
def calendar():
    return table_page("Calendário", "content_calendar", ["id","title","platform","publish_date","status","created_at"])

@web.route("/crm")
def crm():
    if not require_login(): return redirect("/login")
    stages = ["Novo","Contato","Proposta","Fechado"]
    html = '<div class="pipeline">'
    for stage in stages:
        html += f"<div class='stage'><h3>{stage}</h3>"
        leads = cursor.execute("SELECT name,email FROM leads WHERE user_id=? AND stage=?", (uid(), stage)).fetchall()
        for l in leads:
            html += f"<div class='lead'><b>{l[0]}</b><br>{l[1]}</div>"
        html += "</div>"
    html += "</div><br><div class='card'><form method='POST' action='/add-lead'><input name='name' placeholder='Nome'><br><br><input name='email' placeholder='Email'><br><br><input name='phone' placeholder='Telefone'><br><br><textarea name='notes' placeholder='Notas'></textarea><br><br><button>Salvar Lead</button></form></div>"
    return layout("CRM", html)

@web.route("/add-lead", methods=["POST"])
def add_lead():
    cursor.execute("INSERT INTO leads(user_id,name,email,phone,stage,notes,created_at) VALUES(?,?,?,?,?,?,?)", (uid(), request.form.get("name"), request.form.get("email"), request.form.get("phone"), "Novo", request.form.get("notes"), now()))
    conn.commit()
    return redirect("/crm")

@web.route("/ask", methods=["POST"])
def ask_web():
    data = request.get_json()
    prompt = data.get("prompt","")
    agent = data.get("agent","ceo")
    if needs_approval(prompt):
        cursor.execute("INSERT INTO approvals(user_id,action,status,created_at) VALUES(?,?,?,?)", (uid(), prompt, "pendente", now()))
        conn.commit()
        return jsonify({"response":"🛡 Ação sensível criada para aprovação."})
    return jsonify({"response":ask_ai(prompt, agent, uid())})

@web.route("/command-api", methods=["POST"])
def command_api():
    data = request.get_json()
    kind = data.get("type")
    idea = data.get("idea")
    if kind == "projeto":
        result = create_project_from_goal(idea, uid())
    elif kind == "social30":
        result = ask_ai(f"Crie 30 posts para: {idea}", "marketing", uid())
        for i in range(1,31):
            cursor.execute("INSERT INTO content_calendar(user_id,title,platform,publish_date,status,created_at) VALUES(?,?,?,?,?,?)", (uid(), f"Post {i} - {idea[:40]}", "Instagram/TikTok", f"Dia {i}", "planejado", now()))
        conn.commit()
    elif kind == "landing":
        copy = ask_ai(f"Crie copy para landing page sobre: {idea}", "marketing", uid())
        html = generate_landing_html(idea[:60], copy[:900])
        cursor.execute("INSERT INTO pages(user_id,type,title,html,created_at) VALUES(?,?,?,?,?)", (uid(), "landing", idea[:80], html, now()))
        conn.commit()
        result = "✅ Landing page criada e salva."
    else:
        result = debate_agents(idea, uid()) if kind == "empresa" else ask_ai(f"Crie {kind} completo para: {idea}", "ceo", uid())
    return jsonify({"response":result})

@web.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file: return jsonify({"response":"Nenhum arquivo."})
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    content = read_file(filename, path)
    cursor.execute("INSERT INTO files(user_id,filename,content,created_at) VALUES(?,?,?,?)", (uid(), filename, content[:60000], now()))
    conn.commit()
    save_memory(f"Arquivo {filename}: {content[:3000]}", uid())
    analysis = ask_ai(f"Analise profundamente o arquivo {filename}:\n{content[:14000]}", "ceo", uid())
    return jsonify({"response":analysis})

@web.route("/export/<table>")
def export_table(table):
    allowed = ["posts","videos","workflows","memory","files","analytics","leads","projects","content_calendar","pages"]
    if table not in allowed: return "invalid"
    rows = cursor.execute(f"SELECT * FROM {table} WHERE user_id=?", (uid(),)).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    for r in rows: writer.writerow(r)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name=f"{table}.csv")

@web.route("/health")
def health():
    return "OK STREETCORE V9 ONLINE", 200

def run_telegram():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    handlers = {
        "start":start,"menu":menu,"status":status,"completo":completo,"debate":debate,
        "ceo":ceo,"marketing":marketing,"dev":dev,"design":design,"video":video_cmd,"auto":auto,"sales":sales,"finance":finance,"ops":ops,
        "criar_empresa":criar_empresa,"criar_saas":criar_saas,"criar_campanha":criar_campanha,"criar_funil":criar_funil,"criar_marca":criar_marca,"criar_produto":criar_produto,
        "criar_landing":criar_landing,"criar_site":criar_site,"criar_projeto":criar_projeto,
        "post":post,"social30":social30,"videoai":videoai,"workflow":workflow,"copiloto":copiloto,
        "tarefa":tarefa,"salvar":salvar,"buscar":buscar
    }
    for name, func in handlers.items():
        app.add_handler(CommandHandler(name, func))
    app.run_polling(stop_signals=None)

threading.Thread(target=run_telegram, daemon=True).start()
print("🔥 STREETCORE OS V9 ONLINE")
web.run(host="0.0.0.0", port=PORT)