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
    "dev": "dev.json",
    "docs": "docs.json"
}

MASTER_PROMPT = """
Você é StreetCore AI.
Responda sempre em português.
Use apenas ferramentas gratuitas ou plano grátis.
Aja como CEO, COO, diretor criativo, estrategista, copywriter, vendedor, social media,
growth hacker, arquiteto de SaaS, programador full-stack, engenheiro de automação,
consultor de negócios e operador técnico.
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
    encoded = urllib.parse.quote(
        f"ultra realistic cinematic image, street luxury futuristic aesthetic, cyberpunk executive style, premium lighting, 8k, highly detailed. {prompt}"
    )
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

NOVO MODO: ARQUIVOS / DOCUMENTOS

Comandos:
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
/site /app /api /banco /deploy /github /debug /arquitetura /devs

DOCUMENTOS:
/doc
/proposta
/contrato
/briefing
/plano
/email
/arquivos
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
Arquivos/Docs: {len(load_json(FILES["docs"], []))}

Modo: CEO + AGÊNCIA + SAAS + DEV + DOCUMENTOS
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
    await ai_save(update, FILES["projects"], "projeto", tema, f"Crie estrutura inicial de projeto para: {tema}")

async def projetos(update, context): await listar(update, FILES["projects"], "📁 PROJETOS")

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

async def simple_command(update, context, file_key, tipo, prompt_base):
    tema = " ".join(context.args)
    await ai_save(update, FILES[file_key], tipo, tema, f"{prompt_base}\n\nTema:\n{tema}")

async def roadmap(update, context): await simple_command(update, context, "roadmaps", "roadmap", "Crie roadmap executivo completo com estratégia, execução, monetização, ferramentas grátis, plano de 7 dias e plano de 30 dias.")
async def roadmaps(update, context): await listar(update, FILES["roadmaps"], "🗺 ROADMAPS")
async def hoje(update, context):
    resposta = ask_ai(f"Crie plano executivo para hoje com base nestas tarefas:\n{load_json(FILES['tasks'], [])}", load_memory())
    await send_long(update, resposta)
async def semana(update, context):
    resposta = ask_ai(f"Crie plano semanal executivo com base nestas tarefas:\n{load_json(FILES['tasks'], [])}", load_memory())
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
    await update.message.reply_text("🔥 Criando logo...")
    await update.message.reply_photo(photo=gerar_imagem_url(f"minimal futuristic luxury logo, premium streetwear branding, white background, {tema}"))

async def automacao(update, context): await simple_command(update, context, "automations", "automacao", "Crie automação gratuita com ferramentas grátis, passo a passo, fluxo, execução e erros comuns.")
async def fluxo(update, context): await simple_command(update, context, "automations", "fluxo", "Crie fluxo operacional gratuito no formato INÍCIO → ETAPA → FINAL.")
async def script(update, context): await simple_command(update, context, "automations", "script", "Crie script Python gratuito com código completo e como rodar.")
async def checklist(update, context): await simple_command(update, context, "automations", "checklist", "Crie checklist operacional completo.")
async def automacoes(update, context): await listar(update, FILES["automations"], "⚙️ AUTOMAÇÕES")

async def conteudo(update, context): await simple_command(update, context, "content", "conteudo", "Crie conteúdo viral premium para Instagram/TikTok com gancho, texto, legenda, CTA, hashtags e ideia visual.")
async def carrossel(update, context): await simple_command(update, context, "content", "carrossel", "Crie carrossel viral para Instagram, slide por slide, com legenda e direção visual.")
async def reels(update, context): await simple_command(update, context, "content", "reels", "Crie roteiro de Reels/TikTok viral com hook, cenas, narração, texto na tela e CTA.")
async def calendario(update, context): await simple_command(update, context, "content", "calendario", "Crie calendário de conteúdo de 30 dias com tema, formato, gancho, CTA e ferramenta grátis por dia.")
async def campanha(update, context): await simple_command(update, context, "content", "campanha", "Crie campanha premium completa com conceito, público, oferta, posts, reels, funil grátis e plano de 7 dias.")
async def conteudos(update, context): await listar(update, FILES["content"], "📲 CONTEÚDOS")

async def oferta(update, context): await simple_command(update, context, "sales", "oferta", "Crie oferta irresistível com público, dor, promessa, mecanismo único, bônus, urgência ética, preço sugerido e oferta final.")
async def copy(update, context): await simple_command(update, context, "sales", "copy", "Crie copy de vendas premium com headline, subheadline, problema, solução, benefícios, prova, oferta e CTA.")
async def funil(update, context): await simple_command(update, context, "sales", "funil", "Crie funil de vendas grátis com tráfego grátis, isca, captura, nutrição, oferta, follow-up, automação e plano de 7 dias.")
async def landing(update, context): await simple_command(update, context, "sales", "landing", "Crie landing page completa com hero, headline, benefícios, oferta, FAQ, CTA e HTML simples.")
async def whatsapp(update, context): await simple_command(update, context, "sales", "whatsapp", "Crie sequência de WhatsApp para vender com abordagem, diagnóstico, solução, objeções, fechamento e follow-ups.")
async def vendas(update, context): await listar(update, FILES["sales"], "💰 VENDAS")

async def branding(update, context): await simple_command(update, context, "branding", "branding", "Crie estratégia completa de branding premium com essência, posicionamento, público, personalidade, promessa, diferencial, arquétipo, visual, tom de voz e próximos passos.")
async def paleta(update, context): await simple_command(update, context, "branding", "paleta", "Crie paleta de cores premium com HEX, psicologia das cores e aplicação.")
async def tomvoz(update, context): await simple_command(update, context, "branding", "tomvoz", "Crie tom de voz completo com palavras, estilo, exemplos, legenda e mensagens.")
async def manifesto(update, context): await simple_command(update, context, "branding", "manifesto", "Crie manifesto cinematográfico, forte e premium.")
async def brandbook(update, context): await simple_command(update, context, "branding", "brandbook", "Crie mini brand book completo com missão, visão, valores, público, posicionamento, paleta, tipografia gratuita, tom de voz e regras.")
async def identidade(update, context): await simple_command(update, context, "branding", "identidade", "Crie identidade visual completa com logo ideal, símbolos, paleta, tipografia gratuita, fotos, posts, embalagem e prompts.")
async def brandings(update, context): await listar(update, FILES["branding"], "🎯 BRANDINGS")

async def ideia(update, context): await simple_command(update, context, "products", "ideia", "Crie 10 ideias de produto digital/SaaS com nome, problema, público, MVP grátis, monetização, dificuldade e potencial.")
async def validar(update, context): await simple_command(update, context, "products", "validar", "Crie plano de validação gratuito com hipótese, público, perguntas, onde achar pessoas, landing, oferta teste, métricas e plano de 7 dias.")
async def mvp(update, context): await simple_command(update, context, "products", "mvp", "Crie MVP gratuito com versão simples, features essenciais, stack grátis, passo a passo, tela inicial, fluxo e teste.")
async def features(update, context): await simple_command(update, context, "products", "features", "Crie lista de features dividida em essenciais, diferenciais, futuras, automáveis, premium e ordem de desenvolvimento.")
async def saas(update, context): await simple_command(update, context, "products", "saas", "Crie arquitetura completa de SaaS gratuito/plano grátis com nome, proposta, público, features, stack, banco, login, dashboard, monetização e roadmap.")
async def produto(update, context): await simple_command(update, context, "products", "produto", "Crie produto digital completo com nome, promessa, público, entregável, módulos, bônus, preço, página de venda, funil e lançamento.")
async def lancamento(update, context): await simple_command(update, context, "products", "lancamento", "Crie plano de lançamento gratuito com pré-lançamento, conteúdo, oferta, posts, reels, WhatsApp, página, lançamento e pós.")
async def produtos(update, context): await listar(update, FILES["products"], "🧩 PRODUTOS / SAAS")

async def site(update, context): await simple_command(update, context, "dev", "site", "Crie site completo gratuito com estrutura, copy, design, HTML + CSS completo, teste e publicação grátis no GitHub Pages.")
async def app_cmd(update, context): await simple_command(update, context, "dev", "app", "Crie app simples gratuito com funcionalidades, telas, fluxo, stack grátis, código inicial e como rodar.")
async def api(update, context): await simple_command(update, context, "dev", "api", "Crie API gratuita com endpoints, dados, código FastAPI, requirements.txt, como rodar e publicar grátis.")
async def banco(update, context): await simple_command(update, context, "dev", "banco", "Crie estrutura de banco de dados grátis com entidades, tabelas, campos, relacionamentos, SQL e Supabase grátis.")
async def deploy(update, context): await simple_command(update, context, "dev", "deploy", "Crie plano de deploy gratuito com hospedagem grátis, passo a passo, variáveis, GitHub, logs e correções.")
async def github(update, context): await simple_command(update, context, "dev", "github", "Explique como configurar GitHub para este projeto com repositório, arquivos, commit, deploy e cuidados.")
async def debug(update, context): await simple_command(update, context, "dev", "debug", "Analise e corrija erro/código/problema. Explique erro, causa, correção exata, código corrigido e teste.")
async def arquitetura(update, context): await simple_command(update, context, "dev", "arquitetura", "Crie arquitetura técnica completa com frontend, backend, banco, auth, APIs, deploy grátis, segurança e roadmap.")
async def devs(update, context): await listar(update, FILES["dev"], "💻 DEV / PROGRAMAÇÃO")

async def doc(update, context):
    await simple_command(update, context, "docs", "doc", """
Crie um documento profissional completo.

Inclua:
1. Título
2. Objetivo
3. Contexto
4. Estrutura organizada
5. Conteúdo principal
6. Conclusão
7. Próximos passos
8. Versão pronta para copiar
""")

async def proposta(update, context):
    await simple_command(update, context, "docs", "proposta", """
Crie uma proposta comercial profissional.

Inclua:
1. Título
2. Apresentação
3. Problema do cliente
4. Solução proposta
5. Entregáveis
6. Cronograma
7. Investimento sugerido
8. Condições
9. Próximos passos
10. Texto pronto para enviar
""")

async def contrato(update, context):
    await simple_command(update, context, "docs", "contrato", """
Crie um modelo simples de contrato.

Importante:
- informe que é um modelo inicial e não substitui advogado.
Inclua:
1. Partes
2. Objeto
3. Entregáveis
4. Prazo
5. Pagamento
6. Responsabilidades
7. Cancelamento
8. Confidencialidade
9. Assinaturas
""")

async def briefing(update, context):
    await simple_command(update, context, "docs", "briefing", """
Crie um briefing profissional.

Inclua:
1. Objetivo
2. Público-alvo
3. Problema
4. Referências
5. Estilo visual
6. Tom de voz
7. Entregáveis
8. Prazos
9. Perguntas importantes
10. Checklist final
""")

async def plano(update, context):
    await simple_command(update, context, "docs", "plano", """
Crie um plano estratégico completo.

Inclua:
1. Objetivo principal
2. Diagnóstico
3. Estratégia
4. Etapas
5. Cronograma
6. Recursos gratuitos
7. Riscos
8. Métricas
9. Próximo passo imediato
""")

async def email(update, context):
    await simple_command(update, context, "docs", "email", """
Crie um e-mail profissional.

Inclua:
1. Assunto
2. Saudação
3. Mensagem principal
4. CTA
5. Encerramento
6. Versão curta
7. Versão mais persuasiva
""")

async def arquivos(update, context):
    await listar(update, FILES["docs"], "📄 ARQUIVOS / DOCUMENTOS")

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
    "site": site, "app": app_cmd, "api": api, "banco": banco, "deploy": deploy, "github": github, "debug": debug, "arquitetura": arquitetura, "devs": devs,
    "doc": doc, "proposta": proposta, "contrato": contrato, "briefing": briefing, "plano": plano, "email": email, "arquivos": arquivos
}

for name, func in commands.items():
    app.add_handler(CommandHandler(name, func))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🔥 STREETCORE AI DOCUMENT MODE ONLINE")
app.run_polling()
