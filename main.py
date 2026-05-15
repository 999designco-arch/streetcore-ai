import os, json, urllib.parse, traceback, threading
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, render_template_string
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))

client = Groq(api_key=GROQ_API_KEY)
TZ = ZoneInfo("America/Sao_Paulo")

FILES = {
    "memory": "memory.json",
    "tasks": "tasks.json",
    "items": "items.json",
    "assistant": "assistant.json",
    "schedules": "schedules.json",
    "config": "config.json",
    "approvals": "approvals.json"
}

MASTER_PROMPT = """
Você é StreetCore AI MASTER ULTRA.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, estrategista, diretor criativo, programador, vendedor,
engenheiro de automação, social media, designer, roteirista e assistente pessoal.
Explique passo a passo como se estivesse pegando na mão do usuário.
Peça aprovação antes de ações sensíveis.
"""

AGENTS = {
    "ceo": "CEO Agent: estratégia, monetização e escala.",
    "branding": "Branding Agent: marca, identidade e estética.",
    "conteudo": "Content Agent: conteúdo viral e redes sociais.",
    "vendas": "Sales Agent: oferta, copy, funil e conversão.",
    "dev": "Dev Agent: código, apps, APIs, deploy e sistemas.",
    "automacao": "Automation Agent: automações gratuitas e produtividade.",
    "visual": "Visual Agent: imagens, logos, thumbnails e direção de arte.",
    "video": "Video Agent: roteiros, cenas, Shorts, anúncios e prompts.",
    "docs": "Docs Agent: documentos, propostas, briefings e planos.",
    "assistente": "Assistant Agent: agenda, lembretes, hábitos e rotina."
}

SENSITIVE = ["enviar", "publicar", "publique", "postar agora", "apagar", "deletar", "excluir", "comprar", "pagar", "contratar", "cancelar", "mandar mensagem", "enviar email", "remover"]

def load_json(file, default):
    if not os.path.exists(file):
        return default
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def memory():
    mem = load_json(FILES["memory"], {})
    mem.setdefault("perfil", {})
    mem.setdefault("objetivos", [])
    mem.setdefault("preferencias", [])
    return mem

def save_memory(mem):
    save_json(FILES["memory"], mem)

def save_item(tipo, tema, conteudo):
    items = load_json(FILES["items"], [])
    items.append({
        "tipo": tipo,
        "tema": tema,
        "conteudo": conteudo,
        "data": str(datetime.now(TZ))
    })
    save_json(FILES["items"], items)

def sensitive(text):
    return any(w in text.lower() for w in SENSITIVE)

def create_approval(acao, origem):
    data = load_json(FILES["approvals"], [])
    data.append({
        "acao": acao,
        "origem": origem,
        "status": "pendente",
        "data": str(datetime.now(TZ))
    })
    save_json(FILES["approvals"], data)
    return len(data)

def ask_ai(prompt, agent=None):
    mem = json.dumps(memory(), ensure_ascii=False, indent=2)
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT + "\n\n" + AGENTS.get(agent, "") + f"\n\nMEMÓRIA:\n{mem}"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=4000
    )
    return r.choices[0].message.content

async def send_long(update, text):
    for i in range(0, len(text or "Sem resposta.", 3900)):
        await update.message.reply_text((text or "Sem resposta.")[i:i+3900])

def auto_memory(msg):
    mem = memory()
    t = msg.lower()
    try:
        if "meu nome é" in t:
            mem["perfil"]["nome"] = t.split("meu nome é")[1].strip()
        if "minha marca é" in t:
            mem["perfil"]["marca"] = t.split("minha marca é")[1].strip()
        if "meu nicho é" in t:
            mem["perfil"]["nicho"] = t.split("meu nicho é")[1].strip()
        if "quero criar" in t:
            obj = t.split("quero criar")[1].strip()
            if obj not in mem["objetivos"]:
                mem["objetivos"].append(obj)
    except:
        pass
    mem["ultima_interacao"] = str(datetime.now(TZ))
    save_memory(mem)

def img_url(prompt, w=1024, h=1024, seed=77):
    return f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width={w}&height={h}&seed={seed}"

def img_prompt(tipo, tema):
    if tipo == "logo":
        return f"minimal futuristic luxury logo, clean vector, white background, premium streetwear branding. Brand: {tema}"
    if tipo == "thumbnail":
        return f"viral YouTube thumbnail, cinematic, high contrast, bold visual, high CTR, premium futuristic style. Theme: {tema}"
    if tipo == "banner":
        return f"wide premium cinematic banner, futuristic luxury brand campaign, clean space for headline. Theme: {tema}"
    if tipo == "poster":
        return f"cinematic poster, premium futuristic street luxury, neon, dramatic advertising composition. Theme: {tema}"
    return f"ultra realistic cinematic image, street luxury futuristic, cyberpunk premium, dramatic lighting, 8k. Theme: {tema}"

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore AI com Dashboard Web online. Digite /menu.")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI MASTER + DASHBOARD

/menu /status /memoria
/perfil nome = Rafael
/objetivo criar empresa de IA
/preferencia usar ferramentas grátis

/tarefa texto
/tarefas
/check
/concluir 1

/agent objetivo
/ceo /brandagent /contentagent /salesagent /devagent /autoagent /visualagent /videoagent /docsagent

/imagem tema
/logo marca
/thumbnail tema
/poster tema
/banner tema
/promptimg tema

/video tema
/roteiro tema
/shorts tema
/anuncio tema
/promptvideo tema

/roadmap tema
/branding tema
/conteudo tema
/oferta tema
/funil tema
/saas tema
/site tema
/app tema
/doc tema
/proposta tema
/briefing tema

/agenda texto
/lembrete texto
/dia

/ativar
/agendar 09:00 revisar tarefas
/agendamentos

/backup
/exportar
/listar
/buscar palavra
/veritem 1
""")

async def status(update, context):
    mem = memory()
    await update.message.reply_text(f"""
🚀 STATUS

Perfil: {len(mem["perfil"])}
Objetivos: {len(mem["objetivos"])}
Preferências: {len(mem["preferencias"])}
Tarefas: {len(load_json(FILES["tasks"], []))}
Itens salvos: {len(load_json(FILES["items"], []))}
Lembretes/Agenda: {len(load_json(FILES["assistant"], []))}
Agendamentos: {len(load_json(FILES["schedules"], []))}
Aprovações: {len(load_json(FILES["approvals"], []))}

Dashboard: ativo
""")

async def memoria(update, context):
    mem = memory()
    text = "🧠 MEMÓRIA\n\n👤 PERFIL:\n"
    for k, v in mem["perfil"].items():
        text += f"• {k}: {v}\n"
    text += "\n🎯 OBJETIVOS:\n"
    for i, v in enumerate(mem["objetivos"], 1):
        text += f"{i}. {v}\n"
    text += "\n⚙️ PREFERÊNCIAS:\n"
    for i, v in enumerate(mem["preferencias"], 1):
        text += f"{i}. {v}\n"
    await send_long(update, text)

async def perfil(update, context):
    txt = " ".join(context.args)
    if "=" not in txt:
        await update.message.reply_text("Use: /perfil nome = Rafael")
        return
    k, v = txt.split("=", 1)
    mem = memory()
    mem["perfil"][k.strip()] = v.strip()
    save_memory(mem)
    await update.message.reply_text("✅ Perfil salvo.")

async def objetivo(update, context):
    txt = " ".join(context.args)
    mem = memory()
    mem["objetivos"].append(txt)
    save_memory(mem)
    await update.message.reply_text("🎯 Objetivo salvo.")

async def preferencia(update, context):
    txt = " ".join(context.args)
    mem = memory()
    mem["preferencias"].append(txt)
    save_memory(mem)
    await update.message.reply_text("⚙️ Preferência salva.")

async def tarefa(update, context):
    txt = " ".join(context.args)
    tasks = load_json(FILES["tasks"], [])
    tasks.append({"tarefa": txt, "status": "pendente", "data": str(datetime.now(TZ))})
    save_json(FILES["tasks"], tasks)
    await update.message.reply_text("✅ Tarefa criada.")

async def tarefas(update, context):
    tasks = load_json(FILES["tasks"], [])
    text = "📝 TAREFAS:\n\n"
    for i, t in enumerate(tasks, 1):
        text += f"{i}. {t['tarefa']} — {t['status']}\n"
    await send_long(update, text if tasks else "Nenhuma tarefa.")

async def check(update, context):
    tasks = load_json(FILES["tasks"], [])
    text = "⚠️ PENDENTES:\n\n"
    found = False
    for i, t in enumerate(tasks, 1):
        if t.get("status") == "pendente":
            found = True
            text += f"{i}. {t['tarefa']}\n"
    await send_long(update, text if found else "🔥 Nenhuma pendência.")

async def concluir(update, context):
    try:
        n = int(context.args[0])
        tasks = load_json(FILES["tasks"], [])
        tasks[n-1]["status"] = "concluída"
        save_json(FILES["tasks"], tasks)
        await update.message.reply_text("✅ Concluída.")
    except:
        await update.message.reply_text("Use: /concluir 1")

async def generic(update, context, tipo, prompt, agent=None):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text(f"Use: /{tipo} tema")
        return
    resp = ask_ai(prompt + "\n\nTema:\n" + tema, agent)
    save_item(tipo, tema, resp)
    await send_long(update, resp)

async def ceo(u,c): await generic(u,c,"ceo","Analise como CEO com estratégia, monetização e próximos passos.","ceo")
async def brandagent(u,c): await generic(u,c,"branding","Crie branding premium completo.","branding")
async def contentagent(u,c): await generic(u,c,"conteudo","Crie estratégia de conteúdo viral.","conteudo")
async def salesagent(u,c): await generic(u,c,"vendas","Crie oferta, copy, funil e plano de vendas.","vendas")
async def devagent(u,c): await generic(u,c,"dev","Crie solução técnica com stack grátis, código e deploy.","dev")
async def autoagent(u,c): await generic(u,c,"automacao","Crie automação grátis passo a passo.","automacao")
async def visualagent(u,c): await generic(u,c,"visual","Crie direção visual premium e prompts de imagem.","visual")
async def videoagent(u,c): await generic(u,c,"video","Crie estratégia de vídeo, roteiro, cenas e prompts.","video")
async def docsagent(u,c): await generic(u,c,"docs","Crie documento profissional completo.","docs")

async def agent(update, context):
    tema = " ".join(context.args)
    resp = ask_ai(f"""
Resolva com todos os agentes:

{tema}

1. CEO
2. Branding
3. Conteúdo
4. Vendas
5. Dev
6. Automação
7. Visual
8. Vídeo
9. Documentos
10. Assistente pessoal
11. Plano final
12. Próximo passo imediato
""")
    save_item("multiagent", tema, resp)
    await send_long(update, resp)

async def imagem(update, context):
    tema = " ".join(context.args)
    await update.message.reply_text("🎨 Gerando imagem grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("imagem", tema)))

async def logo(update, context):
    tema = " ".join(context.args)
    await update.message.reply_text("🔥 Criando logo grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("logo", tema), 1024, 1024, 88))

async def thumbnail(update, context):
    tema = " ".join(context.args)
    await update.message.reply_text("🧲 Criando thumbnail grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("thumbnail", tema), 1280, 720, 99))

async def poster(update, context):
    tema = " ".join(context.args)
    await update.message.reply_text("🎬 Criando poster grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("poster", tema), 1024, 1536, 111))

async def banner(update, context):
    tema = " ".join(context.args)
    await update.message.reply_text("🖼 Criando banner grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("banner", tema), 1536, 768, 222))

async def promptimg(u,c): await generic(u,c,"promptimg","Crie 5 prompts ultra avançados para imagem IA.","visual")
async def video(u,c): await generic(u,c,"video","Crie conceito completo de vídeo cinematográfico.","video")
async def roteiro(u,c): await generic(u,c,"roteiro","Crie roteiro completo com hook, cenas, narração e CTA.","video")
async def shorts(u,c): await generic(u,c,"shorts","Crie roteiro Shorts/Reels/TikTok.","video")
async def anuncio(u,c): await generic(u,c,"anuncio","Crie anúncio em vídeo com dor, promessa, oferta e CTA.","video")
async def promptvideo(u,c): await generic(u,c,"promptvideo","Crie 5 prompts cinematográficos para vídeo IA em 9:16.","video")

async def roadmap(u,c): await generic(u,c,"roadmap","Crie roadmap executivo com plano de 7 e 30 dias.","ceo")
async def branding(u,c): await generic(u,c,"branding","Crie branding completo.","branding")
async def conteudo(u,c): await generic(u,c,"conteudo","Crie conteúdo viral.","conteudo")
async def oferta(u,c): await generic(u,c,"oferta","Crie oferta irresistível.","vendas")
async def funil(u,c): await generic(u,c,"funil","Crie funil de vendas gratuito.","vendas")
async def saas(u,c): await generic(u,c,"saas","Crie arquitetura SaaS com MVP e stack grátis.","dev")
async def site(u,c): await generic(u,c,"site","Crie site com HTML/CSS e deploy grátis.","dev")
async def app_cmd(u,c): await generic(u,c,"app","Crie app simples com MVP e stack grátis.","dev")
async def doc(u,c): await generic(u,c,"doc","Crie documento profissional.","docs")
async def proposta(u,c): await generic(u,c,"proposta","Crie proposta comercial.","docs")
async def briefing(u,c): await generic(u,c,"briefing","Crie briefing profissional.","docs")

def save_assistant(tipo, conteudo):
    data = load_json(FILES["assistant"], [])
    data.append({"tipo": tipo, "conteudo": conteudo, "data": str(datetime.now(TZ))})
    save_json(FILES["assistant"], data)

async def agenda(update, context):
    save_assistant("agenda", " ".join(context.args))
    await update.message.reply_text("📅 Agenda salva.")

async def lembrete(update, context):
    save_assistant("lembrete", " ".join(context.args))
    await update.message.reply_text("🔔 Lembrete salvo.")

async def dia(update, context):
    resp = ask_ai(f"Monte meu plano de hoje com tarefas {load_json(FILES['tasks'], [])} e agenda {load_json(FILES['assistant'], [])}", "assistente")
    await send_long(update, resp)

async def ativar(update, context):
    config = load_json(FILES["config"], {})
    config["chat_id"] = update.effective_chat.id
    save_json(FILES["config"], config)
    await update.message.reply_text("✅ Execução automática ativada.")

async def agendar(update, context):
    txt = " ".join(context.args)
    try:
        hora, acao = txt.split(" ", 1)
        datetime.strptime(hora, "%H:%M")
        data = load_json(FILES["schedules"], [])
        data.append({"hora": hora, "acao": acao, "ativo": True, "ultimo_disparo": "", "data": str(datetime.now(TZ))})
        save_json(FILES["schedules"], data)
        await update.message.reply_text(f"⏰ Agendado: {hora} — {acao}")
    except:
        await update.message.reply_text("Use: /agendar 09:00 revisar tarefas")

async def agendamentos(update, context):
    data = load_json(FILES["schedules"], [])
    text = "⏰ AGENDAMENTOS:\n\n"
    for i, s in enumerate(data, 1):
        text += f"{i}. {s['hora']} — {s['acao']} — {'ativo' if s.get('ativo') else 'pausado'}\n"
    await send_long(update, text if data else "Nenhum agendamento.")

async def backup(update, context):
    data = {k: load_json(v, {}) for k,v in FILES.items()}
    with open("backup_streetcore.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    await update.message.reply_document(document=open("backup_streetcore.json", "rb"))

async def exportar(update, context):
    items = load_json(FILES["items"], [])
    text = "EXPORTAÇÃO STREETCORE\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['tipo']} — {item['tema']}\n\n{item['conteudo']}\n\n---\n"
    with open("exportacao_streetcore.txt", "w", encoding="utf-8") as f:
        f.write(text)
    await update.message.reply_document(document=open("exportacao_streetcore.txt", "rb"))

async def listar(update, context):
    items = load_json(FILES["items"], [])
    text = "📚 ITENS:\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. [{item['tipo']}] {item['tema']}\n"
    await send_long(update, text if items else "Nada salvo.")

async def buscar(update, context):
    q = " ".join(context.args).lower()
    items = load_json(FILES["items"], [])
    text = f"🔎 BUSCA: {q}\n\n"
    found = False
    for i, item in enumerate(items, 1):
        if q in json.dumps(item, ensure_ascii=False).lower():
            found = True
            text += f"{i}. [{item['tipo']}] {item['tema']}\n"
    await send_long(update, text if found else "Nada encontrado.")

async def veritem(update, context):
    try:
        n = int(context.args[0])
        item = load_json(FILES["items"], [])[n-1]
        await send_long(update, f"📌 {item['tipo']} — {item['tema']}\n\n{item['conteudo']}")
    except:
        await update.message.reply_text("Use: /veritem 1")

async def scheduled_checker(context):
    config = load_json(FILES["config"], {})
    chat = config.get("chat_id")
    if not chat:
        return
    now = datetime.now(TZ)
    cur = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")
    data = load_json(FILES["schedules"], [])
    changed = False
    for s in data:
        if s.get("ativo") and s.get("hora") == cur and s.get("ultimo_disparo") != today:
            acao = s.get("acao", "")
            if sensitive(acao):
                idx = create_approval(acao, "agendamento")
                await context.bot.send_message(chat_id=chat, text=f"🛡 Aprovação necessária #{idx}: {acao}")
            else:
                resp = ask_ai(f"Execute este agendamento: {acao}", "assistente")
                await context.bot.send_message(chat_id=chat, text=f"⏰ AGENDAMENTO\n{acao}")
                for i in range(0, len(resp), 3900):
                    await context.bot.send_message(chat_id=chat, text=resp[i:i+3900])
            s["ultimo_disparo"] = today
            changed = True
    if changed:
        save_json(FILES["schedules"], data)

async def handle_message(update, context):
    msg = update.message.text
    auto_memory(msg)

    if sensitive(msg):
        idx = create_approval(msg, "mensagem")
        await update.message.reply_text(f"🛡 Ação sensível. Aprovação criada #{idx}.")
        return

    low = msg.lower()
    if "plano para hoje" in low or "planeje meu dia" in low:
        resp = ask_ai(f"Monte meu plano de hoje com tarefas {load_json(FILES['tasks'], [])}", "assistente")
        await send_long(update, resp)
        return

    resp = ask_ai(msg)
    await send_long(update, resp)

# DASHBOARD WEB

web = Flask(__name__)

HTML = """
<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>StreetCore AI Dashboard</title>
<style>
body{margin:0;background:#07070a;color:#f5f5f5;font-family:Arial}
header{padding:28px;background:linear-gradient(135deg,#111,#2b0055);border-bottom:1px solid #333}
h1{margin:0;font-size:32px}
p{color:#bbb}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;padding:20px}
.card{background:#111;border:1px solid #292929;border-radius:18px;padding:18px;box-shadow:0 0 25px rgba(130,0,255,.12)}
.card h2{margin-top:0;color:#b56cff}
pre{white-space:pre-wrap;background:#080808;border-radius:12px;padding:12px;max-height:320px;overflow:auto}
.badge{font-size:34px;font-weight:bold}
</style>
</head>
<body>
<header>
<h1>🔥 StreetCore AI Dashboard</h1>
<p>Painel visual gratuito do seu agente IA.</p>
</header>
<div class="grid">
<div class="card"><h2>Memória</h2><div class="badge">{{memory_count}}</div></div>
<div class="card"><h2>Tarefas</h2><div class="badge">{{tasks_count}}</div></div>
<div class="card"><h2>Itens Salvos</h2><div class="badge">{{items_count}}</div></div>
<div class="card"><h2>Agenda</h2><div class="badge">{{assistant_count}}</div></div>
<div class="card"><h2>Agendamentos</h2><div class="badge">{{schedules_count}}</div></div>
<div class="card"><h2>Aprovações</h2><div class="badge">{{approvals_count}}</div></div>
</div>
<div class="grid">
<div class="card"><h2>Memória</h2><pre>{{memory}}</pre></div>
<div class="card"><h2>Tarefas</h2><pre>{{tasks}}</pre></div>
<div class="card"><h2>Últimos Itens</h2><pre>{{items}}</pre></div>
<div class="card"><h2>Agenda/Lembretes</h2><pre>{{assistant}}</pre></div>
</div>
</body>
</html>
"""

@web.route("/")
def dashboard():
    mem = memory()
    tasks = load_json(FILES["tasks"], [])
    items = load_json(FILES["items"], [])
    assistant = load_json(FILES["assistant"], [])
    schedules = load_json(FILES["schedules"], [])
    approvals = load_json(FILES["approvals"], [])

    return render_template_string(
        HTML,
        memory_count=len(mem.get("perfil", {})) + len(mem.get("objetivos", [])) + len(mem.get("preferencias", [])),
        tasks_count=len(tasks),
        items_count=len(items),
        assistant_count=len(assistant),
        schedules_count=len(schedules),
        approvals_count=len(approvals),
        memory=json.dumps(mem, ensure_ascii=False, indent=2),
        tasks=json.dumps(tasks[-10:], ensure_ascii=False, indent=2),
        items=json.dumps(items[-10:], ensure_ascii=False, indent=2),
        assistant=json.dumps(assistant[-10:], ensure_ascii=False, indent=2)
    )

@web.route("/api/status")
def api_status():
    return jsonify({
        "memory": memory(),
        "tasks": load_json(FILES["tasks"], []),
        "items": load_json(FILES["items"], []),
        "assistant": load_json(FILES["assistant"], []),
        "schedules": load_json(FILES["schedules"], []),
        "approvals": load_json(FILES["approvals"], [])
    })

def run_web():
    web.run(host="0.0.0.0", port=PORT)

tg = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

commands = {
    "start": start, "menu": menu, "status": status, "memoria": memoria,
    "perfil": perfil, "objetivo": objetivo, "preferencia": preferencia,
    "tarefa": tarefa, "tarefas": tarefas, "check": check, "concluir": concluir,
    "ceo": ceo, "brandagent": brandagent, "contentagent": contentagent,
    "salesagent": salesagent, "devagent": devagent, "autoagent": autoagent,
    "visualagent": visualagent, "videoagent": videoagent, "docsagent": docsagent,
    "agent": agent,
    "imagem": imagem, "logo": logo, "thumbnail": thumbnail, "poster": poster, "banner": banner, "promptimg": promptimg,
    "video": video, "roteiro": roteiro, "shorts": shorts, "anuncio": anuncio, "promptvideo": promptvideo,
    "roadmap": roadmap, "branding": branding, "conteudo": conteudo, "oferta": oferta, "funil": funil,
    "saas": saas, "site": site, "app": app_cmd, "doc": doc, "proposta": proposta, "briefing": briefing,
    "agenda": agenda, "lembrete": lembrete, "dia": dia,
    "ativar": ativar, "agendar": agendar, "agendamentos": agendamentos,
    "backup": backup, "exportar": exportar, "listar": listar, "buscar": buscar, "veritem": veritem
}

for name, func in commands.items():
    tg.add_handler(CommandHandler(name, func))

tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
tg.job_queue.run_repeating(scheduled_checker, interval=60, first=10)

threading.Thread(target=run_web, daemon=True).start()

print("🔥 STREETCORE AI + WEB DASHBOARD ONLINE")
tg.run_polling()
