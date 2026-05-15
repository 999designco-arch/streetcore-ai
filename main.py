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
        text += f"{r[0]}. {r[1]} — {r[2][:100]