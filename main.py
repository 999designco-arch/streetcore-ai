import os, json, urllib.parse
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

FILES = {
    "memory": "memory.json",
    "tasks": "tasks.json",
    "items": "items.json",
    "assistant": "assistant.json"
}

MASTER_PROMPT = """
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, COO, estrategista, diretor criativo, programador, vendedor, social media,
engenheiro de automação, arquiteto de SaaS e assistente pessoal.
Explique passo a passo, como se estivesse pegando na mão do usuário.
Seja prático, premium, claro e operacional.
"""

AGENTS = {
    "ceo": "Você é o CEO Agent. Foque em visão, prioridade, execução, dinheiro, escala e decisões.",
    "branding": "Você é o Branding Agent. Foque em identidade, posicionamento, estética, tom de voz e marca.",
    "conteudo": "Você é o Content Agent. Foque em conteúdo viral, Reels, TikTok, Instagram e crescimento orgânico.",
    "vendas": "Você é o Sales Agent. Foque em oferta, copy, funil, WhatsApp, objeções e fechamento.",
    "dev": "Você é o Dev Agent. Foque em programação, sites, apps, APIs, banco, debug e deploy grátis.",
    "automacao": "Você é o Automation Agent. Foque em automações gratuitas, n8n, fluxos, scripts e produtividade.",
    "assistente": "Você é o Personal Assistant Agent. Foque em agenda, rotina, hábitos, foco e organização."
}

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def memory():
    base = load_json(FILES["memory"], {})
    base.setdefault("perfil", {})
    base.setdefault("objetivos", [])
    base.setdefault("preferencias", [])
    return base

def save_memory(mem):
    save_json(FILES["memory"], mem)

def save_item(tipo, tema, conteudo):
    data = load_json(FILES["items"], [])
    data.append({"tipo": tipo, "tema": tema, "conteudo": conteudo, "data": str(datetime.now())})
    save_json(FILES["items"], data)

def auto_memory(msg):
    mem = memory()
    text = msg.lower()

    try:
        if "meu nome é" in text:
            mem["perfil"]["nome"] = text.split("meu nome é")[1].strip()
        if "minha marca é" in text:
            mem["perfil"]["marca"] = text.split("minha marca é")[1].strip()
        if "meu nicho é" in text:
            mem["perfil"]["nicho"] = text.split("meu nicho é")[1].strip()
        if "quero criar" in text:
            objetivo = text.split("quero criar")[1].strip()
            if objetivo not in mem["objetivos"]:
                mem["objetivos"].append(objetivo)
    except:
        pass

    mem["ultima_interacao"] = str(datetime.now())
    save_memory(mem)

def ask_ai(prompt, agent=None):
    mem = json.dumps(memory(), ensure_ascii=False, indent=2)
    agent_prompt = AGENTS.get(agent, "")
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT + "\n\n" + agent_prompt + f"\n\nMEMÓRIA:\n{mem}"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=4000
    )
    return r.choices[0].message.content

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

def image_url(prompt):
    p = urllib.parse.quote(f"ultra realistic cinematic image, street luxury futuristic, cyberpunk premium, 8k. {prompt}")
    return f"https://image.pollinations.ai/prompt/{p}?width=1024&height=1024&seed=77"

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore AI online. Digite /menu para ver os comandos.")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI — CENTRAL

ESSENCIAL:
/status /menu /ajuda /comandos

MEMÓRIA AVANÇADA:
/memoria
/perfil
/objetivo
/objetivos
/preferencia
/preferencias
/limparmemoria
/resetar

TAREFAS:
/tarefa /tarefas /check /concluir

IMAGEM:
/imagem /logo

OPERAÇÃO:
/roadmap /automacao /conteudo /oferta /branding /saas /site /doc

ASSISTENTE:
/agenda /lembrete /lembretes /rotina /habito /habitos /dia

MULTIAGENTES:
/ceo /brandagent /contentagent /salesagent /devagent /autoagent /agent
""")

async def ajuda(update, context):
    await update.message.reply_text("""
🧠 COMO USAR

Exemplos:

/perfil nome = Rafael
/objetivo criar uma marca streetwear futurista
/preferencia usar apenas ferramentas grátis
/memoria

/agent quero lançar minha marca do zero
/ceo como monetizar meu agente IA
/branding Street Graff
/dia
""")

async def comandos(update, context):
    await update.message.reply_text("""
📌 COMANDOS

/start /status /menu /ajuda /comandos

/memoria /perfil /objetivo /objetivos /preferencia /preferencias /limparmemoria /resetar

/tarefa /tarefas /check /concluir
/imagem /logo
/roadmap /automacao /conteudo /oferta /branding /saas /site /doc
/agenda /lembrete /lembretes /rotina /habito /habitos /dia
/ceo /brandagent /contentagent /salesagent /devagent /autoagent /agent
""")

async def status(update, context):
    mem = memory()
    await update.message.reply_text(f"""
🚀 STATUS

Perfil: {len(mem.get("perfil", {}))} itens
Objetivos: {len(mem.get("objetivos", []))}
Preferências: {len(mem.get("preferencias", []))}
Tarefas: {len(load_json(FILES["tasks"], []))}
Itens salvos: {len(load_json(FILES["items"], []))}
Assistente pessoal: {len(load_json(FILES["assistant"], []))}

Sistema: ONLINE
IA: Groq grátis
Imagem: Pollinations grátis
Modo: MULTIAGENTES + MEMÓRIA AVANÇADA
""")

async def memoria(update, context):
    mem = memory()
    text = "🧠 MEMÓRIA AVANÇADA:\n\n"

    text += "👤 PERFIL:\n"
    for k, v in mem.get("perfil", {}).items():
        text += f"• {k}: {v}\n"

    text += "\n🎯 OBJETIVOS:\n"
    for i, obj in enumerate(mem.get("objetivos", []), 1):
        text += f"{i}. {obj}\n"

    text += "\n⚙️ PREFERÊNCIAS:\n"
    for i, pref in enumerate(mem.get("preferencias", []), 1):
        text += f"{i}. {pref}\n"

    text += f"\nÚltima interação: {mem.get('ultima_interacao', 'nenhuma')}"
    await send_long(update, text)

async def perfil(update, context):
    texto = " ".join(context.args)
    mem = memory()

    if not texto:
        await memoria(update, context)
        return

    if "=" not in texto:
        await update.message.reply_text("Use assim:\n/perfil nome = Rafael")
        return

    chave, valor = texto.split("=", 1)
    mem["perfil"][chave.strip()] = valor.strip()
    save_memory(mem)

    await update.message.reply_text(f"✅ Perfil salvo:\n{chave.strip()} = {valor.strip()}")

async def objetivo(update, context):
    texto = " ".join(context.args)
    if not texto:
        await update.message.reply_text("Use:\n/objetivo criar uma marca streetwear futurista")
        return

    mem = memory()
    mem["objetivos"].append(texto)
    save_memory(mem)

    await update.message.reply_text(f"🎯 Objetivo salvo:\n{texto}")

async def objetivos(update, context):
    mem = memory()
    objs = mem.get("objetivos", [])
    if not objs:
        await update.message.reply_text("Nenhum objetivo salvo.")
        return

    text = "🎯 OBJETIVOS:\n\n"
    for i, obj in enumerate(objs, 1):
        text += f"{i}. {obj}\n"
    await send_long(update, text)

async def preferencia(update, context):
    texto = " ".join(context.args)
    if not texto:
        await update.message.reply_text("Use:\n/preferencia usar apenas ferramentas gratuitas")
        return

    mem = memory()
    mem["preferencias"].append(texto)
    save_memory(mem)

    await update.message.reply_text(f"⚙️ Preferência salva:\n{texto}")

async def preferencias(update, context):
    mem = memory()
    prefs = mem.get("preferencias", [])
    if not prefs:
        await update.message.reply_text("Nenhuma preferência salva.")
        return

    text = "⚙️ PREFERÊNCIAS:\n\n"
    for i, pref in enumerate(prefs, 1):
        text += f"{i}. {pref}\n"
    await send_long(update, text)

async def limparmemoria(update, context):
    save_memory({"perfil": {}, "objetivos": [], "preferencias": []})
    await update.message.reply_text("🧹 Memória limpa. Tarefas e itens salvos não foram apagados.")

async def resetar(update, context):
    save_memory({"perfil": {}, "objetivos": [], "preferencias": []})
    save_json(FILES["tasks"], [])
    save_json(FILES["items"], [])
    save_json(FILES["assistant"], [])
    await update.message.reply_text("⚠️ Sistema resetado: memória, tarefas, itens e assistente foram apagados.")

async def tarefa(update, context):
    nome = " ".join(context.args)
    if not nome:
        await update.message.reply_text("Use:\n/tarefa descrição")
        return
    tasks = load_json(FILES["tasks"], [])
    tasks.append({"tarefa": nome, "status": "pendente", "data": str(datetime.now())})
    save_json(FILES["tasks"], tasks)
    await update.message.reply_text(f"✅ Tarefa criada:\n{nome}")

async def tarefas(update, context):
    tasks = load_json(FILES["tasks"], [])
    if not tasks:
        await update.message.reply_text("Nenhuma tarefa.")
        return
    text = "📝 TAREFAS:\n\n"
    for i, t in enumerate(tasks, 1):
        text += f"{i}. {t['tarefa']} — {t['status']}\n"
    await send_long(update, text)

async def check(update, context):
    tasks = load_json(FILES["tasks"], [])
    pend = [(i, t) for i, t in enumerate(tasks, 1) if t["status"] == "pendente"]
    if not pend:
        await update.message.reply_text("🔥 Nenhuma pendência.")
        return
    text = "⚠️ PENDENTES:\n\n"
    for i, t in pend:
        text += f"{i}. {t['tarefa']}\n"
    text += "\nUse /concluir número"
    await send_long(update, text)

async def concluir(update, context):
    try:
        n = int(context.args[0])
        tasks = load_json(FILES["tasks"], [])
        tasks[n - 1]["status"] = "concluída"
        save_json(FILES["tasks"], tasks)
        await update.message.reply_text("✅ Tarefa concluída.")
    except:
        await update.message.reply_text("Use assim:\n/concluir 1")

async def imagem(update, context):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Use:\n/imagem descrição")
        return
    await update.message.reply_text("🎨 Gerando imagem...")
    await update.message.reply_photo(photo=image_url(prompt))

async def logo(update, context):
    tema = " ".join(context.args)
    await update.message.reply_text("🔥 Criando logo...")
    await update.message.reply_photo(photo=image_url(f"minimal futuristic luxury logo, white background, premium branding, {tema}"))

async def generic(update, context, tipo, prompt_base, agent=None):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text(f"Use:\n/{tipo} tema")
        return
    resposta = ask_ai(f"{prompt_base}\n\nTema:\n{tema}", agent)
    save_item(tipo, tema, resposta)
    await send_long(update, resposta)

async def roadmap(update, context): await generic(update, context, "roadmap", "Crie roadmap executivo completo com estratégia, execução, monetização, ferramentas grátis, plano de 7 dias e 30 dias.", "ceo")
async def automacao(update, context): await generic(update, context, "automacao", "Crie automação gratuita com ferramentas grátis, fluxo, passo a passo, execução e erros comuns.", "automacao")
async def conteudo(update, context): await generic(update, context, "conteudo", "Crie conteúdo viral premium para Instagram/TikTok com gancho, legenda, CTA, hashtags e ideia visual.", "conteudo")
async def oferta(update, context): await generic(update, context, "oferta", "Crie oferta irresistível com dor, promessa, mecanismo único, bônus, urgência ética, preço sugerido e CTA.", "vendas")
async def branding(update, context): await generic(update, context, "branding", "Crie branding completo com essência, posicionamento, público, personalidade, tom de voz, paleta, manifesto e próximos passos.", "branding")
async def saas(update, context): await generic(update, context, "saas", "Crie arquitetura completa de SaaS usando ferramentas grátis, incluindo MVP, features, stack, banco, login, dashboard, monetização e roadmap.", "dev")
async def site(update, context): await generic(update, context, "site", "Crie site completo com estrutura, copy, design, HTML/CSS simples, como testar e publicar grátis.", "dev")
async def doc(update, context): await generic(update, context, "doc", "Crie documento profissional completo, organizado, claro, pronto para copiar e usar.", "ceo")

def save_assistant(tipo, conteudo):
    data = load_json(FILES["assistant"], [])
    data.append({"tipo": tipo, "conteudo": conteudo, "data": str(datetime.now())})
    save_json(FILES["assistant"], data)

async def agenda(update, context):
    item = " ".join(context.args)
    if not item:
        await update.message.reply_text("Use:\n/agenda compromisso")
        return
    save_assistant("agenda", item)
    await update.message.reply_text(f"📅 Agenda salva:\n{item}")

async def lembrete(update, context):
    item = " ".join(context.args)
    if not item:
        await update.message.reply_text("Use:\n/lembrete algo")
        return
    save_assistant("lembrete", item)
    await update.message.reply_text(f"🔔 Lembrete salvo:\n{item}")

async def lembretes(update, context):
    data = load_json(FILES["assistant"], [])
    lembs = [x for x in data if x["tipo"] in ["lembrete", "agenda"]]
    if not lembs:
        await update.message.reply_text("Nenhum lembrete ou agenda salvo.")
        return
    text = "🔔 LEMBRETES / AGENDA:\n\n"
    for i, x in enumerate(lembs, 1):
        text += f"{i}. {x['tipo']}: {x['conteudo']}\n"
    await send_long(update, text)

async def rotina(update, context):
    tema = " ".join(context.args) or "minha rotina ideal"
    resposta = ask_ai(f"Crie rotina diária prática e inteligente para: {tema}", "assistente")
    save_assistant("rotina", resposta)
    await send_long(update, resposta)

async def habito(update, context):
    item = " ".join(context.args)
    if not item:
        await update.message.reply_text("Use:\n/habito hábito")
        return
    save_assistant("habito", item)
    await update.message.reply_text(f"✅ Hábito salvo:\n{item}")

async def habitos(update, context):
    data = load_json(FILES["assistant"], [])
    hs = [x for x in data if x["tipo"] == "habito"]
    if not hs:
        await update.message.reply_text("Nenhum hábito salvo.")
        return
    text = "✅ HÁBITOS:\n\n"
    for i, x in enumerate(hs, 1):
        text += f"{i}. {x['conteudo']}\n"
    await send_long(update, text)

async def dia(update, context):
    tasks = load_json(FILES["tasks"], [])
    assist = load_json(FILES["assistant"], [])
    resposta = ask_ai(f"""
Monte meu plano de hoje.

Tarefas:
{tasks}

Agenda, lembretes e hábitos:
{assist}

Inclua prioridade máxima, agenda, 3 tarefas essenciais, hábitos, bloco de foco e próximo passo.
""", "assistente")
    await send_long(update, resposta)

async def ceo(update, context): await generic(update, context, "ceo_agent", "Analise como CEO e entregue estratégia, prioridade, plano de ação e próximos passos.", "ceo")
async def brandagent(update, context): await generic(update, context, "branding_agent", "Analise como diretor de branding premium e entregue identidade, posicionamento, estética e tom de voz.", "branding")
async def contentagent(update, context): await generic(update, context, "content_agent", "Analise como estrategista de conteúdo viral e entregue calendário, ideias, roteiros e execução.", "conteudo")
async def salesagent(update, context): await generic(update, context, "sales_agent", "Analise como especialista em vendas e entregue oferta, copy, funil e fechamento.", "vendas")
async def devagent(update, context): await generic(update, context, "dev_agent", "Analise como programador full-stack e entregue arquitetura, stack grátis, código/estrutura e deploy.", "dev")
async def autoagent(update, context): await generic(update, context, "automation_agent", "Analise como engenheiro de automação e entregue fluxo, ferramentas grátis, execução e teste.", "automacao")

async def agent(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/agent problema ou objetivo")
        return
    prompt = f"""
Resolva este objetivo usando múltiplos agentes internos:

{tema}

Estruture:
1. CEO Agent
2. Branding Agent
3. Content Agent
4. Sales Agent
5. Dev Agent
6. Automation Agent
7. Personal Assistant Agent
8. Plano final integrado
9. Próximo passo imediato
"""
    resposta = ask_ai(prompt)
    save_item("multiagent", tema, resposta)
    await send_long(update, resposta)

async def handle_message(update, context):
    msg = update.message.text
    auto_memory(msg)
    resposta = ask_ai(msg)
    await send_long(update, resposta)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

commands = {
    "start": start, "menu": menu, "ajuda": ajuda, "comandos": comandos,
    "status": status, "memoria": memoria,
    "perfil": perfil, "objetivo": objetivo, "objetivos": objetivos,
    "preferencia": preferencia, "preferencias": preferencias,
    "limparmemoria": limparmemoria, "resetar": resetar,
    "tarefa": tarefa, "tarefas": tarefas, "check": check, "concluir": concluir,
    "imagem": imagem, "logo": logo,
    "roadmap": roadmap, "automacao": automacao, "conteudo": conteudo, "oferta": oferta,
    "branding": branding, "saas": saas, "site": site, "doc": doc,
    "agenda": agenda, "lembrete": lembrete, "lembretes": lembretes,
    "rotina": rotina, "habito": habito, "habitos": habitos, "dia": dia,
    "ceo": ceo, "brandagent": brandagent, "contentagent": contentagent,
    "salesagent": salesagent, "devagent": devagent, "autoagent": autoagent,
    "agent": agent
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI ADVANCED MEMORY MODE ONLINE")
app.run_polling()
