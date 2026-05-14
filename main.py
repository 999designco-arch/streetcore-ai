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
DAILY_FILE = "daily.json"

MASTER_PROMPT = """
Você é StreetCore AI.

Um agente executivo, estratégico, criativo e operacional.

Você atua como:
- CEO;
- COO;
- gerente operacional;
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

AGENTE OPERACIONAL DIÁRIO

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
""")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    projects = load_json(PROJECTS_FILE, [])
    tasks = load_json(TASKS_FILE, [])
    roadmaps = load_json(ROADMAPS_FILE, [])

    pendentes = len([t for t in tasks if t.get("status") == "pendente"])
    concluidas = len([t for t in tasks if t.get("status") == "concluída"])

    await update.message.reply_text(f"""
🚀 STATUS

Sistema: ONLINE
IA: Groq grátis
Imagem: Pollinations grátis
Memória: {len(memory)} itens
Projetos: {len(projects)}
Tarefas pendentes: {pendentes}
Tarefas concluídas: {concluidas}
Roadmaps: {len(roadmaps)}
Modo: CEO + COO + GERENTE DIÁRIO
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

    for i, p in enumerate(projects, start=1):
        text += f"{i}. {p['nome']}\n"

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

    text = "📝 TODAS AS TAREFAS:\n\n"

    for i, t in enumerate(tasks, start=1):
        text += f"{i}. {t['tarefa']} — {t['status']}\n"

    await update.message.reply_text(text)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_json(TASKS_FILE, [])

    pendentes = [
        (i, t) for i, t in enumerate(tasks, start=1)
        if t.get("status") == "pendente"
    ]

    if not pendentes:
        await update.message.reply_text("🔥 Nenhuma tarefa pendente. Você está limpo.")
        return

    text = "⚠️ TAREFAS PENDENTES:\n\n"

    for i, t in pendentes:
        text += f"{i}. {t['tarefa']}\n"

    text += "\nPara concluir, use:\n/concluir número"

    await update.message.reply_text(text)

async def concluir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use:\n/concluir número_da_tarefa")
        return

    try:
        numero = int(context.args[0])
    except:
        await update.message.reply_text("Digite um número válido. Exemplo:\n/concluir 1")
        return

    tasks = load_json(TASKS_FILE, [])

    if numero < 1 or numero > len(tasks):
        await update.message.reply_text("Essa tarefa não existe.")
        return

    tasks[numero - 1]["status"] = "concluída"
    tasks[numero - 1]["concluida_em"] = str(datetime.now())

    save_json(TASKS_FILE, tasks)

    await update.message.reply_text(
        f"✅ Tarefa concluída:\n{tasks[numero - 1]['tarefa']}"
    )

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
1. Visão geral
2. Estratégia principal
3. Etapas essenciais
4. Plano de 7 dias
5. Plano de 30 dias
6. Tarefas prioritárias
7. Ferramentas gratuitas recomendadas
8. Monetização
9. Riscos e gargalos
10. Próximo passo imediato
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

async def hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    tasks = load_json(TASKS_FILE, [])
    projects = load_json(PROJECTS_FILE, [])

    pendentes = [t["tarefa"] for t in tasks if t.get("status") == "pendente"]

    prompt = f"""
Crie um PLANO DE EXECUÇÃO PARA HOJE.

Dados:
Projetos: {projects}
Tarefas pendentes: {pendentes}

Estruture:
1. Prioridade número 1 do dia
2. 3 tarefas mais importantes
3. Ordem exata de execução
4. O que evitar hoje
5. Mini plano de foco de 2 horas
6. Próximo passo imediato

Se não houver tarefas, sugira tarefas estratégicas com base na memória.
"""

    resposta = ask_ai(prompt, memory)

    daily = load_json(DAILY_FILE, [])
    daily.append({
        "tipo": "hoje",
        "plano": resposta,
        "data": str(datetime.now())
    })
    save_json(DAILY_FILE, daily)

    await update.message.reply_text(resposta)

async def semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    tasks = load_json(TASKS_FILE, [])
    projects = load_json(PROJECTS_FILE, [])

    prompt = f"""
Crie um PLANO SEMANAL EXECUTIVO.

Dados:
Projetos: {projects}
Tarefas: {tasks}

Estruture:
1. Meta principal da semana
2. Segunda a domingo
3. Tarefas por dia
4. Entregáveis da semana
5. Ferramentas gratuitas úteis
6. Riscos da semana
7. Próximo passo imediato
"""

    resposta = ask_ai(prompt, memory)

    daily = load_json(DAILY_FILE, [])
    daily.append({
        "tipo": "semana",
        "plano": resposta,
        "data": str(datetime.now())
    })
    save_json(DAILY_FILE, daily)

    await update.message.reply_text(resposta)

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
app.add_handler(CommandHandler("check", check))
app.add_handler(CommandHandler("concluir", concluir))

app.add_handler(CommandHandler("roadmap", roadmap))
app.add_handler(CommandHandler("roadmaps", roadmaps))

app.add_handler(CommandHandler("hoje", hoje))
app.add_handler(CommandHandler("semana", semana))

app.add_handler(CommandHandler("imagem", imagem))
app.add_handler(CommandHandler("logo", logo))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI DAILY EXECUTION ONLINE")
app.run_polling()
