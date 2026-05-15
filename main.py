import os, json, urllib.parse, traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
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
Aja como CEO, COO, estrategista, diretor criativo, growth hacker, programador,
vendedor, social media, engenheiro de automação, designer, roteirista e assistente pessoal.
Explique passo a passo, como se estivesse pegando na mão do usuário.
Seja prático, premium, claro, seguro e orientado à execução.
Peça aprovação antes de ações sensíveis.
"""

AGENTS = {
    "ceo": "CEO Agent: estratégia, monetização, prioridade, escala e decisão.",
    "branding": "Branding Agent: identidade, posicionamento, estética, tom de voz e marca.",
    "conteudo": "Content Agent: conteúdo viral, Reels, TikTok, Instagram e calendário.",
    "vendas": "Sales Agent: oferta, copy, funil, WhatsApp, objeções e conversão.",
    "dev": "Dev Agent: código, sites, apps, APIs, banco, debug e deploy grátis.",
    "automacao": "Automation Agent: automações gratuitas, fluxos, n8n, scripts e produtividade.",
    "visual": "Visual Agent: imagens, logos, thumbnails, banners e direção de arte.",
    "video": "Video Agent: roteiros, cenas, anúncios, Shorts e prompts cinematográficos.",
    "docs": "Docs Agent: documentos, propostas, briefings, contratos simples e planos.",
    "assistente": "Personal Assistant Agent: agenda, lembretes, rotina, hábitos e foco."
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

def is_owner(update):
    config = load_json(FILES["config"], {})
    owner = config.get("owner_id")
    if not owner:
        return True
    return update.effective_user.id == owner

async def guard(update):
    if not is_owner(update):
        await update.message.reply_text("🔒 Acesso negado. Este agente já possui dono.")
        return False
    return True

def save_item(tipo, tema, conteudo):
    data = load_json(FILES["items"], [])
    data.append({"tipo": tipo, "tema": tema, "conteudo": conteudo, "data": str(datetime.now(TZ))})
    save_json(FILES["items"], data)

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
    if not text:
        text = "Sem resposta."
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

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

def sensitive(text):
    return any(w in text.lower() for w in SENSITIVE)

def approval(acao, origem):
    data = load_json(FILES["approvals"], [])
    data.append({"acao": acao, "origem": origem, "status": "pendente", "data": str(datetime.now(TZ))})
    save_json(FILES["approvals"], data)
    return len(data)

def img_url(prompt, w=1024, h=1024, seed=77):
    p = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{p}?width={w}&height={h}&seed={seed}"

def img_prompt(tipo, tema):
    base = f"ultra realistic cinematic image, street luxury futuristic, cyberpunk premium, dramatic lighting, 8k, highly detailed. Theme: {tema}"
    if tipo == "logo":
        return f"minimal futuristic luxury logo, clean vector, white background, premium streetwear branding. Brand: {tema}"
    if tipo == "thumbnail":
        return f"viral YouTube thumbnail, cinematic, high contrast, bold visual, high CTR, premium futuristic style. Theme: {tema}"
    if tipo == "banner":
        return f"wide premium cinematic banner, futuristic luxury brand campaign, clean space for headline. Theme: {tema}"
    if tipo == "poster":
        return f"cinematic poster, premium futuristic street luxury, neon, dramatic advertising composition. Theme: {tema}"
    return base

async def start(update, context):
    config = load_json(FILES["config"], {})
    if not config.get("owner_id"):
        config["owner_id"] = update.effective_user.id
        config["chat_id"] = update.effective_chat.id
        save_json(FILES["config"], config)
    await update.message.reply_text("🔥 StreetCore AI MASTER ULTRA online. Digite /menu.")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI MASTER ULTRA

ESSENCIAL:
/menu /status /memoria /backup /exportar

MEMÓRIA:
/perfil nome = Rafael
/objetivo criar empresa de IA
/preferencia usar ferramentas grátis

TAREFAS:
/tarefa texto
/tarefas
/check
/concluir 1
/apagartarefa 1

MULTIAGENTES:
/agent objetivo
/ceo /brandagent /contentagent /salesagent /devagent /autoagent /visualagent /videoagent /docsagent

IMAGEM:
/imagem /logo /thumbnail /poster /banner /promptimg

VÍDEO:
/video /roteiro /cenas /shorts /anuncio /promptvideo

NEGÓCIOS:
/roadmap /branding /conteudo /oferta /funil /saas /site /app /doc /proposta /briefing

ASSISTENTE:
/agenda /lembrete /lembretes /rotina /habito /dia

AUTOMAÇÃO:
/ativar
/agendar 09:00 revisar tarefas
/agendamentos
/pausaragendamento 1
/reativaragendamento 1
/removeragendamento 1

SEGURANÇA:
/pendentesaprovacao
/aprovar 1
/rejeitar 1

ARQUIVO INTERNO:
/listar
/veritem 1
/buscar palavra
/historico
/apagaritem 1
""")

async def status(update, context):
    if not await guard(update): return
    mem = memory()
    pend = [a for a in load_json(FILES["approvals"], []) if a.get("status") == "pendente"]
    await update.message.reply_text(f"""
🚀 STATUS ULTRA

Perfil: {len(mem["perfil"])}
Objetivos: {len(mem["objetivos"])}
Preferências: {len(mem["preferencias"])}
Tarefas: {len(load_json(FILES["tasks"], []))}
Itens salvos: {len(load_json(FILES["items"], []))}
Agenda/Lembretes: {len(load_json(FILES["assistant"], []))}
Agendamentos: {len(load_json(FILES["schedules"], []))}
Aprovações pendentes: {len(pend)}

Sistema: ONLINE
Modo: MASTER ULTRA
""")

async def memoria(update, context):
    if not await guard(update): return
    mem = memory()
    text = "🧠 MEMÓRIA\n\n👤 PERFIL:\n"
    for k, v in mem["perfil"].items():
        text += f"• {k}: {v}\n"
    text += "\n🎯 OBJETIVOS:\n"
    for i, x in enumerate(mem["objetivos"], 1):
        text += f"{i}. {x}\n"
    text += "\n⚙️ PREFERÊNCIAS:\n"
    for i, x in enumerate(mem["preferencias"], 1):
        text += f"{i}. {x}\n"
    await send_long(update, text)

async def perfil(update, context):
    if not await guard(update): return
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
    if not await guard(update): return
    txt = " ".join(context.args)
    mem = memory()
    mem["objetivos"].append(txt)
    save_memory(mem)
    await update.message.reply_text("🎯 Objetivo salvo.")

async def preferencia(update, context):
    if not await guard(update): return
    txt = " ".join(context.args)
    mem = memory()
    mem["preferencias"].append(txt)
    save_memory(mem)
    await update.message.reply_text("⚙️ Preferência salva.")

async def tarefa(update, context):
    if not await guard(update): return
    txt = " ".join(context.args)
    if not txt:
        await update.message.reply_text("Use: /tarefa texto")
        return
    tasks = load_json(FILES["tasks"], [])
    tasks.append({"tarefa": txt, "status": "pendente", "data": str(datetime.now(TZ))})
    save_json(FILES["tasks"], tasks)
    await update.message.reply_text("✅ Tarefa criada.")

async def tarefas(update, context):
    if not await guard(update): return
    tasks = load_json(FILES["tasks"], [])
    if not tasks:
        await update.message.reply_text("Nenhuma tarefa.")
        return
    text = "📝 TAREFAS:\n\n"
    for i, t in enumerate(tasks, 1):
        text += f"{i}. {t['tarefa']} — {t['status']}\n"
    await send_long(update, text)

async def check(update, context):
    if not await guard(update): return
    tasks = load_json(FILES["tasks"], [])
    text = "⚠️ PENDENTES:\n\n"
    found = False
    for i, t in enumerate(tasks, 1):
        if t.get("status") == "pendente":
            found = True
            text += f"{i}. {t['tarefa']}\n"
    await send_long(update, text if found else "🔥 Nenhuma pendência.")

async def concluir(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        tasks = load_json(FILES["tasks"], [])
        tasks[n-1]["status"] = "concluída"
        save_json(FILES["tasks"], tasks)
        await update.message.reply_text("✅ Concluída.")
    except:
        await update.message.reply_text("Use: /concluir 1")

async def apagartarefa(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        tasks = load_json(FILES["tasks"], [])
        removed = tasks.pop(n-1)
        save_json(FILES["tasks"], tasks)
        await update.message.reply_text(f"🗑 Tarefa apagada: {removed['tarefa']}")
    except:
        await update.message.reply_text("Use: /apagartarefa 1")

async def generic(update, context, tipo, prompt, agent=None):
    if not await guard(update): return
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text(f"Use: /{tipo} tema")
        return
    resp = ask_ai(prompt + "\n\nTema:\n" + tema, agent)
    save_item(tipo, tema, resp)
    await send_long(update, resp)

async def ceo(u,c): await generic(u,c,"ceo","Analise como CEO com estratégia, monetização, riscos e próximos passos.","ceo")
async def brandagent(u,c): await generic(u,c,"branding","Crie branding premium completo.","branding")
async def contentagent(u,c): await generic(u,c,"conteudo","Crie estratégia de conteúdo viral.","conteudo")
async def salesagent(u,c): await generic(u,c,"vendas","Crie oferta, copy, funil e plano de vendas.","vendas")
async def devagent(u,c): await generic(u,c,"dev","Crie solução técnica com stack grátis, código e deploy.","dev")
async def autoagent(u,c): await generic(u,c,"automacao","Crie automação grátis passo a passo.","automacao")
async def visualagent(u,c): await generic(u,c,"visual","Crie direção visual premium e prompts de imagem.","visual")
async def videoagent(u,c): await generic(u,c,"video","Crie estratégia de vídeo, roteiro, cenas e prompts.","video")
async def docsagent(u,c): await generic(u,c,"docs","Crie documento profissional completo.","docs")

async def agent(update, context):
    if not await guard(update): return
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use: /agent objetivo")
        return
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
    if not await guard(update): return
    tema = " ".join(context.args)
    await update.message.reply_text("🎨 Gerando imagem grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("imagem", tema)))

async def logo(update, context):
    if not await guard(update): return
    tema = " ".join(context.args)
    await update.message.reply_text("🔥 Criando logo grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("logo", tema), 1024, 1024, 88))

async def thumbnail(update, context):
    if not await guard(update): return
    tema = " ".join(context.args)
    await update.message.reply_text("🧲 Criando thumbnail grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("thumbnail", tema), 1280, 720, 99))

async def poster(update, context):
    if not await guard(update): return
    tema = " ".join(context.args)
    await update.message.reply_text("🎬 Criando poster grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("poster", tema), 1024, 1536, 111))

async def banner(update, context):
    if not await guard(update): return
    tema = " ".join(context.args)
    await update.message.reply_text("🖼 Criando banner grátis...")
    await update.message.reply_photo(photo=img_url(img_prompt("banner", tema), 1536, 768, 222))

async def promptimg(u,c): await generic(u,c,"promptimg","Crie 5 prompts ultra avançados para imagem IA com versão em inglês.","visual")
async def video(u,c): await generic(u,c,"video","Crie conceito completo de vídeo cinematográfico.","video")
async def roteiro(u,c): await generic(u,c,"roteiro","Crie roteiro completo com hook, cenas, narração e CTA.","video")
async def cenas(u,c): await generic(u,c,"cenas","Crie lista de cenas cinematográficas com câmera, luz e prompts.","video")
async def shorts(u,c): await generic(u,c,"shorts","Crie roteiro Shorts/Reels/TikTok com hook, cortes, narração e CTA.","video")
async def anuncio(u,c): await generic(u,c,"anuncio","Crie anúncio em vídeo com dor, promessa, oferta e CTA.","video")
async def promptvideo(u,c): await generic(u,c,"promptvideo","Crie 5 prompts cinematográficos para vídeo IA em 9:16.","video")

async def roadmap(u,c): await generic(u,c,"roadmap","Crie roadmap executivo com plano de 7 e 30 dias.","ceo")
async def branding(u,c): await generic(u,c,"branding","Crie branding completo com paleta, tom, manifesto e posicionamento.","branding")
async def conteudo(u,c): await generic(u,c,"conteudo","Crie conteúdo viral com legenda, CTA, hashtags e ideia visual.","conteudo")
async def oferta(u,c): await generic(u,c,"oferta","Crie oferta irresistível com copy e CTA.","vendas")
async def funil(u,c): await generic(u,c,"funil","Crie funil de vendas usando ferramentas grátis.","vendas")
async def saas(u,c): await generic(u,c,"saas","Crie arquitetura SaaS com MVP, stack grátis e monetização.","dev")
async def site(u,c): await generic(u,c,"site","Crie site com HTML/CSS e deploy grátis.","dev")
async def app_cmd(u,c): await generic(u,c,"app","Crie app simples com MVP, telas e stack grátis.","dev")
async def doc(u,c): await generic(u,c,"doc","Crie documento profissional completo.","docs")
async def proposta(u,c): await generic(u,c,"proposta","Crie proposta comercial profissional.","docs")
async def briefing(u,c): await generic(u,c,"briefing","Crie briefing profissional completo.","docs")

def save_assistant(tipo, conteudo):
    data = load_json(FILES["assistant"], [])
    data.append({"tipo": tipo, "conteudo": conteudo, "data": str(datetime.now(TZ))})
    save_json(FILES["assistant"], data)

async def agenda(update, context):
    if not await guard(update): return
    save_assistant("agenda", " ".join(context.args))
    await update.message.reply_text("📅 Agenda salva.")

async def lembrete(update, context):
    if not await guard(update): return
    save_assistant("lembrete", " ".join(context.args))
    await update.message.reply_text("🔔 Lembrete salvo.")

async def lembretes(update, context):
    if not await guard(update): return
    data = load_json(FILES["assistant"], [])
    text = "🔔 ASSISTENTE:\n\n"
    for i, x in enumerate(data, 1):
        text += f"{i}. {x['tipo']}: {x['conteudo']}\n"
    await send_long(update, text)

async def rotina(u,c): await generic(u,c,"rotina","Crie rotina diária prática e inteligente.","assistente")

async def habito(update, context):
    if not await guard(update): return
    save_assistant("habito", " ".join(context.args))
    await update.message.reply_text("✅ Hábito salvo.")

async def dia(update, context):
    if not await guard(update): return
    resp = ask_ai(f"Monte meu plano de hoje com tarefas {load_json(FILES['tasks'], [])} e agenda {load_json(FILES['assistant'], [])}", "assistente")
    await send_long(update, resp)

async def ativar(update, context):
    config = load_json(FILES["config"], {})
    config["chat_id"] = update.effective_chat.id
    config.setdefault("owner_id", update.effective_user.id)
    save_json(FILES["config"], config)
    await update.message.reply_text("✅ Execução automática ativada.")

async def agendar(update, context):
    if not await guard(update): return
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
    if not await guard(update): return
    data = load_json(FILES["schedules"], [])
    text = "⏰ AGENDAMENTOS:\n\n"
    for i, s in enumerate(data, 1):
        st = "ativo" if s.get("ativo") else "pausado"
        text += f"{i}. {s['hora']} — {s['acao']} — {st}\n"
    await send_long(update, text)

async def pausaragendamento(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        data = load_json(FILES["schedules"], [])
        data[n-1]["ativo"] = False
        save_json(FILES["schedules"], data)
        await update.message.reply_text("⏸ Agendamento pausado.")
    except:
        await update.message.reply_text("Use: /pausaragendamento 1")

async def reativaragendamento(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        data = load_json(FILES["schedules"], [])
        data[n-1]["ativo"] = True
        save_json(FILES["schedules"], data)
        await update.message.reply_text("▶️ Agendamento reativado.")
    except:
        await update.message.reply_text("Use: /reativaragendamento 1")

async def removeragendamento(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        data = load_json(FILES["schedules"], [])
        data.pop(n-1)
        save_json(FILES["schedules"], data)
        await update.message.reply_text("🗑 Agendamento removido.")
    except:
        await update.message.reply_text("Use: /removeragendamento 1")

async def pendentesaprovacao(update, context):
    if not await guard(update): return
    data = load_json(FILES["approvals"], [])
    text = "🛡 APROVAÇÕES PENDENTES:\n\n"
    found = False
    for i, a in enumerate(data, 1):
        if a.get("status") == "pendente":
            found = True
            text += f"{i}. {a['acao']}\n"
    await send_long(update, text if found else "Nenhuma aprovação pendente.")

async def aprovar(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        data = load_json(FILES["approvals"], [])
        data[n-1]["status"] = "aprovado"
        save_json(FILES["approvals"], data)
        resp = ask_ai(f"Ação aprovada: {data[n-1]['acao']}. Entregue execução segura passo a passo.", "assistente")
        await send_long(update, resp)
    except:
        await update.message.reply_text("Use: /aprovar 1")

async def rejeitar(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        data = load_json(FILES["approvals"], [])
        data[n-1]["status"] = "rejeitado"
        save_json(FILES["approvals"], data)
        await update.message.reply_text("❌ Rejeitado.")
    except:
        await update.message.reply_text("Use: /rejeitar 1")

async def backup(update, context):
    if not await guard(update): return
    data = {k: load_json(v, {}) for k,v in FILES.items()}
    with open("backup_streetcore.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    await update.message.reply_document(document=open("backup_streetcore.json", "rb"))

async def exportar(update, context):
    if not await guard(update): return
    items = load_json(FILES["items"], [])
    text = "EXPORTAÇÃO STREETCORE\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. {item['tipo']} — {item['tema']}\n\n{item['conteudo']}\n\n---\n"
    with open("exportacao_streetcore.txt", "w", encoding="utf-8") as f:
        f.write(text)
    await update.message.reply_document(document=open("exportacao_streetcore.txt", "rb"))

async def listar(update, context):
    if not await guard(update): return
    items = load_json(FILES["items"], [])
    text = "📚 ITENS:\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. [{item['tipo']}] {item['tema']}\n"
    await send_long(update, text if items else "Nada salvo.")

async def veritem(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        item = load_json(FILES["items"], [])[n-1]
        await send_long(update, f"📌 {item['tipo']} — {item['tema']}\n\n{item['conteudo']}")
    except:
        await update.message.reply_text("Use: /veritem 1")

async def buscar(update, context):
    if not await guard(update): return
    q = " ".join(context.args).lower()
    items = load_json(FILES["items"], [])
    text = f"🔎 BUSCA: {q}\n\n"
    found = False
    for i, item in enumerate(items, 1):
        blob = json.dumps(item, ensure_ascii=False).lower()
        if q in blob:
            found = True
            text += f"{i}. [{item['tipo']}] {item['tema']}\n"
    await send_long(update, text if found else "Nada encontrado.")

async def historico(update, context): await listar(update, context)

async def apagaritem(update, context):
    if not await guard(update): return
    try:
        n = int(context.args[0])
        items = load_json(FILES["items"], [])
        removed = items.pop(n-1)
        save_json(FILES["items"], items)
        await update.message.reply_text(f"🗑 Item apagado: {removed['tema']}")
    except:
        await update.message.reply_text("Use: /apagaritem 1")

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
        if not s.get("ativo", True):
            continue
        if s.get("hora") == cur and s.get("ultimo_disparo") != today:
            acao = s.get("acao", "")
            if sensitive(acao):
                idx = approval(acao, "agendamento")
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
    if not await guard(update): return
    msg = update.message.text
    auto_memory(msg)
    if sensitive(msg):
        idx = approval(msg, "mensagem")
        await update.message.reply_text(f"🛡 Ação sensível. Aprovação criada #{idx}. Use /aprovar {idx} ou /rejeitar {idx}.")
        return

    low = msg.lower()
    if low.startswith("crie uma tarefa") or low.startswith("tarefa "):
        tasks = load_json(FILES["tasks"], [])
        tasks.append({"tarefa": msg, "status": "pendente", "data": str(datetime.now(TZ))})
        save_json(FILES["tasks"], tasks)
        await update.message.reply_text("✅ Tarefa criada por linguagem natural.")
        return

    if "plano para hoje" in low or "planeje meu dia" in low:
        resp = ask_ai(f"Monte meu plano de hoje com tarefas {load_json(FILES['tasks'], [])}", "assistente")
        await send_long(update, resp)
        return

    if "crie imagem" in low or "gerar imagem" in low:
        await update.message.reply_photo(photo=img_url(img_prompt("imagem", msg)))
        return

    resp = ask_ai(msg)
    await send_long(update, resp)

async def error_handler(update, context):
    err = "".join(traceback.format_exception(None, context.error, context.error.__traceback__))
    print(err)
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ Erro interno capturado. Me mande print dos logs se persistir.")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

commands = {
    "start": start, "menu": menu, "status": status, "memoria": memoria,
    "perfil": perfil, "objetivo": objetivo, "preferencia": preferencia,
    "tarefa": tarefa, "tarefas": tarefas, "check": check, "concluir": concluir, "apagartarefa": apagartarefa,
    "ceo": ceo, "brandagent": brandagent, "contentagent": contentagent, "salesagent": salesagent, "devagent": devagent,
    "autoagent": autoagent, "visualagent": visualagent, "videoagent": videoagent, "docsagent": docsagent, "agent": agent,
    "imagem": imagem, "logo": logo, "thumbnail": thumbnail, "poster": poster, "banner": banner, "promptimg": promptimg,
    "video": video, "roteiro": roteiro, "cenas": cenas, "shorts": shorts, "anuncio": anuncio, "promptvideo": promptvideo,
    "roadmap": roadmap, "branding": branding, "conteudo": conteudo, "oferta": oferta, "funil": funil, "saas": saas, "site": site, "app": app_cmd,
    "doc": doc, "proposta": proposta, "briefing": briefing,
    "agenda": agenda, "lembrete": lembrete, "lembretes": lembretes, "rotina": rotina, "habito": habito, "dia": dia,
    "ativar": ativar, "agendar": agendar, "agendamentos": agendamentos,
    "pausaragendamento": pausaragendamento, "reativaragendamento": reativaragendamento, "removeragendamento": removeragendamento,
    "pendentesaprovacao": pendentesaprovacao, "aprovar": aprovar, "rejeitar": rejeitar,
    "backup": backup, "exportar": exportar, "listar": listar, "veritem": veritem, "buscar": buscar, "historico": historico, "apagaritem": apagaritem
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_error_handler(error_handler)
app.job_queue.run_repeating(scheduled_checker, interval=60, first=10)

print("🔥 STREETCORE AI MASTER ULTRA FINAL ONLINE")
app.run_polling()
