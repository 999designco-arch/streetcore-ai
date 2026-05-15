import os, sqlite3, urllib.parse, threading, math, json, secrets, csv, io, time
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, session, send_file, Response
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
conn = sqlite3.connect("streetcore_v11.db", check_same_thread=False)
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
"CREATE TABLE IF NOT EXISTS approvals(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,action TEXT,status TEXT,created_at TEXT,resolved_at TEXT)",
"CREATE TABLE IF NOT EXISTS gallery(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,type TEXT,prompt TEXT,url TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS analytics(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,event TEXT,data TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,email TEXT,phone TEXT,stage TEXT,notes TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS content_calendar(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,title TEXT,platform TEXT,publish_date TEXT,status TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS pages(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,type TEXT,title TEXT,html TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS automations(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,action TEXT,schedule_text TEXT,status TEXT,last_run TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,type TEXT,message TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS custom_agents(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,description TEXT,system_prompt TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS templates(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,type TEXT,name TEXT,description TEXT,payload TEXT,created_at TEXT)",
"CREATE TABLE IF NOT EXISTS marketplace(id INTEGER PRIMARY KEY AUTOINCREMENT,type TEXT,name TEXT,description TEXT,payload TEXT,created_at TEXT)"
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

def seed_marketplace():
    total = cursor.execute("SELECT COUNT(*) FROM marketplace").fetchone()[0]
    if total > 0:
        return
    seeds = [
        ("business", "Agência de Automação IA", "Modelo de negócio para vender automações com IA.", "Crie uma agência de automação IA com oferta, funil, serviços, pricing e plano de 30 dias."),
        ("business", "SaaS Micro Nicho", "Template para criar SaaS simples e vendável.", "Crie um SaaS de micro nicho com MVP, stack grátis, landing, pricing e roadmap."),
        ("content", "30 Posts Instagram", "Calendário de 30 posts.", "Crie 30 posts para Instagram com gancho, legenda, CTA, hashtag e ideia visual."),
        ("landing", "Landing Page Premium", "Página de vendas simples e forte.", "Crie uma landing page com headline, promessa, seções, prova, oferta e CTA."),
        ("workflow", "Workflow Conteúdo Diário", "Rotina automática de produção de conteúdo.", "Crie workflow diário de conteúdo com ideação, roteiro, imagem, legenda, revisão e publicação segura."),
        ("agent", "Closer IA", "Agente vendedor para WhatsApp e propostas.", "Você é um closer IA. Foque em objeções, proposta, follow-up e fechamento."),
        ("agent", "Diretor Criativo IA", "Agente de branding e campanhas.", "Você é um diretor criativo premium. Foque em estética, campanha, conceito e diferenciação.")
    ]
    for s in seeds:
        cursor.execute("INSERT INTO marketplace(type,name,description,payload,created_at) VALUES(?,?,?,?,?)", (*s, now()))
    conn.commit()

ensure_admin()
seed_marketplace()

MASTER_PROMPT = """
Você é StreetCore OS V11 — AI Company Operating System.
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
    user_id = user_id or uid()
    cursor.execute("INSERT INTO analytics(user_id,event,data,created_at) VALUES(?,?,?,?)", (user_id, event, data, now()))
    conn.commit()

def add_log(user_id, log_type, message):
    cursor.execute("INSERT INTO logs(user_id,type,message,created_at) VALUES(?,?,?,?)", (user_id, log_type, message, now()))
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

def ask_ai(prompt, role="ceo", user_id=None, custom_prompt=None):
    user_id = user_id or uid()
    memories = "\n".join(vector_search(prompt, user_id))
    role_prompt = custom_prompt or AGENTS.get(role, "")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT},
            {"role": "system", "content": role_prompt},
            {"role": "system", "content": "MEMÓRIA:\n" + memories},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=3500
    )
    result = response.choices[0].message.content
    cursor.execute(
        "INSERT INTO history(user_id,agent,prompt,response,created_at) VALUES(?,?,?,?,?)",
        (user_id, role, prompt, result, now())
    )
    conn.commit()
    log_event("ai_response", role, user_id)
    return result

def image_url(prompt):
    return "https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt)

def needs_approval(text):
    return any(x in text.lower() for x in SENSITIVE)

def create_approval(action, user_id=None):
    user_id = user_id or uid()
    cursor.execute(
        "INSERT INTO approvals(user_id,action,status,created_at,resolved_at) VALUES(?,?,?,?,?)",
        (user_id, action, "pendente", now(), "")
    )
    conn.commit()
    add_log(user_id, "approval", "Aprovação criada: " + action[:180])
    return cursor.lastrowid

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
            cursor.execute(
                "INSERT INTO tasks(user_id,project_id,task,status,priority,created_at) VALUES(?,?,?,?,?,?)",
                (user_id, project_id, clean, "pendente", "alta", now())
            )
    conn.commit()
    add_log(user_id, "project", "Projeto criado: " + goal[:120])
    return plan

def debate_agents(goal, user_id):
    final = ""
    for role in ["ceo", "marketing", "sales", "dev", "automation", "design", "finance", "ops"]:
        result = ask_ai(f"Analise este objetivo pelo seu ponto de vista e entregue plano objetivo: {goal}", role, user_id)
        final += f"\n\n## {role.upper()}\n\n{result}"
    synthesis = ask_ai(f"Com base nestas análises dos agentes, crie uma decisão final integrada:\n{final}", "ceo", user_id)
    return final + "\n\n# DECISÃO FINAL INTEGRADA\n\n" + synthesis

def generate_landing_html(title, offer):
    return f"""
<!doctype html>
<html>
<head><meta charset="utf-8"><title>{title}</title>
<style>
body{{margin:0;background:#07070a;color:white;font-family:Arial}}
section{{padding:70px 10%;}}
.hero{{background:linear-gradient(135deg,#07070a,#2b0055);min-height:70vh;display:flex;flex-direction:column;justify-content:center}}
h1{{font-size:54px;max-width:900px}}p{{font-size:20px;line-height:1.6;color:#ddd;max-width:850px}}
.cta{{display:inline-block;background:#9333ea;color:white;padding:18px 28px;border-radius:14px;text-decoration:none;font-weight:bold;margin-top:20px}}
.card{{background:#111827;border:1px solid #333;border-radius:18px;padding:24px;margin:15px 0}}
</style></head>
<body>
<section class="hero"><h1>{title}</h1><p>{offer}</p><a class="cta" href="#">Quero começar agora</a></section>
<section><h2>Por que isso funciona?</h2><div class="card">Oferta clara, direta e criada para conversão.</div><div class="card">Estrutura visual premium e pronta para captar leads.</div><div class="card">Mensagem forte, simples e orientada a resultado.</div></section>
<section><h2>Próximo passo</h2><p>Solicite um diagnóstico e receba um plano personalizado.</p><a class="cta" href="#">Solicitar diagnóstico</a></section>
</body></html>
"""

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

# TELEGRAM

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore OS V11 online. Digite /menu")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE OS V11

/completo ideia
/debate ideia
/ceo /marketing /dev /design /video /auto /sales /finance /ops

/criar_agente nome | função
/agentes
/usar_agente id | pedido

/template tipo | nome | descrição | prompt
/templates
/executar_template id | ideia

/criar_empresa ideia
/criar_saas ideia
/criar_campanha ideia
/criar_funil ideia
/criar_marca ideia
/criar_produto ideia
/criar_landing ideia
/criar_projeto ideia

/post instagram tema
/social30 tema
/videoai tema
/workflow objetivo
/copiloto objetivo

/salvar memória
/buscar termo
/tarefa texto
/hoje
/status
/aprovar id
""")

async def status(update, context):
    text = "🚀 STREETCORE OS V11\n\n"
    for t in ["memory","tasks","projects","posts","videos","workflows","leads","content_calendar","pages","approvals","logs","custom_agents","templates"]:
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

async def criar_agente(update, context):
    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text("Use: /criar_agente Nome | função do agente")
        return
    name, desc = [x.strip() for x in text.split("|", 1)]
    system_prompt = f"Você é {name}. {desc}. Responda em português, de forma prática e passo a passo."
    cursor.execute("INSERT INTO custom_agents(user_id,name,description,system_prompt,created_at) VALUES(?,?,?,?,?)", (1, name, desc, system_prompt, now()))
    conn.commit()
    await update.message.reply_text("✅ Agente criado.")

async def agentes(update, context):
    rows = cursor.execute("SELECT id,name,description FROM custom_agents WHERE user_id=? ORDER BY id DESC", (1,)).fetchall()
    text = "🤖 AGENTES\n\n"
    for r in rows:
        text += f"{r[0]}. {r[1]} — {r[2]}\n"
    await send_long(update, text if rows else "Nenhum agente.")

async def usar_agente(update, context):
    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text("Use: /usar_agente id | pedido")
        return
    idtxt, prompt = [x.strip() for x in text.split("|", 1)]
    row = cursor.execute("SELECT name,system_prompt FROM custom_agents WHERE id=? AND user_id=?", (int(idtxt), 1)).fetchone()
    if not row:
        await update.message.reply_text("Agente não encontrado.")
        return
    await send_long(update, ask_ai(prompt, row[0], 1, row[1]))

async def template(update, context):
    text = " ".join(context.args)
    parts = [x.strip() for x in text.split("|")]
    if len(parts) < 4:
        await update.message.reply_text("Use: /template tipo | nome | descrição | prompt")
        return
    cursor.execute("INSERT INTO templates(user_id,type,name,description,payload,created_at) VALUES(?,?,?,?,?,?)", (1, parts[0], parts[1], parts[2], parts[3], now()))
    conn.commit()
    await update.message.reply_text("✅ Template salvo.")

async def templates(update, context):
    rows = cursor.execute("SELECT id,type,name,description FROM templates WHERE user_id=? ORDER BY id DESC", (1,)).fetchall()
    text = "📦 TEMPLATES\n\n"
    for r in rows:
        text += f"{r[0]}. [{r[1]}] {r[2]} — {r[3]}\n"
    await send_long(update, text if rows else "Nenhum template.")

async def executar_template(update, context):
    text = " ".join(context.args)
    if "|" not in text:
        await update.message.reply_text("Use: /executar_template id | ideia")
        return
    idtxt, idea = [x.strip() for x in text.split("|", 1)]
    row = cursor.execute("SELECT type,name,payload FROM templates WHERE id=? AND user_id=?", (int(idtxt), 1)).fetchone()
    if not row:
        await update.message.reply_text("Template não encontrado.")
        return
    result = ask_ai(row[2] + "\n\nIdeia:\n" + idea, "ceo", 1)
    await send_long(update, result)

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
    await update.message.reply_text("✅ Landing page criada e salva no painel.")

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

async def hoje_cmd(update, context):
    tasks = cursor.execute("SELECT task,priority FROM tasks WHERE user_id=? AND status!='concluída' ORDER BY id DESC LIMIT 20", (1,)).fetchall()
    response = ask_ai(f"Monte meu plano de hoje com base nestas tarefas:\n{tasks}", "ops", 1)
    await send_long(update, response)

async def aprovar_cmd(update, context):
    try:
        approval_id = int(context.args[0])
        cursor.execute("UPDATE approvals SET status=?,resolved_at=? WHERE id=?", ("aprovado", now(), approval_id))
        conn.commit()
        await update.message.reply_text("✅ Aprovação marcada como aprovada.")
    except:
        await update.message.reply_text("Use: /aprovar 1")

# WEB

web = Flask(__name__)
web.secret_key = os.getenv("FLASK_SECRET", "streetcore-v11-" + secrets.token_hex(8))

CSS = """
<style>
*{box-sizing:border-box;font-family:Arial}body{margin:0;background:#050510;color:white;min-height:100vh}a{text-decoration:none;color:white}
.app{display:flex;min-height:100vh}.sidebar{width:295px;background:#0d0d18;padding:20px;border-right:1px solid #222}
.logo{font-size:26px;font-weight:bold;color:#a855f7}.status{font-size:12px;opacity:.7;margin:12px 0 20px}
.nav a{display:block;padding:12px;background:#151525;margin-bottom:8px;border-radius:12px}.nav a:hover{background:#222240}
.main{flex:1}.top{height:70px;background:#0d0d18;border-bottom:1px solid #222;display:flex;align-items:center;justify-content:space-between;padding:0 20px}
.content{padding:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
.card{background:#111827;border:1px solid #333;border-radius:18px;padding:18px}.big{font-size:36px;font-weight:bold;color:#a855f7}
.chat{height:calc(100vh - 245px);overflow:auto;display:flex;flex-direction:column;gap:14px;padding:15px}.msg{padding:15px;border-radius:16px;white-space:pre-wrap;line-height:1.5;max-width:900px}
.ai{background:#111827;border:1px solid #333}.user{background:#1f1f35;align-self:flex-end}.bottom{padding:14px;background:#0d0d18;border-top:1px solid #222;display:flex;flex-direction:column;gap:10px}
.row{display:flex;gap:10px}input,select,textarea{width:100%;padding:14px;border:0;border-radius:12px;background:#151525;color:white}
button{padding:14px 18px;border:0;border-radius:12px;background:#9333ea;color:white;font-weight:bold;cursor:pointer}.upload{background:#2563eb}.danger{background:#dc2626}.ok{background:#16a34a}
table{width:100%;border-collapse:collapse;background:#111827;border-radius:12px;overflow:hidden}td,th{padding:12px;border-bottom:1px solid #333;text-align:left;vertical-align:top}
.login{max-width:450px;margin:80px auto;background:#111827;padding:30px;border-radius:20px;border:1px solid #333}
.pipeline,.kanban{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.stage{background:#111827;padding:14px;border-radius:16px;min-height:300px}.lead,.task{background:#1f1f35;padding:12px;border-radius:12px;margin-bottom:10px}
@media(max-width:900px){.app{flex-direction:column}.sidebar{width:100%}.row{flex-direction:column}.pipeline,.kanban{grid-template-columns:1fr}.chat{height:55vh}}
</style>
"""

def logged():
    return session.get("user_id")

def require_login():
    return bool(logged())

def current_name():
    if not logged():
        return "Usuário"
    row = cursor.execute("SELECT name FROM users WHERE id=?", (uid(),)).fetchone()
    return row[0] if row else "Usuário"

def layout(title, body):
    return f"""
<!doctype html><html><head><title>{title}</title><meta name="viewport" content="width=device-width, initial-scale=1">{CSS}</head>
<body><div class="app"><div class="sidebar"><div class="logo">🔥 StreetCore OS</div><div class="status">V11 AGENT FACTORY<br>{current_name()}</div>
<div class="nav">
<a href="/">Dashboard</a><a href="/today">Hoje</a><a href="/chat">Chat IA</a><a href="/agent-builder">Agent Builder</a><a href="/templates">Templates</a><a href="/marketplace">Marketplace</a>
<a href="/command">Command Center</a><a href="/approvals">Approval Center</a><a href="/kanban">Kanban</a><a href="/projects">Projetos</a><a href="/calendar">Calendário</a><a href="/crm">CRM</a>
<a href="/posts">Posts</a><a href="/videos">Vídeos</a><a href="/workflows">Workflows</a><a href="/automations">Automações</a><a href="/pages">Sites/Landings</a><a href="/memory">Memória</a><a href="/files">Arquivos</a><a href="/logs">Logs</a><a href="/analytics-page">Analytics</a><a href="/logout">Sair</a>
</div></div><div class="main"><div class="top"><b>{title}</b><span>StreetCore OS V11</span></div><div class="content">{body}</div></div></div></body></html>
"""

@web.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        row = cursor.execute("SELECT id,password FROM users WHERE email=?", (request.form.get("email"),)).fetchone()
        if row and check_password_hash(row[1], request.form.get("password")):
            session["user_id"] = row[0]
            return redirect("/")
    return f"""<!doctype html><html><head><title>Login</title>{CSS}</head><body><div class="login">
<h1>🔥 StreetCore OS V11</h1><form method="POST">
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
    for t in ["custom_agents","templates","projects","tasks","posts","videos","workflows","automations","approvals","leads","pages","logs"]:
        cards += f"<div class='card'><h3>{t}</h3><div class='big'>{count_table(t)}</div></div>"
    return layout("Dashboard Executivo", f"<div class='grid'>{cards}</div>")

@web.route("/agent-builder")
def agent_builder():
    if not require_login(): return redirect("/login")
    rows = cursor.execute("SELECT id,name,description FROM custom_agents WHERE user_id=? ORDER BY id DESC", (uid(),)).fetchall()
    html = """
<div class="card"><h2>Criar Agente Personalizado</h2>
<form method="POST" action="/add-agent">
<input name="name" placeholder="Nome do agente"><br><br>
<textarea name="description" placeholder="Função do agente"></textarea><br><br>
<textarea name="system_prompt" placeholder="Prompt avançado do agente"></textarea><br><br>
<button>Criar agente</button>
</form></div><br><div class="card"><table><tr><th>ID</th><th>Nome</th><th>Descrição</th><th>Testar</th></tr>
"""
    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td><a href='/test-agent/{r[0]}'><button>Testar</button></a></td></tr>"
    html += "</table></div>"
    return layout("Agent Builder", html)

@web.route("/add-agent", methods=["POST"])
def add_agent():
    prompt = request.form.get("system_prompt") or f"Você é {request.form.get('name')}. {request.form.get('description')}"
    cursor.execute("INSERT INTO custom_agents(user_id,name,description,system_prompt,created_at) VALUES(?,?,?,?,?)", (uid(), request.form.get("name"), request.form.get("description"), prompt, now()))
    conn.commit()
    return redirect("/agent-builder")

@web.route("/test-agent/<int:agent_id>")
def test_agent(agent_id):
    if not require_login(): return redirect("/login")
    row = cursor.execute("SELECT name FROM custom_agents WHERE id=? AND user_id=?", (agent_id, uid())).fetchone()
    if not row: return redirect("/agent-builder")
    return layout("Testar Agente", f"""
<div class="card">
<h2>{row[0]}</h2>
<input id="prompt" placeholder="Pedido para o agente"><br><br>
<button onclick="run()">Executar</button>
<div id="out" class="msg ai">Resultado aqui.</div>
</div>
<script>
async function run(){{const p=document.getElementById('prompt').value;document.getElementById('out').innerText='Executando...';const r=await fetch('/run-agent-api',{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:{agent_id},prompt:p}})});const d=await r.json();document.getElementById('out').innerText=d.response}}
</script>
""")

@web.route("/templates")
def templates_page():
    if not require_login(): return redirect("/login")
    rows = cursor.execute("SELECT id,type,name,description FROM templates WHERE user_id=? ORDER BY id DESC", (uid(),)).fetchall()
    html = """
<div class="card"><h2>Criar Template</h2>
<form method="POST" action="/add-template">
<input name="type" placeholder="Tipo: post, landing, workflow, business"><br><br>
<input name="name" placeholder="Nome"><br><br>
<textarea name="description" placeholder="Descrição"></textarea><br><br>
<textarea name="payload" placeholder="Prompt/template"></textarea><br><br>
<button>Salvar template</button>
</form></div><br><div class="card"><table><tr><th>ID</th><th>Tipo</th><th>Nome</th><th>Descrição</th><th>Executar</th></tr>
"""
    for r in rows:
        html += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td><a href='/execute-template/{r[0]}'><button>Executar</button></a></td></tr>"
    html += "</table></div>"
    return layout("Templates", html)

@web.route("/add-template", methods=["POST"])
def add_template():
    cursor.execute("INSERT INTO templates(user_id,type,name,description,payload,created_at) VALUES(?,?,?,?,?,?)", (uid(), request.form.get("type"), request.form.get("name"), request.form.get("description"), request.form.get("payload"), now()))
    conn.commit()
    return redirect("/templates")

@web.route("/execute-template/<int:template_id>")
def execute_template_page(template_id):
    if not require_login(): return redirect("/login")
    return layout("Executar Template", f"""
<div class="card">
<input id="idea" placeholder="Ideia base"><br><br>
<button onclick="run()">Executar</button>
<div id="out" class="msg ai">Resultado aqui.</div>
</div>
<script>
async function run(){{const idea=document.getElementById('idea').value;document.getElementById('out').innerText='Gerando...';const r=await fetch('/execute-template-api',{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{id:{template_id},idea:idea}})});const d=await r.json();document.getElementById('out').innerText=d.response}}
</script>
""")

@web.route("/marketplace")
def marketplace_page():
    if not require_login(): return redirect("/login")
    rows = cursor.execute("SELECT id,type,name,description FROM marketplace ORDER BY id DESC").fetchall()
    html = "<div class='grid'>"
    for r in rows:
        html += f"<div class='card'><h3>{r[2]}</h3><p>{r[1]}</p><p>{r[3]}</p><a href='/install-marketplace/{r[0]}'><button>Instalar</button></a></div>"
    html += "</div>"
    return layout("Marketplace Interno", html)

@web.route("/install-marketplace/<int:item_id>")
def install_marketplace(item_id):
    if not require_login(): return redirect("/login")
    row = cursor.execute("SELECT type,name,description,payload FROM marketplace WHERE id=?", (item_id,)).fetchone()
    if row:
        if row[0] == "agent":
            cursor.execute("INSERT INTO custom_agents(user_id,name,description,system_prompt,created_at) VALUES(?,?,?,?,?)", (uid(), row[1], row[2], row[3], now()))
        else:
            cursor.execute("INSERT INTO templates(user_id,type,name,description,payload,created_at) VALUES(?,?,?,?,?,?)", (uid(), row[0], row[1], row[2], row[3], now()))
        conn.commit()
    return redirect("/marketplace")

@web.route("/today")
def today():
    if not require_login(): return redirect("/login")
    tasks = cursor.execute("SELECT id,task,priority FROM tasks WHERE user_id=? AND status!='concluída' ORDER BY id DESC LIMIT 12", (uid(),)).fetchall()
    approvals = cursor.execute("SELECT id,action FROM approvals WHERE user_id=? AND status='pendente' ORDER BY id DESC LIMIT 8", (uid(),)).fetchall()
    posts = cursor.execute("SELECT title,platform,publish_date FROM content_calendar WHERE user_id=? AND status='planejado' ORDER BY id DESC LIMIT 8", (uid(),)).fetchall()
    html = "<div class='grid'><div class='card'><h2>Prioridades</h2>"
    for t in tasks: html += f"<p><b>{t[0]}</b> — {t[1]}<br><small>{t[2]}</small></p>"
    html += "</div><div class='card'><h2>Aprovações</h2>"
    for a in approvals: html += f"<p>#{a[0]} — {a[1][:120]}</p>"
    html += "</div><div class='card'><h2>Conteúdo</h2>"
    for p in posts: html += f"<p>{p[0]} — {p[1]} — {p[2]}</p>"
    html += "</div></div><br><div class='card'><a href='/generate-today'><button>Gerar plano IA de hoje</button></a></div>"
    return layout("O que fazer hoje", html)

@web.route("/generate-today")
def generate_today():
    if not require_login(): return redirect("/login")
    tasks = cursor.execute("SELECT task,priority FROM tasks WHERE user_id=? AND status!='concluída'", (uid(),)).fetchall()
    result = ask_ai(f"Monte meu plano executivo de hoje com base nestas tarefas:\n{tasks}", "ops", uid())
    return layout("Plano IA de Hoje", f"<div class='card'><div class='msg ai'>{result}</div></div>")

@web.route("/chat")
def chat():
    if not require_login(): return redirect("/login")
    return layout("Chat IA", """
<div class="card"><div class="chat" id="chat"><div class="msg ai">🔥 StreetCore OS V11 online.</div></div>
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

@web.route("/approvals")
def approvals_page():
    if not require_login(): return redirect("/login")
    rows = cursor.execute("SELECT id,action,status,created_at FROM approvals WHERE user_id=? ORDER BY id DESC LIMIT 100", (uid(),)).fetchall()
    body = "<div class='card'><table><tr><th>ID</th><th>Ação</th><th>Status</th><th>Data</th><th>Ação</th></tr>"
    for r in rows:
        body += f"<tr><td>{r[0]}</td><td>{r[1][:500]}</td><td>{r[2]}</td><td>{r[3]}</td><td><a href='/approve/{r[0]}'><button class='ok'>Aprovar</button></a> <a href='/reject/{r[0]}'><button class='danger'>Rejeitar</button></a></td></tr>"
    body += "</table></div>"
    return layout("Approval Center", body)

@web.route("/approve/<int:item_id>")
def approve(item_id):
    if not require_login(): return redirect("/login")
    cursor.execute("UPDATE approvals SET status=?,resolved_at=? WHERE id=? AND user_id=?", ("aprovado", now(), item_id, uid()))
    conn.commit()
    add_log(uid(), "approval", f"Aprovação {item_id} aprovada.")
    return redirect("/approvals")

@web.route("/reject/<int:item_id>")
def reject(item_id):
    if not require_login(): return redirect("/login")
    cursor.execute("UPDATE approvals SET status=?,resolved_at=? WHERE id=? AND user_id=?", ("rejeitado", now(), item_id, uid()))
    conn.commit()
    add_log(uid(), "approval", f"Aprovação {item_id} rejeitada.")
    return redirect("/approvals")

@web.route("/kanban")
def kanban():
    if not require_login(): return redirect("/login")
    stages = ["pendente","em andamento","revisão","concluída"]
    html = "<div class='kanban'>"
    for stage in stages:
        html += f"<div class='stage'><h3>{stage}</h3>"
        rows = cursor.execute("SELECT id,task,priority FROM tasks WHERE user_id=? AND status=? ORDER BY id DESC", (uid(), stage)).fetchall()
        for r in rows:
            html += f"<div class='task'><b>#{r[0]}</b><br>{r[1]}<br><small>{r[2]}</small><br><br><a href='/move-task/{r[0]}'><button>Mover</button></a></div>"
        html += "</div>"
    html += "</div>"
    return layout("Kanban de Projetos", html)

@web.route("/move-task/<int:task_id>")
def move_task(task_id):
    if not require_login(): return redirect("/login")
    row = cursor.execute("SELECT status FROM tasks WHERE id=? AND user_id=?", (task_id, uid())).fetchone()
    order = ["pendente","em andamento","revisão","concluída"]
    if row:
        current = row[0]
        nxt = order[(order.index(current) + 1) % len(order)] if current in order else "pendente"
        cursor.execute("UPDATE tasks SET status=? WHERE id=? AND user_id=?", (nxt, task_id, uid()))
        conn.commit()
    return redirect("/kanban")

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
def pages_page():
    if not require_login(): return redirect("/login")
    rows = cursor.execute("SELECT id,type,title,created_at FROM pages WHERE user_id=? ORDER BY id DESC LIMIT 100", (uid(),)).fetchall()
    body = "<div class='card'><table><tr><th>ID</th><th>Tipo</th><th>Título</th><th>Data</th><th>Ações</th></tr>"
    for r in rows:
        body += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td><a href='/page-preview/{r[0]}'><button>Preview</button></a> <a href='/page-export/{r[0]}'><button>Exportar HTML</button></a></td></tr>"
    body += "</table></div>"
    return layout("Sites/Landings", body)

@web.route("/memory")
def memory_page(): return table_page("Memória", "memory", ["id","content","created_at"])
@web.route("/files")
def files_page(): return table_page("Arquivos", "files", ["id","filename","created_at"])
@web.route("/analytics-page")
def analytics_page(): return table_page("Analytics", "analytics", ["id","event","data","created_at"])
@web.route("/logs")
def logs_page(): return table_page("Logs Operacionais", "logs", ["id","type","message","created_at"])
@web.route("/calendar")
def calendar(): return table_page("Calendário", "content_calendar", ["id","title","platform","publish_date","status","created_at"])

@web.route("/automations")
def automations():
    if not require_login(): return redirect("/login")
    rows = cursor.execute("SELECT id,name,action,schedule_text,status,last_run FROM automations WHERE user_id=? ORDER BY id DESC", (uid(),)).fetchall()
    body = "<div class='card'><h2>Nova Automação Segura</h2><form method='POST' action='/add-automation'><input name='name' placeholder='Nome'><br><br><input name='action' placeholder='Ação'><br><br><input name='schedule_text' placeholder='Ex: diário, semanal, manual'><br><br><button>Salvar automação</button></form></div><br>"
    body += "<div class='card'><table><tr><th>ID</th><th>Nome</th><th>Ação</th><th>Agenda</th><th>Status</th><th>Última</th><th>Executar</th></tr>"
    for r in rows:
        body += f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td>{r[4]}</td><td>{r[5]}</td><td><a href='/run-automation/{r[0]}'><button>Executar</button></a></td></tr>"
    body += "</table></div>"
    return layout("Automações Seguras", body)

@web.route("/add-automation", methods=["POST"])
def add_automation():
    if not require_login(): return redirect("/login")
    cursor.execute("INSERT INTO automations(user_id,name,action,schedule_text,status,last_run,created_at) VALUES(?,?,?,?,?,?,?)", (uid(), request.form.get("name"), request.form.get("action"), request.form.get("schedule_text"), "ativo", "", now()))
    conn.commit()
    return redirect("/automations")

@web.route("/run-automation/<int:auto_id>")
def run_automation(auto_id):
    if not require_login(): return redirect("/login")
    row = cursor.execute("SELECT action FROM automations WHERE id=? AND user_id=?", (auto_id, uid())).fetchone()
    if row:
        action = row[0]
        if needs_approval(action):
            create_approval(action, uid())
        else:
            result = ask_ai(f"Execute de forma simulada e segura esta automação: {action}", "automation", uid())
            add_log(uid(), "automation", result[:900])
        cursor.execute("UPDATE automations SET last_run=? WHERE id=? AND user_id=?", (now(), auto_id, uid()))
        conn.commit()
    return redirect("/automations")

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

@web.route("/page-preview/<int:page_id>")
def page_preview(page_id):
    if not require_login(): return redirect("/login")
    row = cursor.execute("SELECT html FROM pages WHERE id=? AND user_id=?", (page_id, uid())).fetchone()
    return row[0] if row else "Página não encontrada."

@web.route("/page-export/<int:page_id>")
def page_export(page_id):
    if not require_login(): return redirect("/login")
    row = cursor.execute("SELECT title,html FROM pages WHERE id=? AND user_id=?", (page_id, uid())).fetchone()
    if not row: return "Página não encontrada."
    filename = (row[0] or "landing").replace(" ", "_")[:40] + ".html"
    return Response(row[1], mimetype="text/html", headers={"Content-Disposition": f"attachment;filename={filename}"})

@web.route("/ask", methods=["POST"])
def ask_web():
    data = request.get_json()
    prompt = data.get("prompt","")
    agent = data.get("agent","ceo")
    if needs_approval(prompt):
        create_approval(prompt, uid())
        return jsonify({"response":"🛡 Ação sensível criada para aprovação."})
    return jsonify({"response":ask_ai(prompt, agent, uid())})

@web.route("/run-agent-api", methods=["POST"])
def run_agent_api():
    data = request.get_json()
    row = cursor.execute("SELECT name,system_prompt FROM custom_agents WHERE id=? AND user_id=?", (data.get("id"), uid())).fetchone()
    if not row:
        return jsonify({"response":"Agente não encontrado."})
    return jsonify({"response":ask_ai(data.get("prompt",""), row[0], uid(), row[1])})

@web.route("/execute-template-api", methods=["POST"])
def execute_template_api():
    data = request.get_json()
    row = cursor.execute("SELECT type,name,payload FROM templates WHERE id=? AND user_id=?", (data.get("id"), uid())).fetchone()
    if not row:
        return jsonify({"response":"Template não encontrado."})
    result = ask_ai(row[2] + "\n\nIdeia:\n" + data.get("idea",""), "ceo", uid())
    return jsonify({"response":result})

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
    allowed = ["posts","videos","workflows","memory","files","analytics","leads","projects","content_calendar","pages","logs","approvals","automations","custom_agents","templates"]
    if table not in allowed: return "invalid"
    rows = cursor.execute(f"SELECT * FROM {table} WHERE user_id=?", (uid(),)).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    for r in rows: writer.writerow(r)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name=f"{table}.csv")

@web.route("/health")
def health():
    return "OK STREETCORE V11 ONLINE", 200

def automation_loop():
    while True:
        try:
            rows = cursor.execute("SELECT id,user_id,name,action,schedule_text,status,last_run FROM automations WHERE status='ativo'").fetchall()
            for r in rows:
                auto_id, user_id, name, action, schedule_text, status, last_run = r
                if schedule_text and "manual" in schedule_text.lower():
                    continue
                current_day = datetime.now().strftime("%Y-%m-%d")
                if last_run and current_day in last_run:
                    continue
                if needs_approval(action):
                    create_approval(f"Automação '{name}': {action}", user_id)
                    add_log(user_id, "automation", f"Automação {name} pediu aprovação.")
                else:
                    result = ask_ai(f"Execute de forma simulada e segura esta automação recorrente: {action}", "automation", user_id)
                    add_log(user_id, "automation", f"{name}: {result[:900]}")
                cursor.execute("UPDATE automations SET last_run=? WHERE id=?", (now(), auto_id))
                conn.commit()
        except Exception as e:
            print("automation_loop_error", e)
        time.sleep(60)

def run_telegram():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    handlers = {
        "start":start,"menu":menu,"status":status,"completo":completo,"debate":debate,
        "ceo":ceo,"marketing":marketing,"dev":dev,"design":design,"video":video_cmd,"auto":auto,"sales":sales,"finance":finance,"ops":ops,
        "criar_agente":criar_agente,"agentes":agentes,"usar_agente":usar_agente,
        "template":template,"templates":templates,"executar_template":executar_template,
        "criar_empresa":criar_empresa,"criar_saas":criar_saas,"criar_campanha":criar_campanha,"criar_funil":criar_funil,"criar_marca":criar_marca,"criar_produto":criar_produto,
        "criar_landing":criar_landing,"criar_projeto":criar_projeto,
        "post":post,"social30":social30,"videoai":videoai,"workflow":workflow,"copiloto":copiloto,
        "tarefa":tarefa,"salvar":salvar,"buscar":buscar,"hoje":hoje_cmd,"aprovar":aprovar_cmd
    }
    for name, func in handlers.items():
        app.add_handler(CommandHandler(name, func))
    app.run_polling(stop_signals=None)

threading.Thread(target=run_telegram, daemon=True).start()
threading.Thread(target=automation_loop, daemon=True).start()

print("🔥 STREETCORE OS V11 ONLINE")
web.run(host="0.0.0.0", port=PORT)