import os, sqlite3, urllib.parse, threading, math, json
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, url_for, session
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

tables = [
"""CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, role TEXT)""",
"""CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS vectors(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, vector TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, prompt TEXT, response TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, content TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, theme TEXT, content TEXT, status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS videos(id INTEGER PRIMARY KEY AUTOINCREMENT, theme TEXT, script TEXT, status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS workflows(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, steps TEXT, status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, status TEXT, created_at TEXT)""",
"""CREATE TABLE IF NOT EXISTS analytics(id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, data TEXT, created_at TEXT)"""
]

for t in tables:
    cursor.execute(t)
conn.commit()

MASTER_PROMPT = """
Você é StreetCore OS GOD MODE.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis como padrão.
Aja como CEO, estrategista, diretor criativo, engenheiro de IA, programador,
copywriter, social media, vendedor, analista de growth, automação e assistente operacional.
Explique passo a passo, como se estivesse fazendo pelo usuário.
Nunca execute ação sensível sem aprovação.
"""

AGENTS = {
    "ceo": "CEO Agent: estratégia, monetização, escala, priorização e negócios digitais.",
    "marketing": "Marketing Agent: branding, copy, viralização, funis, conteúdo e crescimento.",
    "dev": "Dev Agent: Python, APIs, SaaS, automação, banco de dados, deploy e arquitetura.",
    "design": "Design Agent: direção criativa, cyberpunk premium, logos, imagens e identidade visual.",
    "video": "Video Agent: roteiros, cenas, prompts de vídeo, Reels, Shorts, anúncios.",
    "automation": "Automation Agent: workflows, processos, produtividade e sistemas automáticos.",
    "sales": "Sales Agent: oferta, vendas, objeções, WhatsApp, fechamento e monetização."
}

SENSITIVE = ["publicar", "postar agora", "enviar", "apagar", "deletar", "comprar", "pagar", "contratar", "cancelar", "transferir"]

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_event(event, data=""):
    cursor.execute("INSERT INTO analytics(event,data,created_at) VALUES(?,?,?)", (event, data, now()))
    conn.commit()

def chunk_send_text(text, limit=3900):
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def text_vector(text, size=96):
    vec = [0.0] * size
    words = text.lower().split()
    for w in words:
        idx = hash(w) % size
        vec[idx] += 1.0
    norm = math.sqrt(sum(x*x for x in vec)) or 1
    return [x / norm for x in vec]

def cosine(a, b):
    return sum(x*y for x, y in zip(a, b))

def save_vector_memory(content):
    vec = text_vector(content)
    cursor.execute("INSERT INTO memory(content,created_at) VALUES(?,?)", (content, now()))
    cursor.execute("INSERT INTO vectors(content,vector,created_at) VALUES(?,?,?)", (content, json.dumps(vec), now()))
    conn.commit()

def vector_search(query, limit=5):
    qv = text_vector(query)
    rows = cursor.execute("SELECT content, vector FROM vectors").fetchall()
    scored = []
    for content, vec_json in rows:
        try:
            v = json.loads(vec_json)
            scored.append((cosine(qv, v), content))
        except:
            pass
    scored.sort(reverse=True, key=lambda x: x[0])
    return [x[1] for x in scored[:limit]]

def ask_ai(prompt, role="ceo"):
    memories = vector_search(prompt, 6)
    memory_text = "\n".join(memories)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT + "\n\n" + AGENTS.get(role, "")},
            {"role": "system", "content": f"MEMÓRIA VETORIAL:\n{memory_text}"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=4000
    )

    result = response.choices[0].message.content
    cursor.execute("INSERT INTO history(agent,prompt,response,created_at) VALUES(?,?,?,?)", (role, prompt, result, now()))
    conn.commit()
    log_event("ai_response", role)
    return result

def image_url(prompt):
    return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}"

def read_file(path):
    content = ""
    if path.lower().endswith(".pdf"):
        reader = PdfReader(path)
        for page in reader.pages:
            try:
                content += page.extract_text() + "\n"
            except:
                pass
    elif path.lower().endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    return content[:60000]

def needs_approval(text):
    return any(x in text.lower() for x in SENSITIVE)

async def send_long(update, text):
    for part in chunk_send_text(text):
        await update.message.reply_text(part)

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore OS V5 GOD MODE online. Digite /menu")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE OS V5 GOD MODE

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
/posts
/videoai tema
/videos

AUTOMAÇÃO:
/workflow nome + objetivo
/workflows
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
/aprovar id
""")

async def status(update, context):
    counts = {}
    for table in ["memory", "tasks", "history", "files", "posts", "videos", "workflows", "approvals", "analytics"]:
        counts[table] = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    await update.message.reply_text(f"""
🚀 STREETCORE STATUS

Memórias: {counts['memory']}
Tarefas: {counts['tasks']}
Histórico: {counts['history']}
Arquivos: {counts['files']}
Posts: {counts['posts']}
Vídeos: {counts['videos']}
Workflows: {counts['workflows']}
Aprovações: {counts['approvals']}
Analytics: {counts['analytics']}

✅ Web ativo
✅ Telegram ativo
✅ SQLite ativo
✅ Memória vetorial local ativa
✅ Upload IA ativo
✅ Multiagentes ativo
✅ Copiloto operacional ativo
""")

async def generic_agent(update, context, role):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Digite uma ideia após o comando.")
        return
    response = ask_ai(prompt, role)
    await send_long(update, response)

async def completo(update, context):
    prompt = " ".join(context.args)
    final = ""
    for role in AGENTS:
        result = ask_ai(prompt, role)
        final += f"\n\n## {role.upper()}\n\n{result}"
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
    await update.message.reply_text("🧠 memória vetorial salva")

async def memorias(update, context):
    rows = cursor.execute("SELECT id, content FROM memory ORDER BY id DESC LIMIT 20").fetchall()
    text = "🧠 MEMÓRIAS\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]}\n\n"
    await send_long(update, text[:4000] if rows else "Sem memórias.")

async def buscar(update, context):
    q = " ".join(context.args)
    results = vector_search(q, 8)
    text = f"🔎 BUSCA VETORIAL: {q}\n\n"
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
    content = ask_ai(f"Crie um post completo para {platform} sobre: {theme}. Inclua legenda, CTA, hashtags, ideia visual e versão curta.", "marketing")
    cursor.execute("INSERT INTO posts(platform,theme,content,status,created_at) VALUES(?,?,?,?,?)", (platform, theme, content, "rascunho", now()))
    conn.commit()
    await send_long(update, content)

async def posts(update, context):
    rows = cursor.execute("SELECT id, platform, theme, status FROM posts ORDER BY id DESC LIMIT 30").fetchall()
    text = "📲 POSTS\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[2]} — {r[3]}\n"
    await send_long(update, text if rows else "Nenhum post.")

async def videoai(update, context):
    theme = " ".join(context.args)
    script = ask_ai(f"Crie um vídeo IA completo sobre: {theme}. Inclua roteiro, cenas, prompts de vídeo, narração, texto na tela e edição.", "video")
    cursor.execute("INSERT INTO videos(theme,script,status,created_at) VALUES(?,?,?,?)", (theme, script, "roteiro", now()))
    conn.commit()
    await send_long(update, script)

async def videos(update, context):
    rows = cursor.execute("SELECT id, theme, status FROM videos ORDER BY id DESC LIMIT 30").fetchall()
    text = "🎬 VÍDEOS\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[2]}\n"
    await send_long(update, text if rows else "Nenhum vídeo.")

async def workflow(update, context):
    text = " ".join(context.args)
    steps = ask_ai(f"Crie um workflow automático gratuito para: {text}. Inclua etapas, ferramentas grátis, gatilhos, aprovações e execução.", "automation")
    cursor.execute("INSERT INTO workflows(name,steps,status,created_at) VALUES(?,?,?,?)", (text, steps, "ativo", now()))
    conn.commit()
    await send_long(update, steps)

async def workflows(update, context):
    rows = cursor.execute("SELECT id, name, status FROM workflows ORDER BY id DESC LIMIT 30").fetchall()
    text = "⚙️ WORKFLOWS\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[2]}\n"
    await send_long(update, text if rows else "Nenhum workflow.")

async def copiloto(update, context):
    goal = " ".join(context.args)
    response = ask_ai(f"""
Atue como copiloto operacional IA.

Objetivo:
{goal}

Crie:
1. diagnóstico
2. plano de ação
3. tarefas
4. automações possíveis
5. riscos
6. próximos passos
7. o que precisa de aprovação humana
""", "automation")
    await send_long(update, response)

async def aprovar(update, context):
    try:
        approval_id = int(context.args[0])
        cursor.execute("UPDATE approvals SET status=? WHERE id=?", ("aprovado", approval_id))
        conn.commit()
        await update.message.reply_text("✅ aprovado")
    except:
        await update.message.reply_text("Use: /aprovar 1")

async def normal_chat(update, context):
    text = update.message.text
    if needs_approval(text):
        cursor.execute("INSERT INTO approvals(action,status,created_at) VALUES(?,?,?)", (text, "pendente", now()))
        conn.commit()
        await update.message.reply_text("🛡 Ação sensível salva para aprovação. Use /aprovar ID.")
        return
    response = ask_ai(text)
    await send_long(update, response)

web = Flask(__name__)
web.secret_key = "streetcore-secret"

HTML = """
<!doctype html>
<html>
<head>
<title>StreetCore OS V5</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box;font-family:Arial}body{margin:0;background:#050510;color:white;display:flex;height:100vh;overflow:hidden}
.sidebar{width:250px;background:#0d0d18;padding:20px;border-right:1px solid #222}
.logo{font-size:26px;font-weight:bold;color:#9333ea;margin-bottom:8px}.status{font-size:12px;opacity:.7;margin-bottom:20px}
.btn{display:block;width:100%;padding:12px;margin-bottom:10px;border:0;border-radius:12px;background:#151525;color:white;text-align:left}
.main{flex:1;display:flex;flex-direction:column}.top{height:64px;background:#0d0d18;border-bottom:1px solid #222;display:flex;align-items:center;padding:0 20px;font-weight:bold}
.chat{flex:1;overflow:auto;padding:20px;display:flex;flex-direction:column;gap:16px}.msg{padding:16px;border-radius:16px;max-width:900px;white-space:pre-wrap;line-height:1.5}
.ai{background:#111827;border:1px solid #333}.user{background:#1f1f35;align-self:flex-end}.bottom{padding:14px;background:#0d0d18;border-top:1px solid #222;display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:10px}input,select{flex:1;padding:14px;border:0;border-radius:12px;background:#151525;color:white}button{padding:14px 18px;border:0;border-radius:12px;background:#9333ea;color:white;font-weight:bold}
.upload{background:#2563eb}@media(max-width:800px){body{flex-direction:column}.sidebar{width:100%;height:auto}.main{height:calc(100vh - 190px)}.row{flex-direction:column}button{width:100%}}
</style>
</head>
<body>
<div class="sidebar">
<div class="logo">🔥 StreetCore OS</div>
<div class="status">V5 GOD MODE • ONLINE</div>
<button class="btn" onclick="quick('Crie um plano para hoje')">Plano do dia</button>
<button class="btn" onclick="quick('Crie posts automáticos para Instagram')">Posts</button>
<button class="btn" onclick="quick('Crie um workflow automático')">Workflow</button>
<button class="btn" onclick="quick('Crie roteiro de vídeo IA')">Vídeo IA</button>
<button class="btn" onclick="window.location='/api/status'">API Status</button>
</div>
<div class="main">
<div class="top">StreetCore AI Operating System</div>
<div class="chat" id="chat">
<div class="msg ai">🔥 StreetCore OS V5 GOD MODE online.

✅ Chat IA
✅ Upload IA
✅ Posts automáticos
✅ Vídeos IA
✅ Workflows
✅ Memória vetorial local
✅ Analytics
✅ Multiusuário base
✅ Copiloto operacional</div>
</div>
<div class="bottom">
<div class="row">
<select id="agent">
<option value="ceo">CEO</option>
<option value="marketing">Marketing</option>
<option value="dev">Dev</option>
<option value="design">Design</option>
<option value="video">Video</option>
<option value="automation">Automation</option>
<option value="sales">Sales</option>
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
function quick(t){document.getElementById('prompt').value=t;sendMessage()}
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
</body>
</html>
"""

@web.route("/")
def home():
    return render_template_string(HTML)

@web.route("/ask", methods=["POST"])
def ask_web():
    data = request.get_json()
    prompt = data.get("prompt", "")
    agent = data.get("agent", "ceo")

    if needs_approval(prompt):
        cursor.execute("INSERT INTO approvals(action,status,created_at) VALUES(?,?,?)", (prompt, "pendente", now()))
        conn.commit()
        return jsonify({"response": "🛡 Ação sensível criada para aprovação."})

    response = ask_ai(prompt, agent)
    return jsonify({"response": response})

@web.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"response": "Nenhum arquivo."})
    file = request.files["file"]
    filename = secure_filename(file.filename)
    path = os.path.join("uploads", filename)
    file.save(path)

    content = ""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(path)
        for page in reader.pages:
            try:
                content += page.extract_text() + "\n"
            except:
                pass
    elif 