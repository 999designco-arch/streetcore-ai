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
Aja como CEO, estrategista, diretor criativo, programador, vendedor,
engenheiro de automação e assistente pessoal.
Explique passo a passo como se estivesse pegando na mão do usuário.
"""

AGENTS = {
    "ceo": "Você é o CEO Agent.",
    "branding": "Você é o Branding Agent.",
    "conteudo": "Você é o Content Agent.",
    "vendas": "Você é o Sales Agent.",
    "dev": "Você é o Dev Agent.",
    "automacao": "Você é o Automation Agent.",
    "assistente": "Você é o Personal Assistant Agent."
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
    data.append({
        "tipo": tipo,
        "tema": tema,
        "conteudo": conteudo,
        "data": str(datetime.now())
    })
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
            {
                "role": "system",
                "content": MASTER_PROMPT + "\n\n" + agent_prompt + f"\n\nMEMÓRIA:\n{mem}"
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.8,
        max_tokens=4000
    )

    return r.choices[0].message.content

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

def image_url(prompt):
    p = urllib.parse.quote(
        f"ultra realistic cinematic image, street luxury futuristic, cyberpunk premium, 8k. {prompt}"
    )
    return f"https://image.pollinations.ai/prompt/{p}?width=1024&height=1024&seed=77"

async def start(update, context):
    await update.message.reply_text(
        "🔥 StreetCore AI online.\nDigite /menu para abrir a central."
    )

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI — CENTRAL

ESSENCIAL:
/menu
/status
/ajuda
/comandos

MEMÓRIA:
/memoria
/perfil
/objetivo
/preferencia

BACKUP:
/backup
/exportar
/listar
/historico
/apagaritem

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
""")

async def ajuda(update, context):
    await update.message.reply_text("""
🧠 COMO USAR

Exemplos:

/perfil nome = Rafael
/objetivo criar uma marca
/preferencia usar ferramentas grátis

/agent quero lançar uma empresa de IA
/ceo como escalar meu projeto
/devagent criar um app
/contentagent criar reels virais
""")

async def comandos(update, context):
    await menu(update, context)

async def status(update, context):
    mem = memory()

    await update.message.reply_text(f"""
🚀 STATUS

Perfil: {len(mem.get("perfil", {}))}
Objetivos: {len(mem.get("objetivos", []))}
Preferências: {len(mem.get("preferencias", []))}
Tarefas: {len(load_json(FILES["tasks"], []))}
Itens: {len(load_json(FILES["items"], []))}
Assistente: {len(load_json(FILES["assistant"], []))}

Sistema: ONLINE
Modo: MULTIAGENTES + BACKUP
""")

async def memoria(update, context):
    mem = memory()

    text = "🧠 MEMÓRIA:\n\n"

    text += "👤 PERFIL:\n"
    for k, v in mem.get("perfil", {}).items():
        text += f"• {k}: {v}\n"

    text += "\n🎯 OBJETIVOS:\n"
    for i, obj in enumerate(mem.get("objetivos", []), 1):
        text += f"{i}. {obj}\n"

    text += "\n⚙️ PREFERÊNCIAS:\n"
    for i, pref in enumerate(mem.get("preferencias", []), 1):
        text += f"{i}. {pref}\n"

    await send_long(update, text)

async def perfil(update, context):
    texto = " ".join(context.args)

    if "=" not in texto:
        await update.message.reply_text("Use:\n/perfil nome = Rafael")
        return

    chave, valor = texto.split("=", 1)

    mem = memory()
    mem["perfil"][chave.strip()] = valor.strip()

    save_memory(mem)

    await update.message.reply_text("✅ Perfil salvo.")

async def objetivo(update, context):
    texto = " ".join(context.args)

    mem = memory()
    mem["objetivos"].append(texto)

    save_memory(mem)

    await update.message.reply_text("🎯 Objetivo salvo.")

async def preferencia(update, context):
    texto = " ".join(context.args)

    mem = memory()
    mem["preferencias"].append(texto)

    save_memory(mem)

    await update.message.reply_text("⚙️ Preferência salva.")

async def tarefa(update, context):
    nome = " ".join(context.args)

    tasks = load_json(FILES["tasks"], [])

    tasks.append({
        "tarefa": nome,
        "status": "pendente",
        "data": str(datetime.now())
    })

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

    for i, t in enumerate(tasks, 1):
        if t["status"] == "pendente":
            text += f"{i}. {t['tarefa']}\n"

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

    resposta = ask_ai(prompt + "\n\nTema:\n" + tema, agent)

    save_item(tipo, tema, resposta)

    await send_long(update, resposta)

async def ceo(update, context):
    await generic(update, context, "ceo", "Analise como CEO.", "ceo")

async def brandagent(update, context):
    await generic(update, context, "branding", "Crie branding premium.", "branding")

async def contentagent(update, context):
    await generic(update, context, "conteudo", "Crie conteúdo viral.", "conteudo")

async def salesagent(update, context):
    await generic(update, context, "vendas", "Crie estratégia de vendas.", "vendas")

async def devagent(update, context):
    await generic(update, context, "dev", "Crie solução técnica.", "dev")

async def autoagent(update, context):
    await generic(update, context, "automacao", "Crie automação.", "automacao")

async def agent(update, context):
    tema = " ".join(context.args)

    prompt = f"""
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
"""

    resposta = ask_ai(prompt)

    save_item("multiagent", tema, resposta)

    await send_long(update, resposta)

async def backup(update, context):
    backup_data = {
        "memory": load_json(FILES["memory"], {}),
        "tasks": load_json(FILES["tasks"], []),
        "items": load_json(FILES["items"], []),
        "assistant": load_json(FILES["assistant"], [])
    }

    text = json.dumps(backup_data, ensure_ascii=False, indent=2)

    with open("backup_streetcore.json", "w", encoding="utf-8") as f:
        f.write(text)

    await update.message.reply_document(document=open("backup_streetcore.json", "rb"))

async def exportar(update, context):
    items = load_json(FILES["items"], [])

    if not items:
        await update.message.reply_text("Nada para exportar.")
        return

    text = "📦 EXPORTAÇÃO STREETCORE\n\n"

    for i, item in enumerate(items, 1):
        text += f"""
#{i}
TIPO: {item['tipo']}
TEMA: {item['tema']}
DATA: {item['data']}

{item['conteudo']}

------------------------
"""

    with open("exportacao_streetcore.txt", "w", encoding="utf-8") as f:
        f.write(text)

    await update.message.reply_document(document=open("exportacao_streetcore.txt", "rb"))

async def listar(update, context):
    items = load_json(FILES["items"], [])

    if not items:
        await update.message.reply_text("Nenhum item salvo.")
        return

    text = "📚 ITENS SALVOS:\n\n"

    for i, item in enumerate(items, 1):
        text += f"{i}. [{item['tipo']}] {item['tema']}\n"

    await send_long(update, text)

async def historico(update, context):
    items = load_json(FILES["items"], [])

    if not items:
        await update.message.reply_text("Nenhum histórico.")
        return

    text = "🕘 HISTÓRICO:\n\n"

    for i, item in enumerate(items[-20:], 1):
        text += f"""
{i}. {item['tipo']}
Tema: {item['tema']}
Data: {item['data']}

"""

    await send_long(update, text)

async def apagaritem(update, context):
    try:
        n = int(context.args[0])

        items = load_json(FILES["items"], [])

        removido = items.pop(n - 1)

        save_json(FILES["items"], items)

        await update.message.reply_text(
            f"🗑 Item apagado:\n{removido['tema']}"
        )

    except:
        await update.message.reply_text("Use:\n/apagaritem 1")

async def handle_message(update, context):
    msg = update.message.text

    auto_memory(msg)

    resposta = ask_ai(msg)

    await send_long(update, resposta)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

commands = {
    "start": start,
    "menu": menu,
    "ajuda": ajuda,
    "comandos": comandos,
    "status": status,
    "memoria": memoria,
    "perfil": perfil,
    "objetivo": objetivo,
    "preferencia": preferencia,
    "tarefa": tarefa,
    "tarefas": tarefas,
    "check": check,
    "concluir": concluir,
    "ceo": ceo,
    "brandagent": brandagent,
    "contentagent": contentagent,
    "salesagent": salesagent,
    "devagent": devagent,
    "autoagent": autoagent,
    "agent": agent,
    "backup": backup,
    "exportar": exportar,
    "listar": listar,
    "historico": historico,
    "apagaritem": apagaritem
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI BACKUP MODE ONLINE")
app.run_polling()
