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
SALES_FILE = "sales.json"

MASTER_PROMPT = """
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, COO, diretor criativo, copywriter, vendedor, growth hacker, social media e engenheiro de automação.
Explique passo a passo, com execução prática, premium e clara.
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
        max_tokens=4000
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

def salvar_venda(tipo, tema, conteudo):
    sales = load_json(SALES_FILE, [])
    sales.append({
        "tipo": tipo,
        "tema": tema,
        "conteudo": conteudo,
        "data": str(datetime.now())
    })
    save_json(SALES_FILE, sales)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 STREETCORE AI ONLINE

COMANDOS PRINCIPAIS:

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

/oferta
/copy
/funil
/landing
/whatsapp
/vendas
""")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    projects = load_json(PROJECTS_FILE, [])
    tasks = load_json(TASKS_FILE, [])
    roadmaps = load_json(ROADMAPS_FILE, [])
    automations = load_json(AUTOMATIONS_FILE, [])
    contents = load_json(CONTENT_FILE, [])
    sales = load_json(SALES_FILE, [])

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
Vendas/Funis: {len(sales)}

Modo: CEO + AGÊNCIA + VENDAS + AUTOMAÇÃO
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

Inclua estratégia, execução, monetização, ferramentas grátis, plano de 7 dias e plano de 30 dias.
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
    resposta = ask_ai(f"Crie uma automação gratuita para:\n{objetivo}\nInclua ferramentas grátis, passo a passo, fluxo, execução e erros comuns.", load_memory())
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
    resposta = ask_ai(f"Crie um conteúdo viral premium para Instagram/TikTok sobre:\n{tema}\nInclua gancho, texto, legenda, CTA, hashtags e ideia visual.", load_memory())
    contents = load_json(CONTENT_FILE, [])
    contents.append({"tipo": "conteudo", "tema": tema, "conteudo": resposta, "data": str(datetime.now())})
    save_json(CONTENT_FILE, contents)
    await update.message.reply_text(resposta)

async def carrossel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie um carrossel viral para Instagram sobre:\n{tema}\nEstruture slide por slide com legenda e direção visual.", load_memory())
    await update.message.reply_text(resposta)

async def reels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie um roteiro de Reels/TikTok viral sobre:\n{tema}\nInclua hook, cena por cena, narração, texto na tela e CTA.", load_memory())
    await update.message.reply_text(resposta)

async def calendario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie um calendário de conteúdo de 30 dias para:\n{tema}\nInclua tema, formato, gancho, CTA e ferramenta grátis por dia.", load_memory())
    await update.message.reply_text(resposta)

async def campanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie uma campanha premium completa para:\n{tema}\nInclua conceito, público, oferta, posts, reels, funil grátis e plano de 7 dias.", load_memory())
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

async def oferta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    produto = " ".join(context.args)
    if not produto:
        await update.message.reply_text("Use:\n/oferta produto ou serviço")
        return

    resposta = ask_ai(f"""
Crie uma OFERTA IRRESISTÍVEL para:

{produto}

Inclua:
1. Público-alvo
2. Dor principal
3. Promessa forte
4. Mecanismo único
5. Benefícios
6. Bônus gratuitos
7. Garantia sem custo
8. Urgência ética
9. Preço sugerido
10. Oferta final pronta
""", load_memory())

    salvar_venda("oferta", produto, resposta)
    await update.message.reply_text(resposta)

async def copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    produto = " ".join(context.args)
    if not produto:
        await update.message.reply_text("Use:\n/copy produto ou serviço")
        return

    resposta = ask_ai(f"""
Crie uma copy de vendas premium para:

{produto}

Estrutura:
1. Headline
2. Subheadline
3. Problema
4. Agitação da dor
5. Solução
6. Benefícios
7. Prova/autoridade
8. Oferta
9. CTA forte
10. Versão curta para anúncio
""", load_memory())

    salvar_venda("copy", produto, resposta)
    await update.message.reply_text(resposta)

async def funil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    produto = " ".join(context.args)
    if not produto:
        await update.message.reply_text("Use:\n/funil produto ou serviço")
        return

    resposta = ask_ai(f"""
Crie um FUNIL DE VENDAS usando apenas ferramentas gratuitas/plano grátis para:

{produto}

Inclua:
1. Fonte de tráfego grátis
2. Conteúdo de atração
3. Isca digital gratuita
4. Captura de lead grátis
5. Sequência de nutrição
6. Oferta
7. Follow-up
8. Automação possível
9. Ferramentas grátis
10. Plano de implantação em 7 dias
""", load_memory())

    salvar_venda("funil", produto, resposta)
    await update.message.reply_text(resposta)

async def landing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    produto = " ".join(context.args)
    if not produto:
        await update.message.reply_text("Use:\n/landing produto ou serviço")
        return

    resposta = ask_ai(f"""
Crie uma landing page completa para:

{produto}

Inclua:
1. Hero section
2. Headline
3. Subheadline
4. Benefícios
5. Como funciona
6. Provas
7. Oferta
8. FAQ
9. CTA
10. Código HTML simples gratuito
""", load_memory())

    salvar_venda("landing", produto, resposta)
    await update.message.reply_text(resposta)

async def whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    produto = " ".join(context.args)
    if not produto:
        await update.message.reply_text("Use:\n/whatsapp produto ou serviço")
        return

    resposta = ask_ai(f"""
Crie uma sequência de mensagens de WhatsApp para vender:

{produto}

Inclua:
1. Primeira abordagem
2. Quebra de gelo
3. Diagnóstico
4. Apresentação da solução
5. Quebra de objeções
6. Fechamento
7. Follow-up 1
8. Follow-up 2
9. Mensagem final
10. Tom natural, humano e direto
""", load_memory())

    salvar_venda("whatsapp", produto, resposta)
    await update.message.reply_text(resposta)

async def vendas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sales = load_json(SALES_FILE, [])
    if not sales:
        await update.message.reply_text("Nenhuma estratégia de venda salva.")
        return

    text = "💰 VENDAS/FUNIS SALVOS:\n\n"
    for i, s in enumerate(sales, start=1):
        text += f"{i}. {s['tipo']} — {s['tema']}\n"
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

app.add_handler(CommandHandler("oferta", oferta))
app.add_handler(CommandHandler("copy", copy))
app.add_handler(CommandHandler("funil", funil))
app.add_handler(CommandHandler("landing", landing))
app.add_handler(CommandHandler("whatsapp", whatsapp))
app.add_handler(CommandHandler("vendas", vendas))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI SALES FUNNEL MODE ONLINE")
app.run_polling()
