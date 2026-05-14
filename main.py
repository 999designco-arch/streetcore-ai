import os
import json
import urllib.parse
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MEMORY_FILE = "memory.json"
PROJECTS_FILE = "projects.json"
TASKS_FILE = "tasks.json"
ROADMAPS_FILE = "roadmaps.json"

MASTER_PROMPT = """
Você é StreetCore AI.

Um agente executivo, estratégico, criativo e operacional.

Você atua como:
- CEO;
- COO;
- estrategista;
- diretor criativo;
- especialista em branding;
- especialista em IA;
- engenheiro de automação;
- growth hacker;
- operador pessoal.

Regras:
- responda sempre em português;
- use apenas ferramentas gratuitas ou plano grátis como padrão;
- explique passo a passo;
- entregue soluções práticas;
- pense em escala, dinheiro, marca e automação;
- aja como se estivesse pegando na mão do usuário.
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

def ask_ai(prompt, memory=None):
    memory_text = json.dumps(memory or {}, ensure_ascii=False, indent=2)

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": MASTER_PROMPT + f"\n\nMEMÓRIA:\n{memory_text}"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.8,
        max_tokens=3000
    )

    return completion.choices[0].message.content

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 STREETCORE AI ONLINE

AGENTE OPERACIONAL PREMIUM

COMANDOS:

/status
/memoria
/projeto
/projetos
/tarefa
/tarefas
/roadmap
/roadmaps
/imagem
/logo
""")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    projects = load_json(PROJECTS_FILE, [])
    tasks = load_json(TASKS_FILE, [])
    roadmaps = load_json(ROADMAPS_FILE, [])

    await update.message.reply_text(f"""
🚀 STATUS

Sistema: ONLINE
IA: Groq grátis
Imagem: Pollinations grátis
Memória: {len(memory)} itens
Projetos: {len(projects)}
Tarefas: {len(tasks)}
Roadmaps: {len(roadmaps)}
Modo: CEO + COO OPERACIONAL
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
        await update.message.reply_text("Use:\n/projeto nome do projeto")
        return

    projects = load_json(PROJECTS_FILE, [])
    projects.append({
        "nome": nome,
        "data": str(datetime.now())
    })

    save_json(PROJECTS_FILE, projects)
    await update.message.reply_text(f"✅ Projeto criado:\n{nome}")

async def projetos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    projects = load_json(PROJECTS_FILE, [])

    if not projects:
        await update.message.reply_text("Nenhum projeto criado.")
        return

    text = "📁 PROJETOS:\n\n"
    for p in projects:
        text += f"• {p['nome']}\n"

    await update.message.reply_text(text)

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)

    if not nome:
        await update.message.reply_text("Use:\n/tarefa descrição da tarefa")
        return

    tasks = load_json(TASKS_FILE, [])
    tasks.append({
        "tarefa": nome,
        "status": "pendente",
        "data": str(datetime.now())
    })

    save_json(TASKS_FILE, tasks)
    await update.message.reply_text(f"✅ Tarefa criada:\n{nome}")

async def tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_json(TASKS_FILE, [])

    if not tasks:
        await update.message.reply_text("Nenhuma tarefa criada.")
        return

    text = "📝 TAREFAS:\n\n"
    for t in tasks:
        text += f"• {t['tarefa']} ({t['status']})\n"

    await update.message.reply_text(text)

async def roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    objetivo = " ".join(context.args)

    if not objetivo:
        await update.message.reply_text("Use:\n/roadmap seu objetivo")
        return

    await update.message.reply_text("🧠 Criando roadmap estratégico completo...")

    memory = load_memory()

    prompt = f"""
Crie um ROADMAP EXECUTIVO completo para este objetivo:

{objetivo}

Estruture assim:

1. Visão geral do objetivo
2. Estratégia principal
3. Etapas essenciais
4. Plano de execução em 7 dias
5. Plano de execução em 30 dias
6. Tarefas prioritárias
7. Ferramentas gratuitas recomendadas
8. Estratégia de monetização
9. Riscos e gargalos
10. Próximo passo imediato

Use linguagem clara, premium e prática.
"""

    resposta = ask_ai(prompt, memory)

    roadmaps = load_json(ROADMAPS_FILE, [])
    roadmaps.append({
        "objetivo": objetivo,
        "roadmap": resposta,
        "data": str(datetime.now())
    })

    save_json(ROADMAPS_FILE, roadmaps)

    await update.message.reply_text(resposta)

async def roadmaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    roadmaps_list = load_json(ROADMAPS_FILE, [])

    if not roadmaps_list:
        await update.message.reply_text("Nenhum roadmap criado.")
        return

    text = "🗺 ROADMAPS SALVOS:\n\n"

    for i, r in enumerate(roadmaps_list, start=1):
        text += f"{i}. {r['objetivo']}\n"

    await update.message.reply_text(text)

async def imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text("Use:\n/imagem descrição")
        return

    await update.message.reply_text("🎨 Gerando imagem gratuita...")
    image_url = gerar_imagem_url(prompt)
    await update.message.reply_photo(photo=image_url)

async def logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text("Use:\n/logo nome da marca")
        return

    await update.message.reply_text("🔥 Criando logo gratuita...")

    logo_prompt = f"""
minimal futuristic luxury logo,
clean branding,
premium streetwear identity,
white background,
professional logo design.

{prompt}
"""

    image_url = gerar_imagem_url(logo_prompt)
    await update.message.reply_photo(photo=image_url)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    memory = load_memory()
    auto_memory(user_message, memory)

    reply = ask_ai(user_message, memory)

    await update.message.reply_text(reply)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("memoria", memoria))

app.add_handler(CommandHandler("projeto", projeto))
app.add_handler(CommandHandler("projetos", projetos))

app.add_handler(CommandHandler("tarefa", tarefa))
app.add_handler(CommandHandler("tarefas", tarefas))

app.add_handler(CommandHandler("roadmap", roadmap))
app.add_handler(CommandHandler("roadmaps", roadmaps))

app.add_handler(CommandHandler("imagem", imagem))
app.add_handler(CommandHandler("logo", logo))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI ROADMAP ENGINE ONLINE")
app.run_polling()
