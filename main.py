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

FILES = {
    "memory": "memory.json",
    "projects": "projects.json",
    "tasks": "tasks.json",
    "roadmaps": "roadmaps.json",
    "automations": "automations.json",
    "content": "content.json",
    "sales": "sales.json",
    "branding": "branding.json",
    "products": "products.json",
    "dev": "dev.json"
}

MASTER_PROMPT = """
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, COO, diretor criativo, estrategista, copywriter, vendedor, social media,
growth hacker, arquiteto de SaaS, programador full-stack, engenheiro de automação e operador técnico.
Explique passo a passo, como se estivesse pegando na mão do usuário.
Sempre entregue execução prática, premium e clara.
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
    data.append({"tipo": tipo, "tema": tema, "conteudo": conteudo, "data": str(datetime.now())})
    save_json(file, data)

def load_memory():
    return load_json(FILES["memory"], {})

def save_memory(memory):
    save_json(FILES["memory"], memory)

def auto_memory(msg, memory):
    text = msg.lower()
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
    premium_prompt = f"ultra realistic cinematic image, street luxury futuristic aesthetic, cyberpunk executive style, premium lighting, 8k, highly detailed. {prompt}"
    encoded = urllib.parse.quote(premium_prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1024&height=1024&seed=77"

async def ai_save(update, file, tipo, tema, prompt):
    if not tema:
        await update.message.reply_text(f"Use:\n/{tipo} tema")
        return
    resposta = ask_ai(prompt, load_memory())
    salvar(file, tipo, tema, resposta)
    await send_long(update, resposta)

async def listar(update, file, titulo):
    data = load_json(file, [])
    if not data:
        await update.message.reply_text("Nada salvo ainda.")
        return
    text = f"{titulo}:\n\n"
    for i, item in enumerate(data, 1):
        text += f"{i}. {item.get('tipo', 'item')} — {item.get('tema', 'sem tema')}\n"
    await send_long(update, text)

async def start(update, context):
    await update.message.reply_text("""
🔥 STREETCORE AI ONLINE

NOVO MODO: DEV / PROGRAMAÇÃO

Comandos principais:
/status /memoria
/projeto /projetos
/tarefa /tarefas /check /concluir
/roadmap /roadmaps /hoje /semana
/imagem /logo
/automacao /fluxo /script /checklist /automacoes
/conteudo /carrossel /reels /calendario /campanha /conteudos
/oferta /copy /funil /landing /whatsapp /vendas
/branding /paleta /tomvoz /manifesto /brandbook /identidade /brandings
/ideia /validar /mvp /features /saas /produto /lancamento /produtos

DEV:
/site
/app
/api
/banco
/deploy
/github
/debug
/arquitetura
/devs
""")

async def status(update, context):
    await update.message.reply_text(f"""
🚀 STATUS

Memória: {len(load_json(FILES["memory"], {}))}
Projetos: {len(load_json(FILES["projects"], []))}
Tarefas: {len(load_json(FILES["tasks"], []))}
Roadmaps: {len(load_json(FILES["roadmaps"], []))}
Automações: {len(load_json(FILES["automations"], []))}
Conteúdos: {len(load_json(FILES["content"], []))}
Vendas: {len(load_json(FILES["sales"], []))}
Brandings: {len(load_json(FILES["branding"], []))}
Produtos/SaaS: {len(load_json(FILES["products"], []))}
DEV: {len(load_json(FILES["dev"], []))}

Modo: CEO + AGÊNCIA + SAAS + DEV
""")

async def memoria(update, context):
    memory = load_memory()
    if not memory:
        await update.message.reply_text("Nenhuma memória salva.")
        return
    text = "🧠 MEMÓRIAS:\n\n"
    for k, v in memory.items():
        text += f"• {k}: {v}\n"
    await send_long(update, text)

async def projeto(update, context):
    tema = " ".join(context.args)
    if not tema:
        await update.message.reply_text("Use:\n/projeto nome")
        return
    salvar(FILES["projects"], "projeto", tema, tema)
    await update.message.reply_text(f"✅ Projeto criado:\n{tema}")

async def projetos(update, context):
    await listar(update, FILES["projects"], "📁 PROJETOS")

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
    pendentes = [(i, t) for i, t in enumerate(tasks, 1) if t.get("status") == "pendente"]
    if not pendentes:
        await update.message.reply_text("🔥 Nenhuma pendência.")
        return
    text = "⚠️ PENDENTES:\n\n"
    for i, t in pendentes:
        text += f"{i}. {t['tarefa']}\n"
    text += "\n/concluir número"
    await send_long(update, text)

async def concluir(update, context):
    if not context.args:
        await update.message.reply_text("Use:\n/concluir número")
        return
    try:
        numero = int(context.args[0])
    except:
        await update.message.reply_text("Número inválido.")
        return
    tasks = load_json(FILES["tasks"], [])
    if numero < 1 or numero > len(tasks):
        await update.message.reply_text("Tarefa inexistente.")
        return
    tasks[numero - 1]["status"] = "concluída"
    save_json(FILES["tasks"], tasks)
    await update.message.reply_text("✅ Tarefa concluída.")

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

async def simple_command(update, context, file_key, tipo, prompt_base):
    tema = " ".join(context.args)
    await ai_save(update, FILES[file_key], tipo, tema, f"{prompt_base}\n\nTema:\n{tema}")

async def roadmap(update, context):
    await simple_command(update, context, "roadmaps", "roadmap", "Crie roadmap executivo completo. Inclua estratégia, execução, monetização, ferramentas grátis, plano de 7 dias e 30 dias.")

async def roadmaps(update, context): await listar(update, FILES["roadmaps"], "🗺 ROADMAPS")
async def automacoes(update, context): await listar(update, FILES["automations"], "⚙️ AUTOMAÇÕES")
async def conteudos(update, context): await listar(update, FILES["content"], "📲 CONTEÚDOS")
async def vendas(update, context): await listar(update, FILES["sales"], "💰 VENDAS")
async def brandings(update, context): await listar(update, FILES["branding"], "🎯 BRANDINGS")
async def produtos(update, context): await listar(update, FILES["products"], "🧩 PRODUTOS / SAAS")
async def devs(update, context): await listar(update, FILES["dev"], "💻 DEV / PROGRAMAÇÃO")

async def hoje(update, context):
    resposta = ask_ai(f"Crie plano executivo para hoje com base nestas tarefas:\n{load_json(FILES['tasks'], [])}", load_memory())
    await send_long(update, resposta)

async def semana(update, context):
    resposta = ask_ai(f"Crie plano semanal executivo com base nestas tarefas:\n{load_json(FILES['tasks'], [])}", load_memory())
    await send_long(update, resposta)

async def automacao(update, context): await simple_command(update, context, "automations", "automacao", "Crie automação gratuita. Inclua ferramentas grátis, passo a passo, fluxo, execução e erros comuns.")
async def fluxo(update, context): await simple_command(update, context, "automations", "fluxo", "Crie fluxo operacional gratuito no formato INÍCIO → ETAPA → FINAL.")
async def script(update, context): await simple_command(update, context, "automations", "script", "Crie script Python gratuito. Inclua código completo e como rodar.")
async def checklist(update, context): await simple_command(update, context, "automations", "checklist", "Crie checklist operacional completo.")

async def conteudo(update, context): await simple_command(update, context, "content", "conteudo", "Crie conteúdo viral premium para Instagram/TikTok. Inclua gancho, texto, legenda, CTA, hashtags e ideia visual.")
async def carrossel(update, context): await simple_command(update, context, "content", "carrossel", "Crie carrossel viral para Instagram, slide por slide, com legenda e direção visual.")
async def reels(update, context): await simple_command(update, context, "content", "reels", "Crie roteiro de Reels/TikTok viral com hook, cenas, narração, texto na tela e CTA.")
async def calendario(update, context): await simple_command(update, context, "content", "calendario", "Crie calendário de conteúdo de 30 dias com tema, formato, gancho, CTA e ferramenta grátis por dia.")
async def campanha(update, context): await simple_command(update, context, "content", "campanha", "Crie campanha premium completa com conceito, público, oferta, posts, reels, funil grátis e plano de 7 dias.")

async def oferta(update, context): await simple_command(update, context, "sales", "oferta", "Crie oferta irresistível com público, dor, promessa, mecanismo único, bônus, urgência ética, preço sugerido e oferta final.")
async def copy(update, context): await simple_command(update, context, "sales", "copy", "Crie copy de vendas premium com headline, subheadline, problema, solução, benefícios, prova, oferta e CTA.")
async def funil(update, context): await simple_command(update, context, "sales", "funil", "Crie funil de vendas grátis com tráfego grátis, isca, captura, nutrição, oferta, follow-up, automação e plano de 7 dias.")
async def landing(update, context): await simple_command(update, context, "sales", "landing", "Crie landing page completa com hero, headline, benefícios, oferta, FAQ, CTA e HTML simples.")
async def whatsapp(update, context): await simple_command(update, context, "sales", "whatsapp", "Crie sequência de WhatsApp para vender com abordagem, diagnóstico, solução, objeções, fechamento e follow-ups.")

async def branding(update, context): await simple_command(update, context, "branding", "branding", "Crie estratégia completa de branding premium com essência, posicionamento, público, personalidade, promessa, diferencial, arquétipo, visual, tom de voz e próximos passos.")
async def paleta(update, context): await simple_command(update, context, "branding", "paleta", "Crie paleta de cores premium com HEX, psicologia das cores e aplicação.")
async def tomvoz(update, context): await simple_command(update, context, "branding", "tomvoz", "Crie tom de voz completo com palavras, estilo, exemplos, legenda e mensagens.")
async def manifesto(update, context): await simple_command(update, context, "branding", "manifesto", "Crie manifesto cinematográfico, forte e premium.")
async def brandbook(update, context): await simple_command(update, context, "branding", "brandbook", "Crie mini brand book completo com missão, visão, valores, público, posicionamento, paleta, tipografia gratuita, tom de voz e regras.")
async def identidade(update, context): await simple_command(update, context, "branding", "identidade", "Crie identidade visual completa com logo ideal, símbolos, paleta, tipografia gratuita, fotos, posts, embalagem e prompts.")

async def ideia(update, context): await simple_command(update, context, "products", "ideia", "Crie 10 ideias de produto digital/SaaS com nome, problema, público, MVP grátis, monetização, dificuldade e potencial.")
async def validar(update, context): await simple_command(update, context, "products", "validar", "Crie plano de validação gratuito com hipótese, público, perguntas, onde achar pessoas, landing, oferta teste, métricas e plano de 7 dias.")
async def mvp(update, context): await simple_command(update, context, "products", "mvp", "Crie MVP gratuito com versão simples, features essenciais, stack grátis, passo a passo, tela inicial, fluxo e teste.")
async def features(update, context): await simple_command(update, context, "products", "features", "Crie lista de features dividida em essenciais, diferenciais, futuras, automáveis, premium e ordem de desenvolvimento.")
async def saas(update, context): await simple_command(update, context, "products", "saas", "Crie arquitetura completa de SaaS gratuito/plano grátis com nome, proposta, público, features, stack, banco, login, dashboard, monetização e roadmap.")
async def produto(update, context): await simple_command(update, context, "products", "produto", "Crie produto digital completo com nome, promessa, público, entregável, módulos, bônus, preço, página de venda, funil e lançamento.")
async def lancamento(update, context): await simple_command(update, context, "products", "lancamento", "Crie plano de lançamento gratuito com pré-lançamento, conteúdo, oferta, posts, reels, WhatsApp, página, lançamento e pós.")

async def site(update, context):
    await simple_command(update, context, "dev", "site", """
Crie um site completo e gratuito.

Inclua:
1. Objetivo do site
2. Estrutura das páginas
3. Copy principal
4. Design visual
5. Código HTML + CSS completo em um único arquivo
6. Como testar no navegador
7. Como publicar grátis no GitHub Pages
8. Próximo passo
""")

async def app_cmd(update, context):
    await simple_command(update, context, "dev", "app", """
Crie um app simples gratuito.

Inclua:
1. Ideia do app
2. Funcionalidades
3. Telas
4. Fluxo do usuário
5. Stack grátis recomendada
6. Código inicial
7. Como rodar
8. Como evoluir
""")

async def api(update, context):
    await simple_command(update, context, "dev", "api", """
Crie uma API gratuita.

Inclua:
1. Objetivo da API
2. Endpoints
3. Estrutura dos dados
4. Código completo em Python FastAPI
5. requirements.txt
6. Como rodar localmente
7. Como publicar grátis
8. Próxima melhoria
""")

async def banco(update, context):
    await simple_command(update, context, "dev", "banco", """
Crie estrutura de banco de dados grátis.

Inclua:
1. Entidades
2. Tabelas
3. Campos
4. Relacionamentos
5. SQL completo
6. Opção Supabase grátis
7. Como criar passo a passo
8. Cuidados
""")

async def deploy(update, context):
    await simple_command(update, context, "dev", "deploy", """
Crie plano de deploy gratuito.

Inclua:
1. Melhor hospedagem grátis
2. Passo a passo
3. Variáveis de ambiente
4. GitHub
5. Logs
6. Como testar
7. Como corrigir erros comuns
""")

async def github(update, context):
    await simple_command(update, context, "dev", "github", """
Explique como configurar GitHub para este projeto.

Inclua:
1. Criar repositório
2. Criar arquivos
3. Commit
4. Conectar deploy
5. Atualizar projeto
6. Cuidados para iniciante
""")

async def debug(update, context):
    tema = " ".join(context.args)
    await ai_save(update, FILES["dev"], "debug", tema, f"""
Analise e corrija este erro/código/problema:

{tema}

Responda com:
1. O que está errado
2. Por que deu erro
3. Correção exata
4. Código corrigido se possível
5. Como testar
6. Como evitar no futuro
""")

async def arquitetura(update, context):
    await simple_command(update, context, "dev", "arquitetura", """
Crie arquitetura técnica completa.

Inclua:
1. Visão geral
2. Frontend
3. Backend
4. Banco de dados
5. Autenticação
6. APIs
7. Deploy grátis
8. Segurança básica
9. Escalabilidade
10. Roadmap técnico
""")

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
    "ideia": ideia, "validar": validar, "mvp": mvp, "features": features, "saas": saas, "produto": produto, "lancamento": lancamento, "produtos": produtos,
    "site": site, "app": app_cmd, "api": api, "banco": banco, "deploy": deploy, "github": github, "debug": debug, "arquitetura": arquitetura, "devs": devs
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI DEV MODE ONLINE")
app.run_polling()
