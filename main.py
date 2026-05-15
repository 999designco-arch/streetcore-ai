import os
import json
import urllib.parse
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MEMORY_FILE = "memory.json"
PROJECTS_FILE = "projects.json"
TASKS_FILE = "tasks.json"
ROADMAPS_FILE = "roadmaps.json"
AUTOMATIONS_FILE = "automations.json"
CONTENT_FILE = "content.json"

MASTER_PROMPT = """
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, COO, diretor criativo, growth hacker, social media, roteirista e engenheiro de automação.
Explique passo a passo, com execução prática e estética premium.
"""

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_memory():
    return load_json(MEMORY_FILE, {})

def save_memory(memory):
    save_json(MEMORY_FILE, memory)

def auto_memory(user_message, memory):
    text = user_message.lower()
    try:
        if "meu nome é" in text:
            memory["nome"] = text.split("meu nome é")[1].strip()
        if "quero criar" in text:
            memory["objetivo"] = text.split("quero criar")[1].strip()
        if "minha marca é" in text:
            memory["marca"] = text.split("minha marca é")[1].strip()
        if "meu nicho é" in text:
            memory["nicho"] = text.split("meu nicho é")[1].strip()
    except:
        pass

    memory["ultima_interacao"] = str(datetime.now())
    save_memory(memory)

def ask_ai(prompt, memory=None):
    memory_text = json.dumps(memory or {}, ensure_ascii=False, indent=2)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT + f"\n\nMEMÓRIA:\n{memory_text}"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=3500
    )
    return completion.choices[0].message.content

def gerar_imagem_url(prompt):
    premium_prompt = f"""
ultra realistic cinematic image,
street luxury futuristic aesthetic,
cyberpunk executive style,
premium lighting,
8k,
highly detailed.

{prompt}
"""
    encoded = urllib.parse.quote(premium_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&seed=77"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 STREETCORE AI ONLINE

COMANDOS:

/status
/memoria

/projeto
/projetos

/tarefa
/tarefas
/check
/concluir

/roadmap
/roadmaps

/hoje
/semana

/imagem
/logo

/automacao
/fluxo
/script
/checklist
/automacoes

/conteudo
/carrossel
/reels
/calendario
/campanha
/conteudos
""")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    projects = load_json(PROJECTS_FILE, [])
    tasks = load_json(TASKS_FILE, [])
    roadmaps = load_json(ROADMAPS_FILE, [])
    automations = load_json(AUTOMATIONS_FILE, [])
    contents = load_json(CONTENT_FILE, [])

    await update.message.reply_text(f"""
🚀 STATUS

Sistema: ONLINE
IA: Groq grátis
Imagem: Pollinations grátis
Memória: {len(memory)}
Projetos: {len(projects)}
Tarefas: {len(tasks)}
Roadmaps: {len(roadmaps)}
Automações: {len(automations)}
Conteúdos: {len(contents)}

Modo: AGÊNCIA + CEO + AUTOMAÇÃO
""")

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    if not memory:
        await update.message.reply_text("Nenhuma memória salva.")
        return

    text = "🧠 MEMÓRIAS:\n\n"
    for key, value in memory.items():
        text += f"• {key}: {value}\n"
    await update.message.reply_text(text)

async def projeto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    if not nome:
        await update.message.reply_text("Use:\n/projeto nome")
        return

    projects = load_json(PROJECTS_FILE, [])
    projects.append({"nome": nome, "data": str(datetime.now())})
    save_json(PROJECTS_FILE, projects)
    await update.message.reply_text(f"✅ Projeto criado:\n{nome}")

async def projetos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    projects = load_json(PROJECTS_FILE, [])
    if not projects:
        await update.message.reply_text("Nenhum projeto.")
        return

    text = "📁 PROJETOS:\n\n"
    for i, p in enumerate(projects, start=1):
        text += f"{i}. {p['nome']}\n"
    await update.message.reply_text(text)

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    if not nome:
        await update.message.reply_text("Use:\n/tarefa descrição")
        return

    tasks = load_json(TASKS_FILE, [])
    tasks.append({"tarefa": nome, "status": "pendente", "data": str(datetime.now())})
    save_json(TASKS_FILE, tasks)
    await update.message.reply_text(f"✅ Tarefa criada:\n{nome}")

async def tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_json(TASKS_FILE, [])
    if not tasks:
        await update.message.reply_text("Nenhuma tarefa.")
        return

    text = "📝 TAREFAS:\n\n"
    for i, t in enumerate(tasks, start=1):
        text += f"{i}. {t['tarefa']} — {t['status']}\n"
    await update.message.reply_text(text)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_json(TASKS_FILE, [])
    pendentes = [(i, t) for i, t in enumerate(tasks, start=1) if t.get("status") == "pendente"]

    if not pendentes:
        await update.message.reply_text("🔥 Nenhuma pendência.")
        return

    text = "⚠️ PENDENTES:\n\n"
    for i, t in pendentes:
        text += f"{i}. {t['tarefa']}\n"
    text += "\n/concluir número"
    await update.message.reply_text(text)

async def concluir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use:\n/concluir número")
        return

    try:
        numero = int(context.args[0])
    except:
        await update.message.reply_text("Número inválido.")
        return

    tasks = load_json(TASKS_FILE, [])
    if numero < 1 or numero > len(tasks):
        await update.message.reply_text("Tarefa inexistente.")
        return

    tasks[numero - 1]["status"] = "concluída"
    save_json(TASKS_FILE, tasks)
    await update.message.reply_text("✅ Tarefa concluída.")

async def roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    objetivo = " ".join(context.args)
    if not objetivo:
        await update.message.reply_text("Use:\n/roadmap objetivo")
        return

    await update.message.reply_text("🧠 Criando roadmap...")
    resposta = ask_ai(f"""
Crie um roadmap executivo completo para:

{objetivo}

Inclua:
- estratégia;
- execução;
- monetização;
- ferramentas grátis;
- plano de 7 dias;
- plano de 30 dias.
""", load_memory())

    roadmaps = load_json(ROADMAPS_FILE, [])
    roadmaps.append({"objetivo": objetivo, "conteudo": resposta, "data": str(datetime.now())})
    save_json(ROADMAPS_FILE, roadmaps)
    await update.message.reply_text(resposta)

async def roadmaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roadmaps_list = load_json(ROADMAPS_FILE, [])
    if not roadmaps_list:
        await update.message.reply_text("Nenhum roadmap.")
        return

    text = "🗺 ROADMAPS:\n\n"
    for i, r in enumerate(roadmaps_list, start=1):
        text += f"{i}. {r['objetivo']}\n"
    await update.message.reply_text(text)

async def hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_json(TASKS_FILE, [])
    resposta = ask_ai(f"Crie um plano executivo para hoje com base nestas tarefas:\n{tasks}", load_memory())
    await update.message.reply_text(resposta)

async def semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_json(TASKS_FILE, [])
    resposta = ask_ai(f"Crie um plano semanal executivo com base nestas tarefas:\n{tasks}", load_memory())
    await update.message.reply_text(resposta)

async def imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Use:\n/imagem descrição")
        return

    await update.message.reply_text("🎨 Gerando imagem...")
    await update.message.reply_photo(photo=gerar_imagem_url(prompt))

async def logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Use:\n/logo marca")
        return

    await update.message.reply_text("🔥 Criando logo...")
    await update.message.reply_photo(photo=gerar_imagem_url(f"minimal futuristic luxury logo, premium streetwear branding, {prompt}"))

async def automacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    objetivo = " ".join(context.args)
    if not objetivo:
        await update.message.reply_text("Use:\n/automacao objetivo")
        return

    resposta = ask_ai(f"""
Crie uma automação gratuita para:

{objetivo}

Inclua ferramentas grátis, passo a passo, fluxo, execução e erros comuns.
""", load_memory())

    automations = load_json(AUTOMATIONS_FILE, [])
    automations.append({"objetivo": objetivo, "conteudo": resposta, "data": str(datetime.now())})
    save_json(AUTOMATIONS_FILE, automations)
    await update.message.reply_text(resposta)

async def fluxo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    objetivo = " ".join(context.args)
    resposta = ask_ai(f"Crie um fluxo operacional gratuito para:\n{objetivo}\nFormato: INÍCIO → ETAPA → FINAL", load_memory())
    await update.message.reply_text(resposta)

async def script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    objetivo = " ".join(context.args)
    resposta = ask_ai(f"Crie um script Python gratuito para:\n{objetivo}\nInclua código completo e como rodar.", load_memory())
    await update.message.reply_text(resposta)

async def checklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    objetivo = " ".join(context.args)
    resposta = ask_ai(f"Crie um checklist operacional completo para:\n{objetivo}", load_memory())
    await update.message.reply_text(resposta)

async def automacoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    automations = load_json(AUTOMATIONS_FILE, [])
    if not automations:
        await update.message.reply_text("Nenhuma automação.")
        return

    text = "⚙️ AUTOMAÇÕES:\n\n"
    for i, a in enumerate(automations, start=1):
        text += f"{i}. {a['objetivo']}\n"
    await update.message.reply_text(text)

async def conteudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/conteudo tema")
        return

    resposta = ask_ai(f"""
Crie um conteúdo viral premium para Instagram/TikTok sobre:

{tema}

Inclua:
1. Gancho forte
2. Texto principal
3. Legenda
4. CTA
5. Hashtags
6. Ideia visual
7. Sugestão de imagem com IA gratuita
""", load_memory())

    contents = load_json(CONTENT_FILE, [])
    contents.append({"tipo": "conteudo", "tema": tema, "conteudo": resposta, "data": str(datetime.now())})
    save_json(CONTENT_FILE, contents)
    await update.message.reply_text(resposta)

async def carrossel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/carrossel tema")
        return

    resposta = ask_ai(f"""
Crie um carrossel viral para Instagram sobre:

{tema}

Estruture:
Slide 1: capa com gancho
Slides 2-6: conteúdo
Slide 7: conclusão
Slide 8: CTA
Inclua legenda e direção visual premium.
""", load_memory())

    contents = load_json(CONTENT_FILE, [])
    contents.append({"tipo": "carrossel", "tema": tema, "conteudo": resposta, "data": str(datetime.now())})
    save_json(CONTENT_FILE, contents)
    await update.message.reply_text(resposta)

async def reels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/reels tema")
        return

    resposta = ask_ai(f"""
Crie um roteiro de Reels/TikTok viral sobre:

{tema}

Inclua:
1. Hook de 3 segundos
2. Cena por cena
3. Texto na tela
4. Narração
5. B-roll
6. CTA
7. Prompt de vídeo IA gratuito/alternativo
""", load_memory())

    contents = load_json(CONTENT_FILE, [])
    contents.append({"tipo": "reels", "tema": tema, "conteudo": resposta, "data": str(datetime.now())})
    save_json(CONTENT_FILE, contents)
    await update.message.reply_text(resposta)

async def calendario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/calendario tema ou nicho")
        return

    resposta = ask_ai(f"""
Crie um calendário de conteúdo de 30 dias para:

{tema}

Formato:
Dia 1 até Dia 30.
Para cada dia:
- tema;
- formato;
- gancho;
- CTA;
- ideia visual;
- ferramenta grátis sugerida.
""", load_memory())

    contents = load_json(CONTENT_FILE, [])
    contents.append({"tipo": "calendario", "tema": tema, "conteudo": resposta, "data": str(datetime.now())})
    save_json(CONTENT_FILE, contents)
    await update.message.reply_text(resposta)

async def campanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/campanha produto ou marca")
        return

    resposta = ask_ai(f"""
Crie uma campanha premium completa para:

{tema}

Inclua:
1. Conceito central
2. Público-alvo
3. Oferta
4. Mensagem principal
5. 5 posts
6. 3 Reels
7. 1 carrossel
8. Ideias visuais
9. Funil grátis
10. Plano de execução de 7 dias
""", load_memory())

    contents = load_json(CONTENT_FILE, [])
    contents.append({"tipo": "campanha", "tema": tema, "conteudo": resposta, "data": str(datetime.now())})
    save_json(CONTENT_FILE, contents)
    await update.message.reply_text(resposta)

async def conteudos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contents = load_json(CONTENT_FILE, [])
    if not contents:
        await update.message.reply_text("Nenhum conteúdo salvo.")
        return

    text = "📲 CONTEÚDOS SALVOS:\n\n"
    for i, c in enumerate(contents, start=1):
        text += f"{i}. {c['tipo']} — {c['tema']}\n"
    await update.message.reply_text(text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    memory = load_memory()
    auto_memory(user_message, memory)

    resposta = ask_ai(user_message, memory)
    await update.message.reply_text(resposta)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("memoria", memoria))

app.add_handler(CommandHandler("projeto", projeto))
app.add_handler(CommandHandler("projetos", projetos))

app.add_handler(CommandHandler("tarefa", tarefa))
app.add_handler(CommandHandler("tarefas", tarefas))
app.add_handler(CommandHandler("check", check))
app.add_handler(CommandHandler("concluir", concluir))

app.add_handler(CommandHandler("roadmap", roadmap))
app.add_handler(CommandHandler("roadmaps", roadmaps))

app.add_handler(CommandHandler("hoje", hoje))
app.add_handler(CommandHandler("semana", semana))

app.add_handler(CommandHandler("imagem", imagem))
app.add_handler(CommandHandler("logo", logo))

app.add_handler(CommandHandler("automacao", automacao))
app.add_handler(CommandHandler("fluxo", fluxo))
app.add_handler(CommandHandler("script", script))
app.add_handler(CommandHandler("checklist", checklist))
app.add_handler(CommandHandler("automacoes", automacoes))

app.add_handler(CommandHandler("conteudo", conteudo))
app.add_handler(CommandHandler("carrossel", carrossel))
app.add_handler(CommandHandler("reels", reels))
app.add_handler(CommandHandler("calendario", calendario))
app.add_handler(CommandHandler("campanha", campanha))
app.add_handler(CommandHandler("conteudos", conteudos))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI CONTENT MODE ONLINE")
app.run_polling()
