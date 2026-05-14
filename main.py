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

# ====================================
# CONFIG
# ====================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MEMORY_FILE = "memory.json"
PROJECTS_FILE = "projects.json"
TASKS_FILE = "tasks.json"

# ====================================
# MASTER PROMPT
# ====================================

MASTER_PROMPT = """
Você é StreetCore AI.

Um agente executivo, estratégico,
criativo e operacional.

Você ajuda o usuário:
- criar negócios;
- criar marcas;
- organizar projetos;
- automatizar tarefas;
- crescer;
- monetizar;
- executar ideias.

Você sempre:
- responde em português;
- explica passo a passo;
- age como parceiro operacional;
- pensa em escala;
- pensa em branding;
- pensa em produtividade.
"""

# ====================================
# MEMORY
# ====================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return {}

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_memory(memory):

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=2
        )

# ====================================
# PROJECTS
# ====================================

def load_projects():

    if not os.path.exists(PROJECTS_FILE):
        return []

    with open(PROJECTS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_projects(projects):

    with open(PROJECTS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            projects,
            file,
            ensure_ascii=False,
            indent=2
        )

# ====================================
# TASKS
# ====================================

def load_tasks():

    if not os.path.exists(TASKS_FILE):
        return []

    with open(TASKS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_tasks(tasks):

    with open(TASKS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            tasks,
            file,
            ensure_ascii=False,
            indent=2
        )

# ====================================
# IMAGE SYSTEM
# ====================================

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

    encoded = urllib.parse.quote(
        premium_prompt
    )

    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&seed=77"

# ====================================
# AUTO MEMORY
# ====================================

def auto_memory(user_message, memory):

    text = user_message.lower()

    try:

        if "meu nome é" in text:
            memory["nome"] = text.split(
                "meu nome é"
            )[1].strip()

        if "quero criar" in text:
            memory["objetivo"] = text.split(
                "quero criar"
            )[1].strip()

        if "minha marca é" in text:
            memory["marca"] = text.split(
                "minha marca é"
            )[1].strip()

    except:
        pass

    memory["ultima_interacao"] = str(
        datetime.now()
    )

    save_memory(memory)

# ====================================
# COMMANDS
# ====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🔥 STREETCORE AI ONLINE

CAPACIDADES:

✅ IA
✅ Branding
✅ Estratégia
✅ Projetos
✅ Tarefas
✅ Imagens
✅ Memória

COMANDOS:

/status
/memoria
/projeto
/projetos
/tarefa
/tarefas
/imagem
/logo
"""

    await update.message.reply_text(text)

# ====================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🚀 STATUS

Sistema: ONLINE
IA: Groq
Memória: Ativa
Projetos: Ativos
Modo: CEO EXECUTIVO
"""

    await update.message.reply_text(text)

# ====================================

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):

    memory = load_memory()

    if not memory:
        await update.message.reply_text(
            "Nenhuma memória salva."
        )
        return

    text = "🧠 MEMÓRIAS:\n\n"

    for key, value in memory.items():
        text += f"• {key}: {value}\n"

    await update.message.reply_text(text)

# ====================================
# PROJECT COMMANDS
# ====================================

async def projeto(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nome = " ".join(context.args)

    if not nome:
        await update.message.reply_text(
            "Use:\n/projeto nome do projeto"
        )
        return

    projects = load_projects()

    novo = {
        "nome": nome,
        "data": str(datetime.now())
    }

    projects.append(novo)

    save_projects(projects)

    await update.message.reply_text(
        f"✅ Projeto criado:\n{nome}"
    )

# ====================================

async def projetos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    projects = load_projects()

    if not projects:
        await update.message.reply_text(
            "Nenhum projeto criado."
        )
        return

    text = "📁 PROJETOS:\n\n"

    for p in projects:
        text += f"• {p['nome']}\n"

    await update.message.reply_text(text)

# ====================================
# TASK COMMANDS
# ====================================

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nome = " ".join(context.args)

    if not nome:
        await update.message.reply_text(
            "Use:\n/tarefa descrição"
        )
        return

    tasks = load_tasks()

    nova = {
        "tarefa": nome,
        "status": "pendente",
        "data": str(datetime.now())
    }

    tasks.append(nova)

    save_tasks(tasks)

    await update.message.reply_text(
        f"✅ Tarefa criada:\n{nome}"
    )

# ====================================

async def tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tasks = load_tasks()

    if not tasks:
        await update.message.reply_text(
            "Nenhuma tarefa criada."
        )
        return

    text = "📝 TAREFAS:\n\n"

    for t in tasks:
        text += f"• {t['tarefa']} ({t['status']})\n"

    await update.message.reply_text(text)

# ====================================
# IMAGE
# ====================================

async def imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text(
            "Use:\n/imagem descrição"
        )
        return

    await update.message.reply_text(
        "🎨 Gerando imagem..."
    )

    image_url = gerar_imagem_url(prompt)

    await update.message.reply_photo(
        photo=image_url
    )

# ====================================

async def logo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text(
            "Use:\n/logo nome da marca"
        )
        return

    logo_prompt = f"""
minimal futuristic luxury logo,
clean branding,
premium streetwear identity.

{prompt}
"""

    await update.message.reply_text(
        "🔥 Criando logo..."
    )

    image_url = gerar_imagem_url(
        logo_prompt
    )

    await update.message.reply_photo(
        photo=image_url
    )

# ====================================
# CHAT
# ====================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    memory = load_memory()

    auto_memory(user_message, memory)

    memory_text = json.dumps(
        memory,
        ensure_ascii=False,
        indent=2
    )

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content":
                MASTER_PROMPT +
                f"\n\nMEMÓRIA:\n{memory_text}"
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.8,
        max_tokens=2000
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

# ====================================
# APP
# ====================================

app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("memoria", memoria))

app.add_handler(CommandHandler("projeto", projeto))
app.add_handler(CommandHandler("projetos", projetos))

app.add_handler(CommandHandler("tarefa", tarefa))
app.add_handler(CommandHandler("tarefas", tarefas))

app.add_handler(CommandHandler("imagem", imagem))
app.add_handler(CommandHandler("logo", logo))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("🔥 STREETCORE AI OPERACIONAL ONLINE")

app.run_polling()
