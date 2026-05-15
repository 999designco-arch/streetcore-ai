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
engenheiro de automação e assistente pessoal.
Explique passo a passo, como se estivesse pegando na mão do usuário.
Seja prático, premium, claro e operacional.
"""

def load_json(file, default):
    if not os.path.exists(file):
        return default
    with open(file, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def memory():
    return load_json(FILES["memory"], {})

def save_item(tipo, tema, conteudo):
    data = load_json(FILES["items"], [])
    data.append({"tipo": tipo, "tema": tema, "conteudo": conteudo, "data": str(datetime.now())})
    save_json(FILES["items"], data)

def auto_memory(msg):
    mem = memory()
    text = msg.lower()
    try:
        if "meu nome é" in text:
            mem["nome"] = text.split("meu nome é")[1].strip()
        if "minha marca é" in text:
            mem["marca"] = text.split("minha marca é")[1].strip()
        if "meu nicho é" in text:
            mem["nicho"] = text.split("meu nicho é")[1].strip()
        if "quero criar" in text:
            mem["objetivo"] = text.split("quero criar")[1].strip()
    except:
        pass
    mem["ultima_interacao"] = str(datetime.now())
    save_json(FILES["memory"], mem)

def ask_ai(prompt):
    mem = json.dumps(memory(), ensure_ascii=False, indent=2)
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": MASTER_PROMPT + f"\n\nMEMÓRIA:\n{mem}"},
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

async def menu(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI — CENTRAL DE COMANDOS

ESSENCIAL:
/start — iniciar o agente
/status — ver status
/menu — abrir este menu
/ajuda — explicar como usar
/comandos — lista completa

MEMÓRIA:
/memoria — ver memórias

TAREFAS:
/tarefa criar algo
/tarefas
/check
/concluir 1

IMAGEM:
/imagem descrição
/logo nome da marca

CEO / NEGÓCIOS:
/roadmap objetivo
/automacao objetivo
/conteudo tema
/oferta produto
/branding marca
/saas ideia
/site ideia
/doc tema

ASSISTENTE PESSOAL:
/agenda compromisso
/lembrete algo
/lembretes
/rotina objetivo
/habito hábito
/habitos
/dia

Exemplo:
/roadmap criar uma marca streetwear futurista
""")

async def ajuda(update, context):
    await update.message.reply_text("""
🧠 COMO USAR O STREETCORE AI

Você pode falar normalmente comigo ou usar comandos.

Exemplos prontos:

1. Criar tarefa:
/tarefa criar identidade visual da marca

2. Criar plano do dia:
/dia

3. Criar imagem:
/imagem tênis cyberpunk em rua neon

4. Criar logo:
/logo Street Graff

5. Criar negócio:
/roadmap marca de roupa futurista

6. Criar automação:
/automacao postar conteúdo todo dia

7. Criar conteúdo:
/conteudo marca streetwear

8. Criar SaaS:
/saas agente IA para empresas locais

9. Salvar lembrete:
/lembrete gravar vídeos amanhã

10. Ver menu:
/menu
""")

async def comandos(update, context):
    await update.message.reply_text("""
📌 LISTA COMPLETA

/start
/status
/menu
/ajuda
/comandos
/memoria

/tarefa
/tarefas
/check
/concluir

/imagem
/logo

/roadmap
/automacao
/conteudo
/oferta
/branding
/saas
/site
/doc

/agenda
/lembrete
/lembretes
/rotina
/habito
/habitos
/dia
""")

async def start(update, context):
    await update.message.reply_text("🔥 StreetCore AI online. Digite /menu para ver tudo que posso fazer.")

async def status(update, context):
    await update.message.reply_text(f"""
🚀 STATUS

Memórias: {len(load_json(FILES["memory"], {}))}
Tarefas: {len(load_json(FILES["tasks"], []))}
Itens salvos: {len(load_json(FILES["items"], []))}
Assistente pessoal: {len(load_json(FILES["assistant"], []))}

Sistema: ONLINE
IA: Groq grátis
Imagem: Pollinations grátis
Modo: OPERAÇÃO TOTAL
""")

async def memoria(update, context):
    mem = memory()
    if not mem:
        await update.message.reply_text("Nenhuma memória salva.")
        return
    text = "🧠 MEMÓRIAS:\n\n"
    for k, v in mem.items():
        text += f"• {k}: {v}\n"
    await send_long(update, text)

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

async def generic(update, context, tipo, prompt_base):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text(f"Use:\n/{tipo} tema")
        return
    resposta = ask_ai(f"{prompt_base}\n\nTema:\n{tema}")
    save_item(tipo, tema, resposta)
    await send_long(update, resposta)

async def roadmap(update, context):
    await generic(update, context, "roadmap", "Crie um roadmap executivo completo com estratégia, execução, monetização, ferramentas grátis, plano de 7 dias e 30 dias.")

async def automacao(update, context):
    await generic(update, context, "automacao", "Crie uma automação gratuita com ferramentas grátis, fluxo, passo a passo, execução e erros comuns.")

async def conteudo(update, context):
    await generic(update, context, "conteudo", "Crie conteúdo viral premium para Instagram/TikTok com gancho, legenda, CTA, hashtags e ideia visual.")

async def oferta(update, context):
    await generic(update, context, "oferta", "Crie uma oferta irresistível com dor, promessa, mecanismo único, bônus, urgência ética, preço sugerido e CTA.")

async def branding(update, context):
    await generic(update, context, "branding", "Crie branding completo com essência, posicionamento, público, personalidade, tom de voz, paleta, manifesto e próximos passos.")

async def saas(update, context):
    await generic(update, context, "saas", "Crie arquitetura completa de SaaS usando ferramentas grátis, incluindo MVP, features, stack, banco, login, dashboard, monetização e roadmap.")

async def site(update, context):
    await generic(update, context, "site", "Crie um site completo com estrutura, copy, design, HTML/CSS simples, como testar e como publicar grátis.")

async def doc(update, context):
    await generic(update, context, "doc", "Crie um documento profissional completo, organizado, claro, pronto para copiar e usar.")

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
    resposta = ask_ai(f"Crie uma rotina diária prática e inteligente para: {tema}")
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
""")
    await send_long(update, resposta)

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
    "tarefa": tarefa,
    "tarefas": tarefas,
    "check": check,
    "concluir": concluir,
    "imagem": imagem,
    "logo": logo,
    "roadmap": roadmap,
    "automacao": automacao,
    "conteudo": conteudo,
    "oferta": oferta,
    "branding": branding,
    "saas": saas,
    "site": site,
    "doc": doc,
    "agenda": agenda,
    "lembrete": lembrete,
    "lembretes": lembretes,
    "rotina": rotina,
    "habito": habito,
    "habitos": habitos,
    "dia": dia
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI COMMAND CENTER ONLINE")
app.run_polling()
