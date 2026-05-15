import os, sqlite3, urllib.parse, threading, math, json
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string
from werkzeug.utils import secure_filename
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from groq import Groq
from pypdf import PdfReader

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = Groq(api_key=GROQ_API_KEY)

conn = sqlite3.connect("streetcore.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS memory(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS vectors(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT, vector TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT, status TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, agent TEXT, prompt TEXT, response TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, content TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS posts(id INTEGER PRIMARY KEY AUTOINCREMENT, platform TEXT, theme TEXT, content TEXT, status TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS videos(id INTEGER PRIMARY KEY AUTOINCREMENT, theme TEXT, script TEXT, status TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS workflows(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, steps TEXT, status TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, status TEXT, created_at TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS analytics(id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT, data TEXT, created_at TEXT)")
conn.commit()

MASTER_PROMPT = """
Você é StreetCore OS GOD MODE.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, estrategista, diretor criativo, engenheiro de IA, programador,
copywriter, social media, vendedor, automação e assistente operacional.
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

def vector_search(query, limit=5):
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
    memories = "\n".join(vector_search(prompt, 6))
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

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore OS V5.1 online. Digite /menu")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE OS V5.1

/completo ideia
/ceo ideia
/marketing ideia
/dev ideia
/design ideia
/video ideia
/auto ideia
/sales ideia

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
    tables = ["memory", "vectors", "tasks", "history", "files", "posts", "videos", "workflows", "approvals", "analytics"]
    text = "🚀 STATUS STREETCORE\n\n"
    for t in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        text += f"{t}: {count}\n"
    await update.message.reply_text(text)

async def generic_agent(update, context, role):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Digite algo depois do comando.")
        return
    response = ask_ai(prompt, role)
    await send_long(update, response)

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
    response = ask_ai(text)
    await send_long(update, response)

web = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
<title>StreetCore OS V5.1</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
*{box-sizing:border-box;font-family:Arial}
body{margin:0;background:#050510;color:white;display:flex;height:100vh;overflow:hidden}
.sidebar{width:250px;background:#0d0d18;padding:20px;border-right:1px solid #222}
.logo{font-size:26px;font-weight:bold;color:#9333ea;margin-bottom:8px}
.status{font-size:12px;opacity:.7;margin-bottom:20px}
.btn{display:block;width:100%;padding:12px;margin-bottom:10px;border:0;border-radius:12px;background:#151525;color:white;text-align:left}
.main{flex:1;display:flex;flex-direction:column}
.top{height:64px;background:#0d0d18;border-bottom:1px solid #222;display:flex;align-items:center;padding:0 20px;font-weight:bold}
.chat{flex:1;overflow:auto;padding:20px;display:flex;flex-direction:column;gap:16px}
.msg{padding:16px;border-radius:16px;max-width:900px;white-space:pre-wrap;line-height:1.5}
.ai{background:#111827;border:1px solid #333}
.user{background:#1f1f35;align-self:flex-end}
.bottom{padding:14px;background:#0d0d18;border-top:1px solid #222;display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:10px}
input,select{flex:1;padding:14px;border:0;border-radius:12px;background:#151525;color:white}
button{padding:14px 18px;border:0;border-radius:12px;background:#9333ea;color:white;font-weight:bold}
.upload{background:#2563eb}
@media(max-width:800px){
body{flex-direction:column}
.sidebar{width:100%;height:auto}
.main{height:calc(100vh - 190px)}
.row{flex-direction:column}
button{width:100%}
}
</style>
</head>
<body>
<div class="sidebar">
<div class="logo">🔥 StreetCore OS</div>
<div class="status">V5.1 • ONLINE</div>
<button class="btn" onclick="quick('Crie um plano para hoje')">Plano do dia</button>
<button class="btn" onclick="quick('Crie posts automáticos para Instagram sobre IA')">Posts</button>
<button class="btn" onclick="quick('Crie um workflow automático')">Workflow</button>
<button class="btn" onclick="quick('Crie roteiro de vídeo IA')">Vídeo IA</button>
<button class="btn" onclick="window.location='/health'">Health</button>
</div>
<div class="main">
<div class="top">StreetCore AI Operating System</div>
<div class="chat" id="chat">
<div class="msg ai">🔥 StreetCore OS V5.1 online.

✅ Chat IA
✅ Upload IA
✅ Posts
✅ Vídeos IA
✅ Workflows
✅ Memória vetorial
✅ Analytics</div>
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

@web.route("/health")
def health():
    return "OK STREETCORE ONLINE", 200

@web.route("/ask", methods=["POST"])
def ask_web():
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
    if "file" not in request.files:
        return jsonify({"response": "Nenhum arquivo."})
    file = request.files["file"]
    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    content = ""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(path)
        for page in reader.pages:
            try:
                content += page.extract_text() + "\\n"
            except:
                pass
    elif filename.lower().endswith(".txt"):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

    cursor.execute("INSERT INTO files(filename,content,created_at) VALUES(?,?,?)", (filename, content[:60000], now()))
    conn.commit()
    save_vector_memory(f"Arquivo {filename}: {content[:3000]}")

    analysis = ask_ai(f"Analise este arquivo: {filename}\\n\\n{content[:14000]}\\n\\nEntregue resumo, insights, riscos, oportunidades e plano de ação.", "ceo")
    return jsonify({"response": analysis})

@web.route("/api/status")
def api_status():
    data = {}
    for table in ["memory", "vectors", "tasks", "history", "files", "posts", "videos", "workflows", "approvals", "analytics"]:
        data[table] = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
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

print("🔥 STREETCORE OS V5.1 WEB MAIN ONLINE")

web.run(host="0.0.0.0", port=PORT)