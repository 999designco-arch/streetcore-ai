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
BRANDING_FILE = "branding.json"

MASTER_PROMPT = """
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, COO, diretor criativo, estrategista de branding, copywriter, vendedor, social media, growth hacker e engenheiro de automação.
Explique passo a passo, com execução prática, premium e clara.
Estética padrão: street luxury, futurista, cinematográfica, cyberpunk minimalista e premium.
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

def salvar(file, tipo, tema, conteudo):
    data = load_json(file, [])
    data.append({
        "tipo": tipo,
        "tema": tema,
        "conteudo": conteudo,
        "data": str(datetime.now())
    })
    save_json(file, data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""
🔥 STREETCORE AI ONLINE

COMANDOS:

/status
/memoria

/projeto /projetos
/tarefa /tarefas /check /concluir

/roadmap /roadmaps
/hoje /semana

/imagem /logo

/automacao /fluxo /script /checklist /automacoes

/conteudo /carrossel /reels /calendario /campanha /conteudos

/oferta /copy /funil /landing /whatsapp /vendas

/branding
/paleta
/tomvoz
/manifesto
/brandbook
/identidade
/brandings
""")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"""
🚀 STATUS

Memória: {len(load_json(MEMORY_FILE, {}))}
Projetos: {len(load_json(PROJECTS_FILE, []))}
Tarefas: {len(load_json(TASKS_FILE, []))}
Roadmaps: {len(load_json(ROADMAPS_FILE, []))}
Automações: {len(load_json(AUTOMATIONS_FILE, []))}
Conteúdos: {len(load_json(CONTENT_FILE, []))}
Vendas: {len(load_json(SALES_FILE, []))}
Brandings: {len(load_json(BRANDING_FILE, []))}

Modo: CEO + AGÊNCIA + VENDAS + BRANDING
""")

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    if not memory:
        await update.message.reply_text("Nenhuma memória salva.")
        return
    text = "🧠 MEMÓRIAS:\n\n"
    for k, v in memory.items():
        text += f"• {k}: {v}\n"
    await update.message.reply_text(text)

async def projeto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = " ".join(context.args)
    if not nome:
        await update.message.reply_text("Use:\n/projeto nome")
        return
    salvar(PROJECTS_FILE, "projeto", nome, nome)
    await update.message.reply_text(f"✅ Projeto criado:\n{nome}")

async def projetos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(PROJECTS_FILE, [])
    if not data:
        await update.message.reply_text("Nenhum projeto.")
        return
    text = "📁 PROJETOS:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item['tema']}\n"
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
    for i, t in enumerate(tasks, 1):
        text += f"{i}. {t['tarefa']} — {t['status']}\n"
    await update.message.reply_text(text)

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasks = load_json(TASKS_FILE, [])
    pendentes = [(i, t) for i, t in enumerate(tasks, 1) if t.get("status") == "pendente"]
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
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/roadmap objetivo")
        return
    resposta = ask_ai(f"Crie um roadmap executivo completo para: {tema}. Inclua estratégia, execução, monetização, ferramentas grátis, plano de 7 dias e 30 dias.", load_memory())
    salvar(ROADMAPS_FILE, "roadmap", tema, resposta)
    await update.message.reply_text(resposta)

async def roadmaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(ROADMAPS_FILE, [])
    if not data:
        await update.message.reply_text("Nenhum roadmap.")
        return
    text = "🗺 ROADMAPS:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item['tema']}\n"
    await update.message.reply_text(text)

async def hoje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = ask_ai(f"Crie um plano executivo para hoje com base nestas tarefas:\n{load_json(TASKS_FILE, [])}", load_memory())
    await update.message.reply_text(resposta)

async def semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resposta = ask_ai(f"Crie um plano semanal executivo com base nestas tarefas:\n{load_json(TASKS_FILE, [])}", load_memory())
    await update.message.reply_text(resposta)

async def imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Use:\n/imagem descrição")
        return
    await update.message.reply_text("🎨 Gerando imagem...")
    await update.message.reply_photo(photo=gerar_imagem_url(prompt))

async def logo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/logo marca")
        return
    await update.message.reply_text("🔥 Criando logo...")
    await update.message.reply_photo(photo=gerar_imagem_url(f"minimal futuristic luxury logo, premium streetwear branding, white background, {tema}"))

async def automacao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie uma automação gratuita para: {tema}. Inclua ferramentas grátis, passo a passo, fluxo, execução e erros comuns.", load_memory())
    salvar(AUTOMATIONS_FILE, "automacao", tema, resposta)
    await update.message.reply_text(resposta)

async def fluxo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie um fluxo operacional gratuito para: {tema}. Formato: INÍCIO → ETAPA → FINAL.", load_memory())
    await update.message.reply_text(resposta)

async def script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie um script Python gratuito para: {tema}. Inclua código completo e como rodar.", load_memory())
    await update.message.reply_text(resposta)

async def checklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie um checklist operacional completo para: {tema}", load_memory())
    await update.message.reply_text(resposta)

async def automacoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(AUTOMATIONS_FILE, [])
    if not data:
        await update.message.reply_text("Nenhuma automação.")
        return
    text = "⚙️ AUTOMAÇÕES:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item['tema']}\n"
    await update.message.reply_text(text)

async def conteudo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie conteúdo viral premium para Instagram/TikTok sobre: {tema}. Inclua gancho, texto, legenda, CTA, hashtags e ideia visual.", load_memory())
    salvar(CONTENT_FILE, "conteudo", tema, resposta)
    await update.message.reply_text(resposta)

async def carrossel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie carrossel viral para Instagram sobre: {tema}. Estruture slide por slide com legenda e direção visual.", load_memory())
    salvar(CONTENT_FILE, "carrossel", tema, resposta)
    await update.message.reply_text(resposta)

async def reels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie roteiro de Reels/TikTok viral sobre: {tema}. Inclua hook, cena por cena, narração, texto na tela e CTA.", load_memory())
    salvar(CONTENT_FILE, "reels", tema, resposta)
    await update.message.reply_text(resposta)

async def calendario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie calendário de conteúdo de 30 dias para: {tema}. Inclua tema, formato, gancho, CTA e ferramenta grátis por dia.", load_memory())
    salvar(CONTENT_FILE, "calendario", tema, resposta)
    await update.message.reply_text(resposta)

async def campanha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie campanha premium completa para: {tema}. Inclua conceito, público, oferta, posts, reels, funil grátis e plano de 7 dias.", load_memory())
    salvar(CONTENT_FILE, "campanha", tema, resposta)
    await update.message.reply_text(resposta)

async def conteudos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(CONTENT_FILE, [])
    if not data:
        await update.message.reply_text("Nenhum conteúdo salvo.")
        return
    text = "📲 CONTEÚDOS:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item['tipo']} — {item['tema']}\n"
    await update.message.reply_text(text)

async def oferta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie oferta irresistível para: {tema}. Inclua público, dor, promessa, mecanismo único, bônus, urgência ética, preço sugerido e oferta final.", load_memory())
    salvar(SALES_FILE, "oferta", tema, resposta)
    await update.message.reply_text(resposta)

async def copy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie copy de vendas premium para: {tema}. Inclua headline, subheadline, problema, solução, benefícios, prova, oferta e CTA.", load_memory())
    salvar(SALES_FILE, "copy", tema, resposta)
    await update.message.reply_text(resposta)

async def funil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie funil de vendas grátis para: {tema}. Inclua tráfego grátis, isca digital, captura, nutrição, oferta, follow-up, automação e plano de 7 dias.", load_memory())
    salvar(SALES_FILE, "funil", tema, resposta)
    await update.message.reply_text(resposta)

async def landing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie landing page completa para: {tema}. Inclua hero, headline, benefícios, oferta, FAQ, CTA e HTML simples.", load_memory())
    salvar(SALES_FILE, "landing", tema, resposta)
    await update.message.reply_text(resposta)

async def whatsapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie sequência de WhatsApp para vender: {tema}. Inclua abordagem, diagnóstico, solução, objeções, fechamento e follow-ups.", load_memory())
    salvar(SALES_FILE, "whatsapp", tema, resposta)
    await update.message.reply_text(resposta)

async def vendas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(SALES_FILE, [])
    if not data:
        await update.message.reply_text("Nenhuma estratégia salva.")
        return
    text = "💰 VENDAS:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item['tipo']} — {item['tema']}\n"
    await update.message.reply_text(text)

async def branding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    marca = " ".join(context.args)
    if not marca:
        await update.message.reply_text("Use:\n/branding nome ou ideia da marca")
        return
    resposta = ask_ai(f"""
Crie uma estratégia completa de BRANDING PREMIUM para:

{marca}

Inclua:
1. Essência da marca
2. Posicionamento
3. Público-alvo
4. Personalidade
5. Promessa central
6. Diferenciais
7. Arquétipo da marca
8. Estilo visual
9. Tom de voz
10. Ideias de conteúdo
11. Ferramentas gratuitas para executar
12. Próximo passo imediato
""", load_memory())
    salvar(BRANDING_FILE, "branding", marca, resposta)
    await update.message.reply_text(resposta)

async def paleta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    marca = " ".join(context.args)
    resposta = ask_ai(f"""
Crie uma PALETA DE CORES premium para:

{marca}

Inclua:
- cor principal com HEX;
- cor secundária com HEX;
- cor de contraste com HEX;
- cor de fundo com HEX;
- cor de destaque com HEX;
- significado psicológico;
- onde usar cada cor;
- estilo visual recomendado.
""", load_memory())
    salvar(BRANDING_FILE, "paleta", marca, resposta)
    await update.message.reply_text(resposta)

async def tomvoz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    marca = " ".join(context.args)
    resposta = ask_ai(f"""
Crie o TOM DE VOZ completo para:

{marca}

Inclua:
1. Personalidade verbal
2. Palavras que deve usar
3. Palavras que deve evitar
4. Como falar no Instagram
5. Como falar no WhatsApp
6. Como vender
7. 10 frases modelo
8. Exemplo de legenda
""", load_memory())
    salvar(BRANDING_FILE, "tomvoz", marca, resposta)
    await update.message.reply_text(resposta)

async def manifesto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    marca = " ".join(context.args)
    resposta = ask_ai(f"""
Crie um MANIFESTO cinematográfico, forte e premium para a marca:

{marca}

Estilo:
- street luxury;
- futurista;
- emocional;
- memorável;
- direto;
- com força de marca global.
""", load_memory())
    salvar(BRANDING_FILE, "manifesto", marca, resposta)
    await update.message.reply_text(resposta)

async def brandbook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    marca = " ".join(context.args)
    resposta = ask_ai(f"""
Crie um MINI BRAND BOOK completo para:

{marca}

Inclua:
1. Nome
2. Slogan
3. Missão
4. Visão
5. Valores
6. Público
7. Posicionamento
8. Personalidade
9. Paleta de cores
10. Tipografia sugerida gratuita
11. Tom de voz
12. Estilo visual
13. Regras de uso
14. Ideias de aplicação
15. Próximos passos
""", load_memory())
    salvar(BRANDING_FILE, "brandbook", marca, resposta)
    await update.message.reply_text(resposta)

async def identidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    marca = " ".join(context.args)
    resposta = ask_ai(f"""
Crie uma IDENTIDADE VISUAL completa para:

{marca}

Inclua:
1. Direção criativa
2. Logo ideal
3. Símbolos
4. Paleta
5. Tipografia gratuita
6. Estilo de fotos
7. Estilo de posts
8. Estilo de embalagem
9. Prompt para gerar imagens
10. Prompt para gerar logo
11. Ferramentas gratuitas
""", load_memory())
    salvar(BRANDING_FILE, "identidade", marca, resposta)
    await update.message.reply_text(resposta)

async def brandings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(BRANDING_FILE, [])
    if not data:
        await update.message.reply_text("Nenhum branding salvo.")
        return
    text = "🎯 BRANDINGS SALVOS:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item['tipo']} — {item['tema']}\n"
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

app.add_handler(CommandHandler("branding", branding))
app.add_handler(CommandHandler("paleta", paleta))
app.add_handler(CommandHandler("tomvoz", tomvoz))
app.add_handler(CommandHandler("manifesto", manifesto))
app.add_handler(CommandHandler("brandbook", brandbook))
app.add_handler(CommandHandler("identidade", identidade))
app.add_handler(CommandHandler("brandings", brandings))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI BRANDING MODE ONLINE")
app.run_polling()
