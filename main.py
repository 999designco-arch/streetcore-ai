import os, json
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
engenheiro de automação e assistente pessoal.
Explique passo a passo como se estivesse pegando na mão do usuário.

Regra crítica:
Para ações sensíveis, peça aprovação antes de executar.
Ações sensíveis incluem enviar mensagem, publicar, apagar, alterar dados importantes,
mexer com dinheiro, contratar, comprar, deletar ou executar algo externo.
"""

AGENTS = {
    "ceo": "Você é o CEO Agent. Foque em estratégia, dinheiro, escala e prioridade.",
    "branding": "Você é o Branding Agent. Foque em marca, estética e posicionamento.",
    "conteudo": "Você é o Content Agent. Foque em conteúdo viral.",
    "vendas": "Você é o Sales Agent. Foque em oferta, copy e conversão.",
    "dev": "Você é o Dev Agent. Foque em tecnologia, código e deploy grátis.",
    "automacao": "Você é o Automation Agent. Foque em automações gratuitas.",
    "assistente": "Você é o Personal Assistant Agent. Foque em rotina, agenda e organização."
}

SENSITIVE_WORDS = [
    "enviar",
    "publique",
    "publicar",
    "postar agora",
    "apagar",
    "deletar",
    "excluir",
    "comprar",
    "pagar",
    "contratar",
    "cancelar",
    "mandar mensagem",
    "enviar email",
    "enviar e-mail",
    "alterar senha",
    "remover"
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

def save_memory(mem):
    save_json(FILES["memory"], mem)

def save_item(tipo, tema, conteudo):
    data = load_json(FILES["items"], [])
    data.append({
        "tipo": tipo,
        "tema": tema,
        "conteudo": conteudo,
        "data": str(datetime.now(TZ))
    })
    save_json(FILES["items"], data)

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
    save_memory(mem)

def is_sensitive(text):
    lower = text.lower()
    return any(word in lower for word in SENSITIVE_WORDS)

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore AI online com modo aprovação. Digite /menu.")

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI — CENTRAL

/status
/memoria
/tarefa
/tarefas
/check
/concluir

/ceo
/brandagent
/contentagent
/salesagent
/devagent
/autoagent
/agent

/ativar
/agendar
/agendamentos

APROVAÇÕES:
/pendentesaprovacao
/aprovar 1
/rejeitar 1
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
Modo: APROVAÇÃO SEGURA
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

async def tarefa(update, context):
    nome = " ".join(context.args)

    if not nome:
        await update.message.reply_text("Use:\n/tarefa criar logo")
        return

    tasks = load_json(FILES["tasks"], [])
    tasks.append({
        "tarefa": nome,
        "status": "pendente",
        "data": str(datetime.now(TZ))
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

    partes = texto.split(" ", 1)
    hora = partes[0]
    acao = partes[1]

    try:
        datetime.strptime(hora, "%H:%M")
    except:
        await update.message.reply_text("Horário inválido. Use:\n/agendar 09:00 revisar tarefas")
        return

    schedules = load_json(FILES["schedules"], [])
    schedules.append({
        "hora": hora,
        "acao": acao,
        "ativo": True,
        "ultimo_disparo": "",
        "data": str(datetime.now(TZ))
    })
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

    pendentes = [
        (i, a)
        for i, a in enumerate(approvals, 1)
        if a.get("status") == "pendente"
    ]

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

        resposta = ask_ai(f"""
A ação foi aprovada pelo usuário.

Ação:
{acao}

Agora entregue:
1. Confirmação
2. Plano de execução
3. Passo a passo
4. Como o usuário deve executar manualmente se necessário
""", "assistente")

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
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🛡 Ação sensível detectada no agendamento.\n\nAprovação criada #{idx}:\n{acao}\n\nUse /aprovar {idx} ou /rejeitar {idx}"
                )
            else:
                resposta = ask_ai(f"""
Execute este agendamento como assistente operacional:

Ação programada:
{acao}

Entregue:
1. O que fazer agora
2. Passo 1
3. Passo 2
4. Passo 3
5. Próxima ação imediata
""", "assistente")

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏰ AGENDAMENTO AUTOMÁTICO\n\n{s['hora']} — {acao}"
                )

                for i in range(0, len(resposta), 3900):
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=resposta[i:i+3900]
                    )

            s["ultimo_disparo"] = today
            changed = True

    if changed:
        save_json(FILES["schedules"], schedules)

async def handle_message(update, context):
    msg = update.message.text
    auto_memory(msg)

    if is_sensitive(msg):
        idx = save_approval(msg, "mensagem")
        await update.message.reply_text(
            f"🛡 Isso parece uma ação sensível.\n\nCriei uma aprovação pendente #{idx}.\n\nUse:\n/aprovar {idx}\n/rejeitar {idx}"
        )
        return

    resposta = ask_ai(msg)
    await send_long(update, resposta)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

commands = {
    "start": start,
    "menu": menu,
    "status": status,
    "memoria": memoria,
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
    "ativar": ativar,
    "agendar": agendar,
    "agendamentos": agendamentos,
    "pendentesaprovacao": pendentesaprovacao,
    "aprovar": aprovar,
    "rejeitar": rejeitar
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.job_queue.run_repeating(scheduled_checker, interval=60, first=10)

print("🔥 STREETCORE AI APPROVAL MODE ONLINE")
app.run_polling()
