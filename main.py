import os, json, urllib.parse
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
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, estrategista, diretor criativo, programador, vendedor,
engenheiro de automação, designer visual, roteirista de vídeos e assistente pessoal.
Explique passo a passo como se estivesse pegando na mão do usuário.
"""

AGENTS = {
    "ceo": "Você é o CEO Agent. Foque em estratégia, dinheiro, escala e prioridade.",
    "branding": "Você é o Branding Agent. Foque em marca, estética e posicionamento.",
    "conteudo": "Você é o Content Agent. Foque em conteúdo viral.",
    "vendas": "Você é o Sales Agent. Foque em oferta, copy e conversão.",
    "dev": "Você é o Dev Agent. Foque em tecnologia, código e deploy grátis.",
    "automacao": "Você é o Automation Agent. Foque em automações gratuitas.",
    "visual": "Você é o Visual Agent. Foque em direção de arte, imagem e estética premium.",
    "video": "Você é o Video Agent. Foque em roteiro, cenas, narrativa, câmera, edição, Reels, Shorts, anúncios e prompts cinematográficos.",
    "assistente": "Você é o Personal Assistant Agent. Foque em rotina, agenda e organização."
}

SENSITIVE_WORDS = [
    "enviar", "publique", "publicar", "postar agora", "apagar", "deletar",
    "excluir", "comprar", "pagar", "contratar", "cancelar", "mandar mensagem",
    "enviar email", "enviar e-mail", "alterar senha", "remover"
]

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def memory():
    mem = load_json(FILES["memory"], {})
    mem.setdefault("perfil", {})
    mem.setdefault("objetivos", [])
    mem.setdefault("preferencias", [])
    return mem

def save_item(tipo, tema, conteudo):
    data = load_json(FILES["items"], [])
    data.append({
        "tipo": tipo,
        "tema": tema,
        "conteudo": conteudo,
        "data": str(datetime.now(TZ))
    })
    save_json(FILES["items"], data)

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
        max_tokens=3500
    )

    return r.choices[0].message.content

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

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

    mem["ultima_interacao"] = str(datetime.now(TZ))
    save_json(FILES["memory"], mem)

def is_sensitive(text):
    return any(word in text.lower() for word in SENSITIVE_WORDS)

def save_approval(acao, origem="manual"):
    approvals = load_json(FILES["approvals"], [])
    approvals.append({
        "acao": acao,
        "origem": origem,
        "status": "pendente",
        "data": str(datetime.now(TZ))
    })
    save_json(FILES["approvals"], approvals)
    return len(approvals)

def image_url(prompt, width=1024, height=1024, seed=77):
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&seed={seed}"

def visual_prompt(tipo, tema):
    if tipo == "logo":
        return f"minimal futuristic luxury logo, clean vector style, premium streetwear identity, white background, professional logo design. Brand: {tema}"
    if tipo == "thumbnail":
        return f"viral YouTube thumbnail, cinematic premium composition, bold contrast, dramatic lighting, high CTR, street luxury futuristic aesthetic. Theme: {tema}"
    if tipo == "poster":
        return f"cinematic movie poster, premium futuristic street luxury, neon accents, urban luxury atmosphere, professional advertising poster. Theme: {tema}"
    if tipo == "banner":
        return f"wide cinematic banner, premium brand campaign, street luxury futuristic aesthetic, space for headline. Theme: {tema}"
    return f"ultra realistic cinematic image, street luxury futuristic aesthetic, cyberpunk executive style, premium lighting, 8k, highly detailed. Theme: {tema}"

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore AI online com MODO VÍDEO. Digite /menu.")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI — CENTRAL

/status
/memoria

TAREFAS:
/tarefa
/tarefas
/check
/concluir

MULTIAGENTES:
/ceo
/brandagent
/contentagent
/salesagent
/devagent
/autoagent
/agent

IMAGEM:
/imagem
/logo
/thumbnail
/poster
/banner
/promptimg

VÍDEO:
/video
/roteiro
/cenas
/shorts
/anuncio
/promptvideo

APROVAÇÕES:
/pendentesaprovacao
/aprovar 1
/rejeitar 1

AGENDAMENTOS:
/ativar
/agendar 09:00 revisar tarefas
/agendamentos
""")

async def status(update, context):
    mem = memory()
    approvals = load_json(FILES["approvals"], [])
    pendentes = [a for a in approvals if a.get("status") == "pendente"]

    await update.message.reply_text(f"""
🚀 STATUS

Perfil: {len(mem.get("perfil", {}))}
Objetivos: {len(mem.get("objetivos", []))}
Preferências: {len(mem.get("preferencias", []))}
Tarefas: {len(load_json(FILES["tasks"], []))}
Itens salvos: {len(load_json(FILES["items"], []))}
Agendamentos: {len(load_json(FILES["schedules"], []))}
Aprovações pendentes: {len(pendentes)}

Sistema: ONLINE
Modo: VÍDEO + IMAGEM + APROVAÇÃO SEGURA
""")

async def memoria(update, context):
    mem = memory()
    text = "🧠 MEMÓRIA:\n\n👤 PERFIL:\n"

    for k, v in mem.get("perfil", {}).items():
        text += f"• {k}: {v}\n"

    text += "\n🎯 OBJETIVOS:\n"
    for i, obj in enumerate(mem.get("objetivos", []), 1):
        text += f"{i}. {obj}\n"

    text += "\n⚙️ PREFERÊNCIAS:\n"
    for i, pref in enumerate(mem.get("preferencias", []), 1):
        text += f"{i}. {pref}\n"

    await send_long(update, text)

async def tarefa(update, context):
    nome = " ".join(context.args)
    if not nome:
        await update.message.reply_text("Use:\n/tarefa criar logo")
        return

    tasks = load_json(FILES["tasks"], [])
    tasks.append({"tarefa": nome, "status": "pendente", "data": str(datetime.now(TZ))})
    save_json(FILES["tasks"], tasks)
    await update.message.reply_text("✅ Tarefa criada.")

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
    text = "⚠️ PENDENTES:\n\n"
    found = False

    for i, t in enumerate(tasks, 1):
        if t["status"] == "pendente":
            found = True
            text += f"{i}. {t['tarefa']}\n"

    if not found:
        text = "🔥 Nenhuma pendência."

    await send_long(update, text)

async def concluir(update, context):
    try:
        n = int(context.args[0])
        tasks = load_json(FILES["tasks"], [])
        tasks[n - 1]["status"] = "concluída"
        save_json(FILES["tasks"], tasks)
        await update.message.reply_text("✅ Concluída.")
    except:
        await update.message.reply_text("Use:\n/concluir 1")

async def generic(update, context, tipo, prompt, agent=None):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text(f"Use:\n/{tipo} tema")
        return

    resposta = ask_ai(prompt + "\n\nTema:\n" + tema, agent)
    save_item(tipo, tema, resposta)
    await send_long(update, resposta)

async def ceo(update, context):
    await generic(update, context, "ceo", "Analise como CEO e entregue estratégia prática.", "ceo")

async def brandagent(update, context):
    await generic(update, context, "branding", "Crie branding premium completo.", "branding")

async def contentagent(update, context):
    await generic(update, context, "conteudo", "Crie estratégia de conteúdo viral.", "conteudo")

async def salesagent(update, context):
    await generic(update, context, "vendas", "Crie estratégia de vendas e funil.", "vendas")

async def devagent(update, context):
    await generic(update, context, "dev", "Crie solução técnica com ferramentas grátis.", "dev")

async def autoagent(update, context):
    await generic(update, context, "automacao", "Crie automação gratuita passo a passo.", "automacao")

async def agent(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/agent objetivo")
        return

    resposta = ask_ai(f"""
Resolva usando múltiplos agentes:

{tema}

1. CEO
2. Branding
3. Conteúdo
4. Vendas
5. Dev
6. Automação
7. Assistente pessoal
8. Plano final
""")

    save_item("multiagent", tema, resposta)
    await send_long(update, resposta)

async def imagem(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/imagem descrição")
        return
    await update.message.reply_text("🎨 Gerando imagem premium grátis...")
    await update.message.reply_photo(photo=image_url(visual_prompt("imagem", tema), 1024, 1024, 77))

async def logo(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/logo nome da marca")
        return
    await update.message.reply_text("🔥 Criando logo grátis...")
    await update.message.reply_photo(photo=image_url(visual_prompt("logo", tema), 1024, 1024, 88))

async def thumbnail(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/thumbnail tema")
        return
    await update.message.reply_text("🧲 Criando thumbnail grátis...")
    await update.message.reply_photo(photo=image_url(visual_prompt("thumbnail", tema), 1280, 720, 99))

async def poster(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/poster tema")
        return
    await update.message.reply_text("🎬 Criando poster grátis...")
    await update.message.reply_photo(photo=image_url(visual_prompt("poster", tema), 1024, 1536, 111))

async def banner(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/banner tema")
        return
    await update.message.reply_text("🖼 Criando banner grátis...")
    await update.message.reply_photo(photo=image_url(visual_prompt("banner", tema), 1536, 768, 222))

async def promptimg(update, context):
    await generic(update, context, "promptimg", """
Crie 5 prompts visuais ultra avançados para gerar imagens IA.
Cada prompt deve ter composição, iluminação, estilo, lente/câmera, atmosfera, detalhes premium e versão em inglês.
""", "visual")

async def video(update, context):
    await generic(update, context, "video", """
Crie um conceito completo de vídeo cinematográfico.

Inclua:
1. Ideia central
2. Objetivo do vídeo
3. Público
4. Duração recomendada
5. Estilo visual
6. Roteiro resumido
7. Cenas principais
8. Narração
9. Texto na tela
10. CTA
11. Ferramentas gratuitas para executar
""", "video")

async def roteiro(update, context):
    await generic(update, context, "roteiro", """
Crie um roteiro completo para vídeo.

Inclua:
1. Hook inicial
2. Cena por cena
3. Narração
4. Texto na tela
5. B-roll
6. Trilha sugerida
7. Ritmo de edição
8. CTA final
""", "video")

async def cenas(update, context):
    await generic(update, context, "cenas", """
Crie uma lista de cenas cinematográficas.

Inclua:
1. Cena
2. Descrição visual
3. Movimento de câmera
4. Iluminação
5. Ação
6. Texto na tela
7. Prompt visual para cada cena
""", "video")

async def shorts(update, context):
    await generic(update, context, "shorts", """
Crie um vídeo curto estilo Shorts/Reels/TikTok.

Inclua:
1. Hook de 3 segundos
2. Roteiro de 30 segundos
3. Cortes rápidos
4. Texto na tela
5. Narração
6. CTA
7. Ideia visual
8. Legenda
""", "video")

async def anuncio(update, context):
    await generic(update, context, "anuncio_video", """
Crie um anúncio em vídeo.

Inclua:
1. Dor
2. Promessa
3. Produto/oferta
4. Prova
5. Objeções
6. Roteiro de 15s
7. Roteiro de 30s
8. CTA
9. Versão para Reels
10. Versão para Stories
""", "video")

async def promptvideo(update, context):
    await generic(update, context, "promptvideo", """
Crie 5 prompts cinematográficos para gerar vídeo IA.

Cada prompt deve incluir:
1. Descrição da cena
2. Movimento de câmera
3. Iluminação
4. Estilo visual
5. Atmosfera
6. Duração
7. Formato 9:16
8. Prompt em inglês pronto para ferramentas de vídeo IA gratuitas ou plano grátis
""", "video")

async def ativar(update, context):
    config = load_json(FILES["config"], {})
    config["chat_id"] = update.effective_chat.id
    save_json(FILES["config"], config)
    await update.message.reply_text("✅ Execução automática ativada neste chat.")

async def agendar(update, context):
    texto = " ".join(context.args)
    if not texto or len(texto.split()) < 2:
        await update.message.reply_text("Use:\n/agendar 09:00 revisar tarefas")
        return

    hora, acao = texto.split(" ", 1)

    try:
        datetime.strptime(hora, "%H:%M")
    except:
        await update.message.reply_text("Horário inválido. Use:\n/agendar 09:00 revisar tarefas")
        return

    schedules = load_json(FILES["schedules"], [])
    schedules.append({"hora": hora, "acao": acao, "ativo": True, "ultimo_disparo": "", "data": str(datetime.now(TZ))})
    save_json(FILES["schedules"], schedules)

    await update.message.reply_text(f"⏰ Agendamento criado:\n{hora} — {acao}")

async def agendamentos(update, context):
    schedules = load_json(FILES["schedules"], [])
    if not schedules:
        await update.message.reply_text("Nenhum agendamento.")
        return

    text = "⏰ AGENDAMENTOS:\n\n"
    for i, s in enumerate(schedules, 1):
        status = "ativo" if s.get("ativo") else "pausado"
        text += f"{i}. {s['hora']} — {s['acao']} — {status}\n"

    await send_long(update, text)

async def pendentesaprovacao(update, context):
    approvals = load_json(FILES["approvals"], [])
    pendentes = [(i, a) for i, a in enumerate(approvals, 1) if a.get("status") == "pendente"]

    if not pendentes:
        await update.message.reply_text("Nenhuma aprovação pendente.")
        return

    text = "🛡 APROVAÇÕES PENDENTES:\n\n"
    for i, a in pendentes:
        text += f"{i}. {a['acao']}\nOrigem: {a['origem']}\nData: {a['data']}\n\n"

    text += "Use:\n/aprovar número\n/rejeitar número"
    await send_long(update, text)

async def aprovar(update, context):
    try:
        n = int(context.args[0])
        approvals = load_json(FILES["approvals"], [])
        approvals[n - 1]["status"] = "aprovado"
        approvals[n - 1]["aprovado_em"] = str(datetime.now(TZ))
        save_json(FILES["approvals"], approvals)

        acao = approvals[n - 1]["acao"]
        resposta = ask_ai(f"Ação aprovada: {acao}. Entregue plano de execução seguro.", "assistente")
        await send_long(update, resposta)
    except:
        await update.message.reply_text("Use:\n/aprovar 1")

async def rejeitar(update, context):
    try:
        n = int(context.args[0])
        approvals = load_json(FILES["approvals"], [])
        approvals[n - 1]["status"] = "rejeitado"
        approvals[n - 1]["rejeitado_em"] = str(datetime.now(TZ))
        save_json(FILES["approvals"], approvals)
        await update.message.reply_text("❌ Ação rejeitada.")
    except:
        await update.message.reply_text("Use:\n/rejeitar 1")

async def scheduled_checker(context):
    config = load_json(FILES["config"], {})
    chat_id = config.get("chat_id")

    if not chat_id:
        return

    now = datetime.now(TZ)
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    schedules = load_json(FILES["schedules"], [])
    changed = False

    for s in schedules:
        if not s.get("ativo", True):
            continue

        if s.get("hora") == current_time and s.get("ultimo_disparo") != today:
            acao = s.get("acao", "")

            if is_sensitive(acao):
                idx = save_approval(acao, "agendamento")
                await context.bot.send_message(chat_id=chat_id, text=f"🛡 Ação sensível detectada.\nAprovação #{idx}: {acao}")
            else:
                resposta = ask_ai(f"Execute este agendamento como assistente operacional: {acao}", "assistente")
                await context.bot.send_message(chat_id=chat_id, text=f"⏰ AGENDAMENTO AUTOMÁTICO\n\n{s['hora']} — {acao}")
                for i in range(0, len(resposta), 3900):
                    await context.bot.send_message(chat_id=chat_id, text=resposta[i:i+3900])

            s["ultimo_disparo"] = today
            changed = True

    if changed:
        save_json(FILES["schedules"], schedules)

async def handle_message(update, context):
    msg = update.message.text
    auto_memory(msg)

    if is_sensitive(msg):
        idx = save_approval(msg, "mensagem")
        await update.message.reply_text(f"🛡 Ação sensível. Aprovação criada #{idx}.\nUse /aprovar {idx} ou /rejeitar {idx}")
        return

    resposta = ask_ai(msg)
    await send_long(update, resposta)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

commands = {
    "start": start, "menu": menu, "status": status, "memoria": memoria,
    "tarefa": tarefa, "tarefas": tarefas, "check": check, "concluir": concluir,
    "ceo": ceo, "brandagent": brandagent, "contentagent": contentagent,
    "salesagent": salesagent, "devagent": devagent, "autoagent": autoagent,
    "agent": agent,
    "imagem": imagem, "logo": logo, "thumbnail": thumbnail,
    "poster": poster, "banner": banner, "promptimg": promptimg,
    "video": video, "roteiro": roteiro, "cenas": cenas,
    "shorts": shorts, "anuncio": anuncio, "promptvideo": promptvideo,
    "ativar": ativar, "agendar": agendar, "agendamentos": agendamentos,
    "pendentesaprovacao": pendentesaprovacao, "aprovar": aprovar, "rejeitar": rejeitar
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.job_queue.run_repeating(scheduled_checker, interval=60, first=10)

print("🔥 STREETCORE AI VIDEO MODE ONLINE")
app.run_polling()
