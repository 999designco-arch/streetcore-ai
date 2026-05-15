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
PRODUCT_FILE = "products.json"

MASTER_PROMPT = """
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, COO, diretor criativo, estrategista, copywriter, vendedor, social media,
growth hacker, arquiteto de SaaS, criador de produtos digitais e engenheiro de automação.
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

def salvar(file, tipo, tema, conteudo):
    data = load_json(file, [])
    data.append({
        "tipo": tipo,
        "tema": tema,
        "conteudo": conteudo,
        "data": str(datetime.now())
    })
    save_json(file, data)

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

async def send_long(update, text):
    for i in range(0, len(text), 3900):
        await update.message.reply_text(text[i:i+3900])

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

/status /memoria

/projeto /projetos
/tarefa /tarefas /check /concluir

/roadmap /roadmaps
/hoje /semana

/imagem /logo

/automacao /fluxo /script /checklist /automacoes

/conteudo /carrossel /reels /calendario /campanha /conteudos

/oferta /copy /funil /landing /whatsapp /vendas

/branding /paleta /tomvoz /manifesto /brandbook /identidade /brandings

/ideia
/validar
/mvp
/features
/saas
/produto
/lancamento
/produtos
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
Produtos/SaaS: {len(load_json(PRODUCT_FILE, []))}

Modo: CEO + AGÊNCIA + VENDAS + BRANDING + SAAS
""")

async def memoria(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memory = load_memory()
    if not memory:
        await update.message.reply_text("Nenhuma memória salva.")
        return
    text = "🧠 MEMÓRIAS:\n\n"
    for k, v in memory.items():
        text += f"• {k}: {v}\n"
    await send_long(update, text)

async def projeto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/projeto nome")
        return
    salvar(PROJECTS_FILE, "projeto", tema, tema)
    await update.message.reply_text(f"✅ Projeto criado:\n{tema}")

async def projetos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_json(PROJECTS_FILE, [])
    if not data:
        await update.message.reply_text("Nenhum projeto.")
        return
    text = "📁 PROJETOS:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item['tema']}\n"
    await send_long(update, text)

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
    await send_long(update, text)

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
    await send_long(update, text)

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

async def ai_save(update, file, tipo, tema, prompt):
    if not tema:
        await update.message.reply_text(f"Use:\n/{tipo} tema")
        return
    resposta = ask_ai(prompt, load_memory())
    salvar(file, tipo, tema, resposta)
    await send_long(update, resposta)

async def roadmap(update, context):
    tema = " ".join(context.args)
    await ai_save(update, ROADMAPS_FILE, "roadmap", tema, f"Crie roadmap executivo completo para: {tema}. Inclua estratégia, execução, monetização, ferramentas grátis, plano de 7 dias e 30 dias.")

async def roadmaps(update, context):
    await listar(update, ROADMAPS_FILE, "🗺 ROADMAPS")

async def hoje(update, context):
    resposta = ask_ai(f"Crie um plano executivo para hoje com base nestas tarefas:\n{load_json(TASKS_FILE, [])}", load_memory())
    await send_long(update, resposta)

async def semana(update, context):
    resposta = ask_ai(f"Crie um plano semanal executivo com base nestas tarefas:\n{load_json(TASKS_FILE, [])}", load_memory())
    await send_long(update, resposta)

async def imagem(update, context):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Use:\n/imagem descrição")
        return
    await update.message.reply_text("🎨 Gerando imagem...")
    await update.message.reply_photo(photo=gerar_imagem_url(prompt))

async def logo(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/logo marca")
        return
    await update.message.reply_text("🔥 Criando logo...")
    await update.message.reply_photo(photo=gerar_imagem_url(f"minimal futuristic luxury logo, premium streetwear branding, white background, {tema}"))

async def automacao(update, context):
    tema = " ".join(context.args)
    await ai_save(update, AUTOMATIONS_FILE, "automacao", tema, f"Crie automação gratuita para: {tema}. Inclua ferramentas grátis, passo a passo, fluxo, execução e erros comuns.")

async def fluxo(update, context):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie fluxo operacional gratuito para: {tema}. Formato: INÍCIO → ETAPA → FINAL.", load_memory())
    await send_long(update, resposta)

async def script(update, context):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie script Python gratuito para: {tema}. Inclua código completo e como rodar.", load_memory())
    await send_long(update, resposta)

async def checklist(update, context):
    tema = " ".join(context.args)
    resposta = ask_ai(f"Crie checklist operacional completo para: {tema}", load_memory())
    await send_long(update, resposta)

async def automacoes(update, context):
    await listar(update, AUTOMATIONS_FILE, "⚙️ AUTOMAÇÕES")

async def conteudo(update, context):
    tema = " ".join(context.args)
    await ai_save(update, CONTENT_FILE, "conteudo", tema, f"Crie conteúdo viral premium para Instagram/TikTok sobre: {tema}. Inclua gancho, texto, legenda, CTA, hashtags e ideia visual.")

async def carrossel(update, context):
    tema = " ".join(context.args)
    await ai_save(update, CONTENT_FILE, "carrossel", tema, f"Crie carrossel viral para Instagram sobre: {tema}. Estruture slide por slide com legenda e direção visual.")

async def reels(update, context):
    tema = " ".join(context.args)
    await ai_save(update, CONTENT_FILE, "reels", tema, f"Crie roteiro de Reels/TikTok viral sobre: {tema}. Inclua hook, cena por cena, narração, texto na tela e CTA.")

async def calendario(update, context):
    tema = " ".join(context.args)
    await ai_save(update, CONTENT_FILE, "calendario", tema, f"Crie calendário de conteúdo de 30 dias para: {tema}. Inclua tema, formato, gancho, CTA e ferramenta grátis por dia.")

async def campanha(update, context):
    tema = " ".join(context.args)
    await ai_save(update, CONTENT_FILE, "campanha", tema, f"Crie campanha premium completa para: {tema}. Inclua conceito, público, oferta, posts, reels, funil grátis e plano de 7 dias.")

async def conteudos(update, context):
    await listar(update, CONTENT_FILE, "📲 CONTEÚDOS")

async def oferta(update, context):
    tema = " ".join(context.args)
    await ai_save(update, SALES_FILE, "oferta", tema, f"Crie oferta irresistível para: {tema}. Inclua público, dor, promessa, mecanismo único, bônus, urgência ética, preço sugerido e oferta final.")

async def copy(update, context):
    tema = " ".join(context.args)
    await ai_save(update, SALES_FILE, "copy", tema, f"Crie copy de vendas premium para: {tema}. Inclua headline, subheadline, problema, solução, benefícios, prova, oferta e CTA.")

async def funil(update, context):
    tema = " ".join(context.args)
    await ai_save(update, SALES_FILE, "funil", tema, f"Crie funil de vendas grátis para: {tema}. Inclua tráfego grátis, isca digital, captura, nutrição, oferta, follow-up, automação e plano de 7 dias.")

async def landing(update, context):
    tema = " ".join(context.args)
    await ai_save(update, SALES_FILE, "landing", tema, f"Crie landing page completa para: {tema}. Inclua hero, headline, benefícios, oferta, FAQ, CTA e HTML simples.")

async def whatsapp(update, context):
    tema = " ".join(context.args)
    await ai_save(update, SALES_FILE, "whatsapp", tema, f"Crie sequência de WhatsApp para vender: {tema}. Inclua abordagem, diagnóstico, solução, objeções, fechamento e follow-ups.")

async def vendas(update, context):
    await listar(update, SALES_FILE, "💰 VENDAS")

async def branding(update, context):
    tema = " ".join(context.args)
    await ai_save(update, BRANDING_FILE, "branding", tema, f"Crie estratégia completa de branding premium para: {tema}. Inclua essência, posicionamento, público, personalidade, promessa, diferencial, arquétipo, visual, tom de voz e próximos passos.")

async def paleta(update, context):
    tema = " ".join(context.args)
    await ai_save(update, BRANDING_FILE, "paleta", tema, f"Crie paleta de cores premium para: {tema}. Inclua HEX, psicologia das cores e aplicação.")

async def tomvoz(update, context):
    tema = " ".join(context.args)
    await ai_save(update, BRANDING_FILE, "tomvoz", tema, f"Crie tom de voz completo para: {tema}. Inclua palavras, estilo, exemplos, legenda e mensagens.")

async def manifesto(update, context):
    tema = " ".join(context.args)
    await ai_save(update, BRANDING_FILE, "manifesto", tema, f"Crie manifesto cinematográfico, forte e premium para a marca: {tema}.")

async def brandbook(update, context):
    tema = " ".join(context.args)
    await ai_save(update, BRANDING_FILE, "brandbook", tema, f"Crie mini brand book completo para: {tema}. Inclua missão, visão, valores, público, posicionamento, paleta, tipografia gratuita, tom de voz e regras de uso.")

async def identidade(update, context):
    tema = " ".join(context.args)
    await ai_save(update, BRANDING_FILE, "identidade", tema, f"Crie identidade visual completa para: {tema}. Inclua logo ideal, símbolos, paleta, tipografia gratuita, fotos, posts, embalagem e prompts.")

async def brandings(update, context):
    await listar(update, BRANDING_FILE, "🎯 BRANDINGS")

async def ideia(update, context):
    tema = " ".join(context.args)
    await ai_save(update, PRODUCT_FILE, "ideia", tema, f"""
Crie 10 ideias de produto digital/SaaS para:

{tema}

Para cada ideia inclua:
1. Nome
2. Problema que resolve
3. Público
4. Funcionalidade principal
5. Como fazer MVP grátis
6. Como monetizar
7. Dificuldade
8. Potencial de venda
""")

async def validar(update, context):
    tema = " ".join(context.args)
    await ai_save(update, PRODUCT_FILE, "validar", tema, f"""
Crie um plano de validação gratuito para:

{tema}

Inclua:
1. Hipótese
2. Público-alvo
3. Perguntas de validação
4. Como encontrar pessoas grátis
5. Landing page simples
6. Oferta teste
7. Métricas
8. Critério para continuar ou abandonar
9. Plano de 7 dias
""")

async def mvp(update, context):
    tema = " ".join(context.args)
    await ai_save(update, PRODUCT_FILE, "mvp", tema, f"""
Crie o MVP gratuito para:

{tema}

Inclua:
1. Versão mais simples possível
2. Funcionalidades essenciais
3. Funcionalidades que NÃO entram agora
4. Stack gratuita
5. Passo a passo de construção
6. Tela inicial
7. Fluxo do usuário
8. Como testar
9. Próxima melhoria
""")

async def features(update, context):
    tema = " ".join(context.args)
    await ai_save(update, PRODUCT_FILE, "features", tema, f"""
Crie lista de features para:

{tema}

Divida em:
1. Essenciais
2. Diferenciais
3. Futuras
4. Automáveis
5. Premium
6. Ordem correta de desenvolvimento
""")

async def saas(update, context):
    tema = " ".join(context.args)
    await ai_save(update, PRODUCT_FILE, "saas", tema, f"""
Crie arquitetura completa de SaaS gratuito/plano grátis para:

{tema}

Inclua:
1. Nome do SaaS
2. Proposta de valor
3. Público
4. Features
5. Stack grátis
6. Banco de dados grátis
7. Login grátis
8. Dashboard
9. Monetização
10. Roadmap 30 dias
11. Prompt para programar
""")

async def produto(update, context):
    tema = " ".join(context.args)
    await ai_save(update, PRODUCT_FILE, "produto", tema, f"""
Crie produto digital completo para:

{tema}

Inclua:
1. Nome
2. Promessa
3. Público-alvo
4. Entregável
5. Módulos
6. Bônus
7. Preço sugerido
8. Página de venda
9. Funil grátis
10. Plano de lançamento
""")

async def lancamento(update, context):
    tema = " ".join(context.args)
    await ai_save(update, PRODUCT_FILE, "lancamento", tema, f"""
Crie plano de lançamento gratuito para:

{tema}

Inclua:
1. Pré-lançamento
2. Conteúdo de aquecimento
3. Oferta
4. Sequência de posts
5. Reels
6. WhatsApp
7. Página simples
8. Dia do lançamento
9. Pós-lançamento
10. Plano de 14 dias
""")

async def produtos(update, context):
    await listar(update, PRODUCT_FILE, "🧩 PRODUTOS / SAAS")

async def listar(update, file, titulo):
    data = load_json(file, [])
    if not data:
        await update.message.reply_text("Nada salvo ainda.")
        return
    text = f"{titulo}:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item.get('tipo', 'item')} — {item.get('tema', 'sem tema')}\n"
    await send_long(update, text)

async def handle_message(update, context):
    user_message = update.message.text
    memory = load_memory()
    auto_memory(user_message, memory)
    resposta = ask_ai(user_message, memory)
    await send_long(update, resposta)

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

commands = {
    "start": start, "status": status, "memoria": memoria,
    "projeto": projeto, "projetos": projetos,
    "tarefa": tarefa, "tarefas": tarefas, "check": check, "concluir": concluir,
    "roadmap": roadmap, "roadmaps": roadmaps, "hoje": hoje, "semana": semana,
    "imagem": imagem, "logo": logo,
    "automacao": automacao, "fluxo": fluxo, "script": script, "checklist": checklist, "automacoes": automacoes,
    "conteudo": conteudo, "carrossel": carrossel, "reels": reels, "calendario": calendario, "campanha": campanha, "conteudos": conteudos,
    "oferta": oferta, "copy": copy, "funil": funil, "landing": landing, "whatsapp": whatsapp, "vendas": vendas,
    "branding": branding, "paleta": paleta, "tomvoz": tomvoz, "manifesto": manifesto, "brandbook": brandbook, "identidade": identidade, "brandings": brandings,
    "ideia": ideia, "validar": validar, "mvp": mvp, "features": features, "saas": saas, "produto": produto, "lancamento": lancamento, "produtos": produtos
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI SAAS PRODUCT MODE ONLINE")
app.run_polling()
