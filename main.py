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

# ====================================
# FILES
# ====================================

MEMORY_FILE = "memory.json"
PROJECTS_FILE = "projects.json"
TASKS_FILE = "tasks.json"
ROADMAPS_FILE = "roadmaps.json"
DAILY_FILE = "daily.json"
AUTOMATIONS_FILE = "automations.json"

# ====================================
# MASTER PROMPT
# ====================================

MASTER_PROMPT = """
Você é StreetCore AI.

Um agente executivo, estratégico,
criativo, técnico e operacional.

Você atua como:
- CEO;
- COO;
- estrategista;
- engenheiro de automação;
- branding expert;
- growth hacker;
- operador pessoal.

REGRAS:
- responda sempre em português;
- use apenas ferramentas gratuitas;
- explique passo a passo;
- aja como parceiro operacional;
- pense em automação, branding e escala.
"""

# ====================================
# JSON SYSTEM
# ====================================

def load_json(file, default):

    if not os.path.exists(file):
        return default

    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):

    with open(file, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

# ====================================
# MEMORY
# ====================================

def load_memory():
    return load_json(MEMORY_FILE, {})

def save_memory(memory):
    save_json(MEMORY_FILE, memory)

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

        if "meu nicho é" in text:
            memory["nicho"] = text.split(
                "meu nicho é"
            )[1].strip()

    except:
        pass

    memory["ultima_interacao"] = str(
        datetime.now()
    )

    save_memory(memory)

# ====================================
# AI SYSTEM
# ====================================

def ask_ai(prompt, memory=None):

    memory_text = json.dumps(
        memory or {},
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
                "content": prompt
            }
        ],
        temperature=0.8,
        max_tokens=3000
    )

    return completion.choices[0].message.content

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
# START
# ====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
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
"""

    await update.message.reply_text(text)

# ====================================
# STATUS
# ====================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    memory = load_memory()

    projects = load_json(
        PROJECTS_FILE,
        []
    )

    tasks = load_json(
        TASKS_FILE,
        []
    )

    roadmaps = load_json(
        ROADMAPS_FILE,
        []
    )

    automations = load_json(
        AUTOMATIONS_FILE,
        []
    )

    await update.message.reply_text(f"""
🚀 STATUS

Sistema: ONLINE
Memória: {len(memory)}
Projetos: {len(projects)}
Tarefas: {len(tasks)}
Roadmaps: {len(roadmaps)}
Automações: {len(automations)}

Modo:
CEO + COO + AUTOMAÇÃO
""")

# ====================================
# MEMORY
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
# PROJECTS
# ====================================

async def projeto(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nome = " ".join(context.args)

    if not nome:
        await update.message.reply_text(
            "Use:\n/projeto nome"
        )
        return

    projects = load_json(
        PROJECTS_FILE,
        []
    )

    projects.append({
        "nome": nome,
        "data": str(datetime.now())
    })

    save_json(
        PROJECTS_FILE,
        projects
    )

    await update.message.reply_text(
        f"✅ Projeto criado:\n{nome}"
    )

async def projetos(update: Update, context: ContextTypes.DEFAULT_TYPE):

    projects = load_json(
        PROJECTS_FILE,
        []
    )

    if not projects:
        await update.message.reply_text(
            "Nenhum projeto."
        )
        return

    text = "📁 PROJETOS:\n\n"

    for i, p in enumerate(projects, start=1):
        text += f"{i}. {p['nome']}\n"

    await update.message.reply_text(text)

# ====================================
# TASKS
# ====================================

async def tarefa(update: Update, context: ContextTypes.DEFAULT_TYPE):

    nome = " ".join(context.args)

    if not nome:
        await update.message.reply_text(
            "Use:\n/tarefa descrição"
        )
        return

    tasks = load_json(
        TASKS_FILE,
        []
    )

    tasks.append({
        "tarefa": nome,
        "status": "pendente",
        "data": str(datetime.now())
    })

    save_json(
        TASKS_FILE,
        tasks
    )

    await update.message.reply_text(
        f"✅ Tarefa criada:\n{nome}"
    )

async def tarefas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tasks = load_json(
        TASKS_FILE,
        []
    )

    if not tasks:
        await update.message.reply_text(
            "Nenhuma tarefa."
        )
        return

    text = "📝 TAREFAS:\n\n"

    for i, t in enumerate(tasks, start=1):
        text += f"{i}. {t['tarefa']} — {t['status']}\n"

    await update.message.reply_text(text)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tasks = load_json(
        TASKS_FILE,
        []
    )

    pendentes = [
        (i, t)
        for i, t in enumerate(tasks, start=1)
        if t["status"] == "pendente"
    ]

    if not pendentes:
        await update.message.reply_text(
            "🔥 Nenhuma pendência."
        )
        return

    text = "⚠️ PENDENTES:\n\n"

    for i, t in pendentes:
        text += f"{i}. {t['tarefa']}\n"

    text += "\n/concluir número"

    await update.message.reply_text(text)

async def concluir(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "Use:\n/concluir número"
        )
        return

    try:
        numero = int(context.args[0])

    except:
        await update.message.reply_text(
            "Número inválido."
        )
        return

    tasks = load_json(
        TASKS_FILE,
        []
    )

    if numero < 1 or numero > len(tasks):
        await update.message.reply_text(
            "Tarefa inexistente."
        )
        return

    tasks[numero - 1]["status"] = "concluída"

    save_json(
        TASKS_FILE,
        tasks
    )

    await update.message.reply_text(
        "✅ Tarefa concluída."
    )

# ====================================
# ROADMAP
# ====================================

async def roadmap(update: Update, context: ContextTypes.DEFAULT_TYPE):

    objetivo = " ".join(context.args)

    if not objetivo:
        await update.message.reply_text(
            "Use:\n/roadmap objetivo"
        )
        return

    await update.message.reply_text(
        "🧠 Criando roadmap..."
    )

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
""")

    roadmaps = load_json(
        ROADMAPS_FILE,
        []
    )

    roadmaps.append({
        "objetivo": objetivo,
        "conteudo": resposta
    })

    save_json(
        ROADMAPS_FILE,
        roadmaps
    )

    await update.message.reply_text(resposta)

async def roadmaps(update: Update, context: ContextTypes.DEFAULT_TYPE):

    roadmaps_list = load_json(
        ROADMAPS_FILE,
        []
    )

    if not roadmaps_list:
        await update.message.reply_text(
            "Nenhum roadmap."
        )
        return

    text = "🗺 ROADMAPS:\n\n"

    for i, r in enumerate(
        roadmaps_list,
        start=1
    ):
        text += f"{i}. {r['objetivo']}\n"

    await update.message.reply_text(text)

# ====================================
# DAILY
# ====================================

async def hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tasks = load_json(
        TASKS_FILE,
        []
    )

    resposta = ask_ai(f"""
Crie um plano executivo para hoje.

Tarefas:
{tasks}
""")

    await update.message.reply_text(resposta)

async def semana(update: Update, context: ContextTypes.DEFAULT_TYPE):

    tasks = load_json(
        TASKS_FILE,
        []
    )

    resposta = ask_ai(f"""
Crie um plano semanal executivo.

Tarefas:
{tasks}
""")

    await update.message.reply_text(resposta)

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

    await update.message.reply_photo(
        photo=gerar_imagem_url(prompt)
    )

async def logo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text(
            "Use:\n/logo marca"
        )
        return

    logo_prompt = f"""
minimal futuristic logo,
luxury branding,
streetwear premium.

{prompt}
"""

    await update.message.reply_text(
        "🔥 Criando logo..."
    )

    await update.message.reply_photo(
        photo=gerar_imagem_url(
            logo_prompt
        )
    )

# ====================================
# AUTOMATION
# ====================================

async def automacao(update: Update, context: ContextTypes.DEFAULT_TYPE):

    objetivo = " ".join(context.args)

    if not objetivo:
        await update.message.reply_text(
            "Use:\n/automacao objetivo"
        )
        return

    resposta = ask_ai(f"""
Crie uma automação gratuita para:

{objetivo}

Inclua:
- ferramentas grátis;
- passo a passo;
- fluxo;
- execução;
- erros comuns.
""")

    automations = load_json(
        AUTOMATIONS_FILE,
        []
    )

    automations.append({
        "objetivo": objetivo,
        "conteudo": resposta
    })

    save_json(
        AUTOMATIONS_FILE,
        automations
    )

    await update.message.reply_text(resposta)

async def fluxo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    objetivo = " ".join(context.args)

    resposta = ask_ai(f"""
Crie um fluxo operacional gratuito para:

{objetivo}

Formato:
INÍCIO →
ETAPA →
ETAPA →
FINAL
""")

    await update.message.reply_text(resposta)

async def script(update: Update, context: ContextTypes.DEFAULT_TYPE):

    objetivo = " ".join(context.args)

    resposta = ask_ai(f"""
Crie um script Python gratuito para:

{objetivo}

Inclua:
- código completo;
- como rodar;
- explicação simples.
""")

    await update.message.reply_text(resposta)

async def checklist(update: Update, context: ContextTypes.DEFAULT_TYPE):

    objetivo = " ".join(context.args)

    resposta = ask_ai(f"""
Crie um checklist operacional para:

{objetivo}
""")

    await update.message.reply_text(resposta)

async def automacoes(update: Update, context: ContextTypes.DEFAULT_TYPE):

    automations = load_json(
        AUTOMATIONS_FILE,
        []
    )

    if not automations:
        await update.message.reply_text(
            "Nenhuma automação."
        )
        return

    text = "⚙️ AUTOMAÇÕES:\n\n"

    for i, a in enumerate(
        automations,
        start=1
    ):
        text += f"{i}. {a['objetivo']}\n"

    await update.message.reply_text(text)

# ====================================
# CHAT
# ====================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    memory = load_memory()

    auto_memory(
        user_message,
        memory
    )

    resposta = ask_ai(
        user_message,
        memory
    )

    await update.message.reply_text(resposta)

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

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("🔥 STREETCORE AI ONLINE")

app.run_polling()
