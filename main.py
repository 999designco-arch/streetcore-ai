import os, sqlite3, urllib.parse, threading, math, json, secrets
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from groq import Groq
from pypdf import PdfReader

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "streetcore123")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = Groq(api_key=GROQ_API_KEY)
conn = sqlite3.connect("streetcore_v7.db", check_same_thread=False)
cursor = conn.cursor()

TABLES = [
"CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,email TEXT UNIQUE,password TEXT,role TEXT,plan TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,content TEXT,vector TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,task TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,agent TEXT,prompt TEXT,response TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,filename TEXT,content TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,platform TEXT,theme TEXT,content TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS videos(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,theme TEXT,script TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS workflows(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,steps TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS gallery(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,type TEXT,prompt TEXT,url TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS analytics(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,event TEXT,data TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS api_keys(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,token TEXT,created_at TEXT)"
]

for t in TABLES:
    cursor.execute(t)
conn.commit()

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
Você é StreetCore OS V7 — AI Company Operating System.
Responda sempre em português.
Use ferramentas gratuitas ou plano grátis como padrão.
Aja como CEO, estrategista, diretor criativo, engenheiro de IA, programador, vendedor,
copywriter, social media, analista de growth, automação e assistente operacional.
Explique passo a passo, como se estivesse fazendo pelo usuário.
Nunca execute ação sensível sem aprovação.
"""

AGENTS = {
    "ceo": "CEO Agent: estratégia, monetização, escala, priorização e negócios digitais.",
    "marketing": "Marketing Agent: branding, copy, viralização, funis, conteúdo e crescimento.",
    "dev": "Dev Agent: Python, APIs, SaaS, automação, banco, deploy e arquitetura.",
    "design": "Design Agent: direção criativa, cyberpunk premium, logos, imagens e identidade visual.",
    "video": "Video Agent: roteiros, cenas, prompts de vídeo, Reels, Shorts e anúncios.",
    "automation": "Automation Agent: workflows, processos, produtividade e sistemas automáticos.",
    "sales": "Sales Agent: oferta, vendas, objeções, WhatsApp, fechamento e monetização.",
    "finance": "Finance Agent: precificação, modelo de receita, planos, custos e lucro.",
    "ops": "Operations Agent: tarefas, processos, rotinas, sistemas e execução."
}

SENSITIVE = ["publicar", "postar agora", "enviar", "apagar", "deletar", "comprar", "pagar", "contratar", "cancelar", "transferir"]

def uid():
    return session.get("user_id", 1)

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
    vec = json.dumps(text_vector(content))
    cursor.execute("INSERT INTO memory(user_id,content,vector,created_at) VALUES(?,?,?,?)", (user_id, content, vec, now()))
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
    scored.sort(reverse=True, key=lambda x: x[0])
    return [x[1] for x in scored[:limit]]

def ask_ai(prompt, role="ceo", user_id=None):
    user_id = user_id or uid()
    memories = "\n".join(vector_search(prompt, user_id))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT + "\n\n" + AGENTS.get(role, "")},
            {"role": "system", "content": f"MEMÓRIA VETORIAL DO USUÁRIO:\n{memories}"},
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

def needs_approval(text):
    return any(x in text.lower() for x in SENSITIVE)

def image_url(prompt):
    return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"

def count_table(table):
    return cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id=?", (uid(),)).fetchone()[0]

def read_upload(filename, path):
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

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

# TELEGRAM

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore OS V7 online. Digite /menu")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE OS V7

/completo ideia
/ceo ideia
/marketing ideia
/dev ideia
/design ideia
/video ideia
/auto ideia
/sales ideia
/finance ideia
/ops ideia

/criar_empresa ideia
/criar_saas ideia
/criar_campanha ideia
/criar_funil ideia
/criar_marca ideia
/criar_produto ideia

/post instagram tema
/videoai tema
/workflow objetivo
/copiloto objetivo

/salvar memória
/memorias
/buscar termo

/tarefa texto
/tarefas
/concluir id

/imagem tema
/logo marca
/thumb tema

/status
/historico
/analytics
""")

async def status(update, context):
    text = "🚀 STREETCORE OS V7\n\n"
    for t in ["memory","tasks","history","files","posts","videos","workflows","approvals","gallery","analytics"]:
        total = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        text += f"{t}: {total}\n"
    await update.message.reply_text(text)

async def generic_agent(update, context, role):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Digite algo depois do comando.")
        return
    await send_long(update, ask_ai(prompt, role, 1))

async def completo(update, context):
    prompt = " ".join(context.args)
    final = ""
    for role in AGENTS:
        final += f"\n\n## {role.upper()}\n\n{ask_ai(prompt, role, 1)}"
    await send_long(update, final)

async def ceo(u,c): await generic_agent(u,c,"ceo")
async def marketing(u,c): await generic_agent(u,c,"marketing")
async def dev(u,c): await generic_agent(u,c,"dev")
async def design(u,c): await generic_agent(u,c,"design")
async def video_cmd(u,c): await generic_agent(u,c,"video")
async def auto(u,c): await generic_agent(u,c,"automation")
async def sales(u,c): await generic_agent(u,c,"sales")
async def finance(u,c): await generic_agent(u,c,"finance")
async def ops(u,c): await generic_agent(u,c,"ops")

async def command_creator(update, context, kind):
    idea = " ".join(context.args)
    prompts = {
        "empresa": "Crie uma empresa de IA completa com posicionamento, produto, público, monetização, operação, funil e plano de 30 dias.",
        "saas": "Crie um SaaS completo com MVP, funcionalidades, stack grátis, banco, dashboard, preço, landing page e roadmap.",
        "campanha": "Crie uma campanha completa com conceito, posts, vídeos, funil, CTA, calendário e execução.",
        "funil": "Crie um funil completo com tráfego, isca, landing, sequência, oferta, WhatsApp e automação.",
        "marca": "Crie uma marca completa com nome, manifesto, paleta, tom de voz, público, posicionamento e identidade.",
        "produto": "Crie um produto digital completo com promessa, módulos, bônus, preço, página e lançamento."
    }
    resp = ask_ai(prompts[kind] + "\n\nIdeia:\n" + idea, "ceo", 1)
    await send_long(update, resp)

async def criar_empresa(u,c): await command_creator(u,c,"empresa")
async def criar_saas(u,c): await command_creator(u,c,"saas")
async def criar_campanha(u,c): await command_creator(u,c,"campanha")
async def criar_funil(u,c): await command_creator(u,c,"funil")
async def criar_marca(u,c): await command_creator(u,c,"marca")
async def criar_produto(u,c): await command_creator(u,c,"produto")

async def tarefa(update, context):
    text = " ".join(context.args)
    cursor.execute("INSERT INTO tasks(user_id,task,status,created_at) VALUES(?,?,?,?)", (1, text, "pendente", now()))
    conn.commit()
    await update.message.reply_text("✅ tarefa salva")

async def tarefas(update, context):
    rows = cursor.execute("SELECT id,task,status FROM tasks ORDER BY id DESC LIMIT 50").fetchall()
    text = "🧠 TAREFAS\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[2]}\n"
    await send_long(update, text if rows else "Nenhuma tarefa.")

async def concluir(update, context):
    try:
        task_id = int(context.args[0])
        cursor.execute("UPDATE tasks SET status=? WHERE id=?", ("concluída", task_id))
        conn.commit()
        await update.message.reply_text("✅ concluída")
    except:
        await update.message.reply_text("Use: /concluir 1")

async def salvar(update, context):
    save_memory(" ".join(context.args), 1)
    await update.message.reply_text("🧠 memória salva")

async def memorias(update, context):
    rows = cursor.execute("SELECT id,content FROM memory ORDER BY id DESC LIMIT 20").fetchall()
    text = "🧠 MEMÓRIAS\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]}\n\n"
    await send_long(update, text if rows else "Sem memórias.")

async def buscar(update, context):
    q = " ".join(context.args)
    results = vector_search(q, 1, 8)
    text = f"🔎 BUSCA: {q}\n\n"
    for i, r in enumerate(results, 1):
        text += f"{i}. {r}\n\n"
    await send_long(update, text if results else "Nada encontrado.")

async def historico(update, context):
    rows = cursor.execute("SELECT id,agent,prompt FROM history ORDER BY id DESC LIMIT 20").fetchall()
    text = "📚 HISTÓRICO\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[2][:100]}\n\n"
    await send_long(update, text if rows else "Sem histórico.")

async def analytics(update, context):
    rows = cursor.execute("SELECT event,COUNT(*) FROM analytics GROUP BY event").fetchall()
    text = "📊 ANALYTICS\n\n"
    for r in rows:
        text += f"{r[0]}: {r[1]}\n"
    await send_long(update, text if rows else "Sem analytics.")

async def imagem(update, context):
    prompt = " ".join(context.args)
    url = image_url(f"ultra realistic cinematic cyberpunk premium 8k, {prompt}")
    cursor.execute("INSERT INTO gallery(user_id,type,prompt,url,created_at) VALUES(?,?,?,?,?)", (1, "imagem", prompt, url, now()))
    conn.commit()
    await update.message.reply_photo(photo=url)

async def logo(update, context):
    prompt = " ".join(context.args)
    url = image_url(f"minimal futuristic luxury logo, white background, clean vector, {prompt}")
    cursor.execute("INSERT INTO gallery(user_id,type,prompt,url,created_at) VALUES(?,?,?,?,?)", (1, "logo", prompt, url, now()))
    conn.commit()
    await update.message.reply_photo(photo=url)

async def thumb(update, context):
    prompt = " ".join(context.args)
    url = image_url(f"viral youtube thumbnail, cinematic, high CTR, premium futuristic, {prompt}")
    cursor.execute("INSERT INTO gallery(user_id,type,prompt,url,created_at) VALUES(?,?,?,?,?)", (1, "thumb", prompt, url, now()))
    conn.commit()
    await update.message.reply_photo(photo=url)

async def post(update, context):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Use: /post instagram tema")
        return
    platform = args[0]
    theme = " ".join(args[1:])
    content = ask_ai(f"Crie um post completo para {platform} sobre: {theme}. Inclua legenda, CTA, hashtags e ideia visual.", "marketing", 1)
    cursor.execute("INSERT INTO posts(user_id,platform,theme,content,status,created_at) VALUES(?,?,?,?,?,?)", (1, platform, theme, content, "rascunho", now()))
    conn.commit()
    await send_long(update, content)

async def videoai(update, context):
    theme = " ".join(context.args)
    script = ask_ai(f"Crie um vídeo IA completo sobre: {theme}. Inclua roteiro, cenas, prompts, narração e edição.", "video", 1)
    cursor.execute("INSERT INTO videos(user_id,theme,script,status,created_at) VALUES(?,?,?,?,?)", (1, theme, script, "roteiro", now()))
    conn.commit()
    await send_long(update, script)

async def workflow(update, context):
    text = " ".join(context.args)
    steps = ask_ai(f"Crie um workflow automático gratuito para: {text}. Inclua etapas, ferramentas grátis, gatilhos e execução.", "automation", 1)
    cursor.execute("INSERT INTO workflows(user_id,name,steps,status,created_at) VALUES(?,?,?,?,?)", (1, text, steps, "ativo", now()))
    conn.commit()
    await send_long(update, steps)

async def copiloto(update, context):
    goal = " ".join(context.args)
    response = ask_ai(f"Atue como copiloto operacional IA para: {goal}. Crie diagnóstico, plano, tarefas, automações e próximos passos.", "automation", 1)
    await send_long(update, response)

async def normal_chat(update, context):
    text = update.message.text
    if needs_approval(text):
        cursor.execute("INSERT INTO approvals(user_id,action,status,created_at) VALUES(?,?,?,?)", (1, text, "pendente", now()))
        conn.commit()
        await update.message.reply_text("🛡 Ação sensível salva para aprovação.")
        return
    await send_long(update, ask_ai(text, "ceo", 1))

# WEB

web = Flask(__name__)
web.secret_key = os.getenv("FLASK_SECRET", "streetcore-v7-" + secrets.token_hex(8))

CSS = """
<style>
*{box-sizing:border-box;font-family:Arial}body{margin:0;background:#050510;color:white;min-height:100vh}
a{text-decoration:none;color:white}.app{display:flex;min-height:100vh}
.sidebar{width:270px;background:#0d0d18;padding:20px;border-right:1px solid #222}
.logo{font-size:25px;font-weight:bold;color:#a855f7;margin-bottom:8px}.status{font-size:12px;opacity:.7;margin-bottom:20px}
.nav a{display:block;padding:13px;background:#151525;margin-bottom:10px;border-radius:12px}.nav a:hover{background:#222240}
.main{flex:1}.top{height:64px;background:#0d0d18;border-bottom:1px solid #222;display:flex;align-items:center;justify-content:space-between;padding:0 20px}
.content{padding:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.card{background:#111827;border:1px solid #333;border-radius:18px;padding:18px}.big{font-size:34px;font-weight:bold;color:#a855f7}
.chat{height:calc(100vh - 220px);overflow:auto;display:flex;flex-direction:column;gap:14px;padding:15px}
.msg{padding:15px;border-radius:16px;white-space:pre-wrap;line-height:1.5;max-width:900px}.ai{background:#111827;border:1px solid #333}.user{background:#1f1f35;align-self:flex-end}
.bottom{padding:14px;background:#0d0d18;border-top:1px solid #222;display:flex;flex-direction:column;gap:10px}.row{display:flex;gap:10px}
input,select,textarea{width:100%;padding:14px;border:0;border-radius:12px;background:#151525;color:white}
button{padding:14px 18px;border:0;border-radius:12px;background:#9333ea;color:white;font-weight:bold;cursor:pointer}.upload{background:#2563eb}
table{width:100%;border-collapse:collapse;background:#111827;border-radius:12px;overflow:hidden}td,th{padding:12px;border-bottom:1px solid #333;text-align:left;vertical-align:top}
.login{max-width:440px;margin:80px auto;background:#111827;padding:30px;border-radius:20px;border:1px solid #333}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px}.gallery img{width:100%;border-radius:16px;border:1px solid #333}
@media(max-width:850px){.app{flex-direction:column}.sidebar{width:100%}.row{flex-direction:column}.chat{height:55vh}}
</style>
"""

def logged():
    return session.get("user_id")

def current_user():
    if not logged(): return None
    return cursor.execute("SELECT id,name,email,role,plan FROM users WHERE id=?", (session["user_id"],)).fetchone()

def require_login():
    return bool(logged())

def layout(title, body):
    user = current_user()
    name = user[1] if user else "Usuário"
    return f"""
<!doctype html><html><head><title>{title}</title><meta name="viewport" content="width=device-width, initial-scale=1">{CSS}</head>
<body><div class="app"><div class="sidebar">
<div class="logo">🔥 StreetCore OS</div><div class="status">V7 AI COMPANY OS • {name}</div>
<div class="nav">
<a href="/">Dashboard</a><a href="/chat">Chat IA</a><a href="/command">Command Center</a><a href="/posts">Posts</a><a href="/videos">Vídeos</a>
<a href="/workflows">Workflows</a><a href="/memory">Memória</a><a href="/files">Arquivos</a><a href="/gallery">Galeria</a>
<a href="/analytics-page">Analytics</a><a href="/api-keys">API Keys</a><a href="/billing">Stripe Ready</a><a href="/logout">Sair</a>
</div></div><div class="main"><div class="top"><b>{title}</b><span>StreetCore OS V7</span></div><div class="content">{body}</div></div></div></body></html>
"""

@web.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))
        try:
            cursor.execute("INSERT INTO users(name,email,password,role,plan,created_at) VALUES(?,?,?,?,?,?)", (name,email,password,"user","free",now()))
            conn.commit()
            return redirect("/login")
        except:
            pass
    return f"""<!doctype html><html><head><title>Cadastro</title>{CSS}</head><body><div class="login">
<h1>🔥 StreetCore OS</h1><p>Criar conta</p><form method="POST">
<input name="name" placeholder="Nome"><br><br><input name="email" placeholder="Email"><br><br><input name="password" type="password" placeholder="Senha"><br><br>
<button>Cadastrar</button></form><p><a href="/login">Entrar</a></p></div></body></html>"""

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
<h1>🔥 StreetCore OS V7</h1><p>Login SaaS</p><form method="POST">
<input name="email" placeholder="Email" value="admin@streetcore.ai"><br><br><input name="password" type="password" placeholder="Senha"><br><br>
<button>Entrar</button></form><p>Senha admin padrão: streetcore123</p><p><a href="/register">Criar conta</a></p></div></body></html>"""

@web.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@web.route("/")
def dashboard():
    if not require_login(): return redirect("/login")
    cards = ""
    for t in ["memory","tasks","history","files","posts","videos","workflows","approvals","gallery","analytics"]:
        cards += f"<div class='card'><h3>{t}</h3><div class='big'>{count_table(t)}</div></div>"
    return layout("Dashboard Executivo", f"<div class='grid'>{cards}</div>")

@web.route("/chat")
def chat_page():
    if not require_login(): return redirect("/login")
    return layout("Chat IA", """
<div class="card"><div class="chat" id="chat"><div class="msg ai">🔥 StreetCore OS V7 online. Escolha um agente e envie sua ideia.</div></div>
<div class="bottom"><div class="row"><select id="agent">
<option value="ceo">CEO</option><option value="marketing">Marketing</option><option value="dev">Dev</option><option value="design">Design</option>
<option value="video">Video</option><option value="automation">Automation</option><option value="sales">Sales</option><option value="finance">Finance</option><option value="ops">Ops</option>
</select><input id="prompt" placeholder="Digite sua ideia..."><button onclick="sendMessage()">Enviar</button></div>
<div class="row"><input type="file" id="file"><button class="upload" onclick="uploadFile()">Upload IA</button></div></div></div>
<script>
function add(cls,text){document.getElementById('chat').innerHTML+=`<div class="msg ${cls}">${text}</div>`;document.getElementById('chat').scrollTop=999999}
async function sendMessage(){const text=document.getElementById('prompt').value;const agent=document.getElementById('agent').value;if(!text)return;add('user',text);document.getElementById('prompt').value='';const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:text,agent:agent})});const d=await r.json();add('ai',d.response)}
async function uploadFile(){const f=document.getElementById('file').files[0];if(!f){alert('Escolha um arquivo');return}const fd=new FormData();fd.append('file',f);const r=await fetch('/upload',{method:'POST',body:fd});const d=await r.json();add('ai',d.response)}
</script>
""")

@web.route("/command")
def command_page():
    if not require_login(): return redirect("/login")
    return layout("AI Command Center", """
<div class="grid">
<div class="card"><h3>Criar Empresa IA</h3><button onclick="cmd('empresa')">Executar</button></div>
<div class="card"><h3>Criar SaaS</h3><button onclick="cmd('saas')">Executar</button></div>
<div class="card"><h3>Criar Campanha</h3><button onclick="cmd('campanha')">Executar</button></div>
<div class="card"><h3>Criar Funil</h3><button onclick="cmd('funil')">Executar</button></div>
<div class="card"><h3>Criar Marca</h3><button onclick="cmd('marca')">Executar</button></div>
<div class="card"><h3>Criar Produto</h3><button onclick="cmd('produto')">Executar</button></div>
</div><br><div class="card"><input id="idea" placeholder="Digite sua ideia base..."><br><br><div id="out" class="msg ai">Resultado aparecerá aqui.</div></div>
<script>
async function cmd(type){const idea=document.getElementById('idea').value||'negócio de IA';document.getElementById('out').innerText='Gerando...';const r=await fetch('/command-api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type:type,idea:idea})});const d=await r.json();document.getElementById('out').innerText=d.response}
</script>
""")

def table_page(title, table, columns):
    if not require_login(): return redirect("/login")
    rows = cursor.execute(f"SELECT {','.join(columns)} FROM {table} WHERE user_id=? ORDER BY id DESC LIMIT 100", (uid(),)).fetchall()
    head = "".join([f"<th>{c}</th>" for c in columns])
    body = ""
    for r in rows:
        body += "<tr>" + "".join([f"<td>{str(x)[:500]}</td>" for x in r]) + "</tr>"
    return layout(title, f"<div class='card'><table><tr>{head}</tr>{body}</table></div>")

@web.route("/posts")
def posts_page(): return table_page("Posts", "posts", ["id","platform","theme","status","created_at"])
@web.route("/videos")
def videos_page(): return table_page("Vídeos", "videos", ["id","theme","status","created_at"])
@web.route("/workflows")
def workflows_page(): return table_page("Workflows", "workflows", ["id","name","status","created_at"])
@web.route("/memory")
def memory_page(): return table_page("Memória", "memory", ["id","content","created_at"])
@web.route("/files")
def files_page(): return table_page("Arquivos", "files", ["id","filename","created_at"])
@web.route("/analytics-page")
def analytics_page(): return table_page("Analytics", "analytics", ["id","event","data","created_at"])

@web.route("/gallery")
def gallery_page():
    if not require_login(): return redirect("/login")
    rows = cursor.execute("SELECT type,prompt,url FROM gallery WHERE user_id=? ORDER BY id DESC LIMIT 60", (uid(),)).fetchall()
    html = "<div class='gallery'>"
    for r in rows:
        html += f"<div class='card'><img src='{r[2]}'><h3>{r[0]}</h3><p>{r[1]}</p></div>"
    html += "</div>"
    return layout("Galeria IA", html)

@web.route("/api-keys")
def api_keys():
    if not require_login(): return redirect("/login")
    token = secrets.token_hex(24)
    cursor.execute("INSERT INTO api_keys(user_id,token,created_at) VALUES(?,?,?)", (uid(), token, now()))
    conn.commit()
    return layout("API System", f"<div class='card'><h2>Token API gerado</h2><p>{token}</p><p>Estrutura pronta para integrações futuras.</p></div>")

@web.route("/billing")
def billing():
    if not require_login(): return redirect("/login")
    return layout("Stripe Ready", "<div class='card'><h2>Stripe Ready</h2><p>Estrutura SaaS preparada para planos Free, Pro e Agency. Nenhuma cobrança automática foi ativada.</p></div>")

@web.route("/ask", methods=["POST"])
def ask_web():
    if not require_login(): return jsonify({"response":"Login necessário."})
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
    if not require_login(): return jsonify({"response":"Login necessário."})
    data = request.get_json()
    kind = data.get("type")
    idea = data.get("idea")
    prompts = {
        "empresa":"Crie uma empresa de IA completa.",
        "saas":"Crie um SaaS completo.",
        "campanha":"Crie uma campanha completa.",
        "funil":"Crie um funil completo.",
        "marca":"Crie uma marca completa.",
        "produto":"Crie um produto digital completo."
    }
    return jsonify({"response":ask_ai(prompts.get(kind,"Crie um plano completo.") + "\n\nIdeia:\n" + idea, "ceo", uid())})

@web.route("/upload", methods=["POST"])
def upload():
    if not require_login(): return jsonify({"response":"Login necessário."})
    file = request.files.get("file")
    if not file: return jsonify({"response":"Nenhum arquivo."})
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    content = read_upload(filename, path)
    cursor.execute("INSERT INTO files(user_id,filename,content,created_at) VALUES(?,?,?,?)", (uid(), filename, content[:60000], now()))
    conn.commit()
    save_memory(f"Arquivo {filename}: {content[:3000]}", uid())
    analysis = ask_ai(f"Analise profundamente este arquivo: {filename}\n\n{content[:14000]}\n\nEntregue resumo, insights, riscos, oportunidades e plano de ação.", "ceo", uid())
    return jsonify({"response":analysis})

@web.route("/health")
def health():
    return "OK STREETCORE V7 ONLINE", 200

def run_telegram():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    handlers = {
        "start":start,"menu":menu,"status":status,
        "completo":completo,"ceo":ceo,"marketing":marketing,"dev":dev,"design":design,"video":video_cmd,"auto":auto,"sales":sales,"finance":finance,"ops":ops,
        "criar_empresa":criar_empresa,"criar_saas":criar_saas,"criar_campanha":criar_campanha,"criar_funil":criar_funil,"criar_marca":criar_marca,"criar_produto":criar_produto,
        "tarefa":tarefa,"tarefas":tarefas,"concluir":concluir,
        "salvar":salvar,"memorias":memorias,"buscar":buscar,"historico":historico,"analytics":analytics,
        "imagem":imagem,"logo":logo,"thumb":thumb,
        "post":post,"videoai":videoai,"workflow":workflow,"copiloto":copiloto
    }
    for name, func in handlers.items():
        app.add_handler(CommandHandler(name, func))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, normal_chat))
    app.run_polling(stop_signals=None)

threading.Thread(target=run_telegram, daemon=True).start()

print("🔥 STREETCORE OS V7 AI COMPANY OPERATING SYSTEM ONLINE")
web.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))