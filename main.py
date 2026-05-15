import os, sqlite3, urllib.parse, threading, math, json
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, session
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

conn = sqlite3.connect("streetcore.db", check_same_thread=False)
cursor = conn.cursor()

for sql in [
    "CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS vectors(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, vector TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, status TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, prompt TEXT, response TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, content TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, theme TEXT, content TEXT, status TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS videos(id INTEGER PRIMARY KEY AUTOINCREMENT, theme TEXT, script TEXT, status TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS workflows(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, steps TEXT, status TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, status TEXT, created_at TEXT)",
    "CREATE TABLE IF NOT EXISTS analytics(id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, data TEXT, created_at TEXT)"
]:
    cursor.execute(sql)

conn.commit()

MASTER_PROMPT = """
Você é StreetCore OS V6.
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
    "dev": "Dev Agent: Python, APIs, SaaS, automação, banco de dados, deploy e arquitetura.",
    "design": "Design Agent: direção criativa, cyberpunk premium, logos, imagens e identidade visual.",
    "video": "Video Agent: roteiros, cenas, prompts de vídeo, Reels, Shorts e anúncios.",
    "automation": "Automation Agent: workflows, processos, produtividade e sistemas automáticos.",
    "sales": "Sales Agent: oferta, vendas, objeções, WhatsApp, fechamento e monetização."
}

SENSITIVE = ["publicar", "postar agora", "enviar", "apagar", "deletar", "comprar", "pagar", "contratar", "cancelar", "transferir"]

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_event(event, data=""):
    cursor.execute("INSERT INTO analytics(event,data,created_at) VALUES(?,?,?)", (event, data, now()))
    conn.commit()

def text_vector(text, size=96):
    vec = [0.0] * size
    for w in text.lower().split():
        vec[hash(w) % size] += 1.0
    norm = math.sqrt(sum(x*x for x in vec)) or 1
    return [x / norm for x in vec]

def cosine(a, b):
    return sum(x*y for x, y in zip(a, b))

def save_vector_memory(content):
    vec = text_vector(content)
    cursor.execute("INSERT INTO memory(content,created_at) VALUES(?,?)", (content, now()))
    cursor.execute("INSERT INTO vectors(content,vector,created_at) VALUES(?,?,?)", (content, json.dumps(vec), now()))
    conn.commit()

def vector_search(query, limit=6):
    qv = text_vector(query)
    rows = cursor.execute("SELECT content, vector FROM vectors").fetchall()
    scored = []
    for content, vec_json in rows:
        try:
            scored.append((cosine(qv, json.loads(vec_json)), content))
        except:
            pass
    scored.sort(reverse=True, key=lambda x: x[0])
    return [x[1] for x in scored[:limit]]

def ask_ai(prompt, role="ceo"):
    memories = "\n".join(vector_search(prompt))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT + "\n\n" + AGENTS.get(role, "")},
            {"role": "system", "content": f"MEMÓRIA VETORIAL:\n{memories}"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=3500
    )
    result = response.choices[0].message.content
    cursor.execute("INSERT INTO history(agent,prompt,response,created_at) VALUES(?,?,?,?)", (role, prompt, result, now()))
    conn.commit()
    log_event("ai_response", role)
    return result

def image_url(prompt):
    return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"

def needs_approval(text):
    return any(x in text.lower() for x in SENSITIVE)

def count_table(table):
    return cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

def read_upload(filename, path):
    content = ""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(path)
        for page in reader.pages:
            try:
                content += page.extract_text() + "\n"
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
    await update.message.reply_text("🔥 StreetCore OS V6 online. Digite /menu")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE OS V6

IA:
/completo ideia
/ceo ideia
/marketing ideia
/dev ideia
/design ideia
/video ideia
/auto ideia
/sales ideia

CONTEÚDO:
/post instagram tema
/videoai tema
/workflow objetivo
/copiloto objetivo

MEMÓRIA:
/salvar memória
/memorias
/buscar termo

TAREFAS:
/tarefa texto
/tarefas
/concluir id

IMAGEM:
/imagem tema
/logo marca
/thumb tema

SISTEMA:
/status
/historico
/analytics
""")

async def status(update, context):
    text = "🚀 STATUS STREETCORE V6\n\n"
    for t in ["memory", "vectors", "tasks", "history", "files", "posts", "videos", "workflows", "approvals", "analytics"]:
        text += f"{t}: {count_table(t)}\n"
    await update.message.reply_text(text)

async def generic_agent(update, context, role):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Digite algo depois do comando.")
        return
    await send_long(update, ask_ai(prompt, role))

async def completo(update, context):
    prompt = " ".join(context.args)
    final = ""
    for role in AGENTS:
        final += f"\n\n## {role.upper()}\n\n{ask_ai(prompt, role)}"
    await send_long(update, final)

async def ceo(update, context): await generic_agent(update, context, "ceo")
async def marketing(update, context): await generic_agent(update, context, "marketing")
async def dev(update, context): await generic_agent(update, context, "dev")
async def design(update, context): await generic_agent(update, context, "design")
async def video_cmd(update, context): await generic_agent(update, context, "video")
async def auto(update, context): await generic_agent(update, context, "automation")
async def sales(update, context): await generic_agent(update, context, "sales")

async def tarefa(update, context):
    text = " ".join(context.args)
    cursor.execute("INSERT INTO tasks(task,status,created_at) VALUES(?,?,?)", (text, "pendente", now()))
    conn.commit()
    await update.message.reply_text("✅ tarefa salva")

async def tarefas(update, context):
    rows = cursor.execute("SELECT id, task, status FROM tasks ORDER BY id DESC LIMIT 50").fetchall()
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
    text = " ".join(context.args)
    save_vector_memory(text)
    await update.message.reply_text("🧠 memória salva")

async def memorias(update, context):
    rows = cursor.execute("SELECT id, content FROM memory ORDER BY id DESC LIMIT 20").fetchall()
    text = "🧠 MEMÓRIAS\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]}\n\n"
    await send_long(update, text if rows else "Sem memórias.")

async def buscar(update, context):
    q = " ".join(context.args)
    results = vector_search(q, 8)
    text = f"🔎 BUSCA: {q}\n\n"
    for i, r in enumerate(results, 1):
        text += f"{i}. {r}\n\n"
    await send_long(update, text if results else "Nada encontrado.")

async def historico(update, context):
    rows = cursor.execute("SELECT id, agent, prompt FROM history ORDER BY id DESC LIMIT 20").fetchall()
    text = "📚 HISTÓRICO\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[2][:100]}\n\n"
    await send_long(update, text if rows else "Sem histórico.")

async def analytics(update, context):
    rows = cursor.execute("SELECT event, COUNT(*) FROM analytics GROUP BY event").fetchall()
    text = "📊 ANALYTICS\n\n"
    for r in rows:
        text += f"{r[0]}: {r[1]}\n"
    await send_long(update, text if rows else "Sem analytics.")

async def imagem(update, context):
    prompt = " ".join(context.args)
    await update.message.reply_photo(photo=image_url(f"ultra realistic cinematic cyberpunk premium 8k, {prompt}"))

async def logo(update, context):
    prompt = " ".join(context.args)
    await update.message.reply_photo(photo=image_url(f"minimal futuristic luxury logo, white background, clean vector, {prompt}"))

async def thumb(update, context):
    prompt = " ".join(context.args)
    await update.message.reply_photo(photo=image_url(f"viral youtube thumbnail, cinematic, high CTR, premium futuristic, {prompt}"))

async def post(update, context):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Use: /post instagram tema")
        return
    platform = args[0]
    theme = " ".join(args[1:])
    content = ask_ai(f"Crie um post completo para {platform} sobre: {theme}. Inclua legenda, CTA, hashtags e ideia visual.", "marketing")
    cursor.execute("INSERT INTO posts(platform,theme,content,status,created_at) VALUES(?,?,?,?,?)", (platform, theme, content, "rascunho", now()))
    conn.commit()
    await send_long(update, content)

async def videoai(update, context):
    theme = " ".join(context.args)
    script = ask_ai(f"Crie um vídeo IA completo sobre: {theme}. Inclua roteiro, cenas, prompts, narração e edição.", "video")
    cursor.execute("INSERT INTO videos(theme,script,status,created_at) VALUES(?,?,?,?)", (theme, script, "roteiro", now()))
    conn.commit()
    await send_long(update, script)

async def workflow(update, context):
    text = " ".join(context.args)
    steps = ask_ai(f"Crie um workflow automático gratuito para: {text}. Inclua etapas, ferramentas grátis, gatilhos e execução.", "automation")
    cursor.execute("INSERT INTO workflows(name,steps,status,created_at) VALUES(?,?,?,?)", (text, steps, "ativo", now()))
    conn.commit()
    await send_long(update, steps)

async def copiloto(update, context):
    goal = " ".join(context.args)
    response = ask_ai(f"Atue como copiloto operacional IA para: {goal}. Crie diagnóstico, plano, tarefas, automações e próximos passos.", "automation")
    await send_long(update, response)

async def normal_chat(update, context):
    text = update.message.text
    if needs_approval(text):
        cursor.execute("INSERT INTO approvals(action,status,created_at) VALUES(?,?,?)", (text, "pendente", now()))
        conn.commit()
        await update.message.reply_text("🛡 Ação sensível salva para aprovação.")
        return
    await send_long(update, ask_ai(text))

# WEB

web = Flask(__name__)
web.secret_key = "streetcore-v6-secret"

BASE_CSS = """
<style>
*{box-sizing:border-box;font-family:Arial}
body{margin:0;background:#050510;color:white;min-height:100vh}
a{text-decoration:none;color:white}
.app{display:flex;min-height:100vh}
.sidebar{width:260px;background:#0d0d18;padding:20px;border-right:1px solid #222}
.logo{font-size:25px;font-weight:bold;color:#a855f7;margin-bottom:10px}
.status{font-size:12px;opacity:.7;margin-bottom:20px}
.nav a{display:block;padding:13px;background:#151525;margin-bottom:10px;border-radius:12px}
.nav a:hover{background:#222240}
.main{flex:1;display:flex;flex-direction:column}
.top{height:64px;background:#0d0d18;border-bottom:1px solid #222;display:flex;align-items:center;justify-content:space-between;padding:0 20px}
.content{padding:22px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}
.card{background:#111827;border:1px solid #333;border-radius:18px;padding:18px}
.big{font-size:34px;font-weight:bold;color:#a855f7}
.chat{height:calc(100vh - 210px);overflow:auto;display:flex;flex-direction:column;gap:14px;padding:15px}
.msg{padding:15px;border-radius:16px;white-space:pre-wrap;line-height:1.5;max-width:900px}
.ai{background:#111827;border:1px solid #333}
.user{background:#1f1f35;align-self:flex-end}
.bottom{padding:14px;background:#0d0d18;border-top:1px solid #222;display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:10px}
input,select,textarea{width:100%;padding:14px;border:0;border-radius:12px;background:#151525;color:white}
button{padding:14px 18px;border:0;border-radius:12px;background:#9333ea;color:white;font-weight:bold;cursor:pointer}
.upload{background:#2563eb}
table{width:100%;border-collapse:collapse;background:#111827;border-radius:12px;overflow:hidden}
td,th{padding:12px;border-bottom:1px solid #333;text-align:left}
.login{max-width:420px;margin:100px auto;background:#111827;padding:30px;border-radius:20px;border:1px solid #333}
@media(max-width:800px){.app{flex-direction:column}.sidebar{width:100%}.row{flex-direction:column}.chat{height:55vh}}
</style>
"""

def require_login():
    return session.get("logged") == True

def layout(title, body):
    return f"""
<!doctype html>
<html>
<head>
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{BASE_CSS}
</head>
<body>
<div class="app">
<div class="sidebar">
<div class="logo">🔥 StreetCore OS</div>
<div class="status">V6 SAAS PANEL • ONLINE</div>
<div class="nav">
<a href="/">Dashboard</a>
<a href="/chat">Chat IA</a>
<a href="/posts">Posts</a>
<a href="/videos">Vídeos</a>
<a href="/workflows">Workflows</a>
<a href="/memory">Memória</a>
<a href="/files">Arquivos</a>
<a href="/analytics-page">Analytics</a>
<a href="/logout">Sair</a>
</div>
</div>
<div class="main">
<div class="top"><b>{title}</b><span>StreetCore OS V6</span></div>
<div class="content">{body}</div>
</div>
</div>
</body>
</html>
"""

@web.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["logged"] = True
            return redirect("/")
    return f"""
<!doctype html>
<html>
<head><title>Login</title><meta name="viewport" content="width=device-width, initial-scale=1">{BASE_CSS}</head>
<body>
<div class="login">
<h1>🔥 StreetCore OS</h1>
<p>Login administrativo</p>
<form method="POST">
<input name="password" type="password" placeholder="Senha">
<br><br>
<button>Entrar</button>
</form>
<p style="opacity:.6">Senha padrão: streetcore123</p>
</div>
</body>
</html>
"""

@web.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@web.route("/")
def dashboard():
    if not require_login(): return redirect("/login")
    cards = ""
    for t in ["memory", "tasks", "history", "files", "posts", "videos", "workflows", "approvals", "analytics"]:
        cards += f"<div class='card'><h3>{t}</h3><div class='big'>{count_table(t)}</div></div>"
    return layout("Dashboard", f"<div class='grid'>{cards}</div>")

@web.route("/chat")
def chat_page():
    if not require_login(): return redirect("/login")
    return layout("Chat IA", """
<div class="card">
<div class="chat" id="chat"><div class="msg ai">🔥 StreetCore OS V6 online. Escolha um agente e envie sua ideia.</div></div>
<div class="bottom">
<div class="row">
<select id="agent">
<option value="ceo">CEO</option><option value="marketing">Marketing</option><option value="dev">Dev</option>
<option value="design">Design</option><option value="video">Video</option><option value="automation">Automation</option><option value="sales">Sales</option>
</select>
<input id="prompt" placeholder="Digite sua ideia...">
<button onclick="sendMessage()">Enviar</button>
</div>
<div class="row">
<input type="file" id="file">
<button class="upload" onclick="uploadFile()">Upload IA</button>
</div>
</div>
</div>
<script>
function add(cls,text){document.getElementById('chat').innerHTML+=`<div class="msg ${cls}">${text}</div>`;document.getElementById('chat').scrollTop=999999}
async function sendMessage(){
const text=document.getElementById('prompt').value;const agent=document.getElementById('agent').value;if(!text)return;
add('user',text);document.getElementById('prompt').value='';
const r=await fetch('/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:text,agent:agent})});
const d=await r.json();add('ai',d.response)}
async function uploadFile(){
const f=document.getElementById('file').files[0];if(!f){alert('Escolha um arquivo');return}
const fd=new FormData();fd.append('file',f);
const r=await fetch('/upload',{method:'POST',body:fd});const d=await r.json();add('ai',d.response)}
</script>
""")

def table_page(title, table, columns):
    if not require_login(): return redirect("/login")
    rows = cursor.execute(f"SELECT {','.join(columns)} FROM {table} ORDER BY id DESC LIMIT 100").fetchall()
    head = "".join([f"<th>{c}</th>" for c in columns])
    body = ""
    for r in rows:
        body += "<tr>" + "".join([f"<td>{str(x)[:500]}</td>" for x in r]) + "</tr>"
    return layout(title, f"<div class='card'><table><tr>{head}</tr>{body}</table></div>")

@web.route("/posts")
def posts_page(): return table_page("Posts", "posts", ["id", "platform", "theme", "status", "created_at"])

@web.route("/videos")
def videos_page(): return table_page("Vídeos", "videos", ["id", "theme", "status", "created_at"])

@web.route("/workflows")
def workflows_page(): return table_page("Workflows", "workflows", ["id", "name", "status", "created_at"])

@web.route("/memory")
def memory_page(): return table_page("Memória", "memory", ["id", "content", "created_at"])

@web.route("/files")
def files_page(): return table_page("Arquivos", "files", ["id", "filename", "created_at"])

@web.route("/analytics-page")
def analytics_page(): return table_page("Analytics", "analytics", ["id", "event", "data", "created_at"])

@web.route("/health")
def health():
    return "OK STREETCORE V6 ONLINE", 200

@web.route("/ask", methods=["POST"])
def ask_web():
    if not require_login(): return jsonify({"response": "Login necessário."})
    data = request.get_json()
    prompt = data.get("prompt", "")
    agent = data.get("agent", "ceo")
    if needs_approval(prompt):
        cursor.execute("INSERT INTO approvals(action,status,created_at) VALUES(?,?,?)", (prompt, "pendente", now()))
        conn.commit()
        return jsonify({"response": "🛡 Ação sensível criada para aprovação."})
    return jsonify({"response": ask_ai(prompt, agent)})

@web.route("/upload", methods=["POST"])
def upload():
    if not require_login(): return jsonify({"response": "Login necessário."})
    if "file" not in request.files:
        return jsonify({"response": "Nenhum arquivo."})
    file = request.files["file"]
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    content = read_upload(filename, path)
    cursor.execute("INSERT INTO files(filename,content,created_at) VALUES(?,?,?)", (filename, content[:60000], now()))
    conn.commit()
    save_vector_memory(f"Arquivo {filename}: {content[:3000]}")

    analysis = ask_ai(f"Analise profundamente este arquivo: {filename}\n\n{content[:14000]}\n\nEntregue resumo, insights, riscos, oportunidades e plano de ação.", "ceo")
    return jsonify({"response": analysis})

@web.route("/api/status")
def api_status():
    data = {}
    for table in ["memory", "vectors", "tasks", "history", "files", "posts", "videos", "workflows", "approvals", "analytics"]:
        data[table] = count_table(table)
    return jsonify(data)

def run_telegram():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    handlers = {
        "start": start, "menu": menu, "status": status,
        "completo": completo, "ceo": ceo, "marketing": marketing, "dev": dev,
        "design": design, "video": video_cmd, "auto": auto, "sales": sales,
        "tarefa": tarefa, "tarefas": tarefas, "concluir": concluir,
        "salvar": salvar, "memorias": memorias, "buscar": buscar,
        "historico": historico, "analytics": analytics,
        "imagem": imagem, "logo": logo, "thumb": thumb,
        "post": post, "videoai": videoai,
        "workflow": workflow, "copiloto": copiloto
    }

    for name, func in handlers.items():
        app.add_handler(CommandHandler(name, func))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, normal_chat))
    app.run_polling(stop_signals=None)

threading.Thread(target=run_telegram, daemon=True).start()

print("🔥 STREETCORE OS V6 SAAS PANEL ONLINE")
web.run(host="0.0.0.0", port=PORT)