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

MEMORY_FILE = "memory.json"

# ====================================
# MASTER PROMPT
# ====================================

MASTER_PROMPT = """
Você é StreetCore AI.

Um agente executivo, criativo e operacional.

Você atua como:
- CEO;
- estrategista;
- branding expert;
- diretor criativo;
- especialista em marketing;
- especialista em IA;
- engenheiro de automação;
- growth hacker;
- operador pessoal.

Você ajuda o usuário:
- criar negócios;
- criar marcas;
- criar conteúdo;
- automatizar tarefas;
- crescer nas redes sociais;
- desenvolver produtos digitais;
- criar sistemas inteligentes.

Você sempre responde:
- em português;
- com clareza;
- passo a passo;
- como parceiro operacional.

Use estética:
- futurista;
- premium;
- street luxury;
- cyberpunk minimalista;
- cinematográfica.
"""

# ====================================
# MEMORY
# ====================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):
        return {}

    with open(MEMORY_FILE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_memory(memory):

    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(
            memory,
            file,
            ensure_ascii=False,
            indent=2
        )

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
# IMAGE SYSTEM
# ====================================

def gerar_imagem_url(prompt):

    premium_prompt = f"""
ultra realistic cinematic image,
street luxury futuristic aesthetic,
cyberpunk executive style,
premium lighting,
8k,
luxury global brand style,
highly detailed.

{prompt}
"""

    encoded_prompt = urllib.parse.quote(
        premium_prompt
    )

    return f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&seed=77"

# ====================================
# COMMANDS
# ====================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🔥 STREETCORE AI ONLINE

AGENTE PREMIUM ATIVO

CAPACIDADES:
✅ IA avançada
✅ Branding
✅ Estratégia
✅ Memória
✅ Imagens IA
✅ Conteúdo
✅ Growth
✅ Agência criativa

COMANDOS:

/status
/memoria
/imagem
/logo
/nome
/slogan
/post
/video
"""

    await update.message.reply_text(text)

# ====================================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = """
🚀 STATUS

Sistema: ONLINE
IA: Groq
Imagem: Grátis
Memória: Ativa
Modo: Agência Premium
"""

    await update.message.reply_text(text)

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

    image_url = gerar_imagem_url(prompt)

    await update.message.reply_photo(
        photo=image_url
    )

# ====================================

async def logo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    prompt = " ".join(context.args)

    if not prompt:
        await update.message.reply_text(
            "Use:\n/logo nome da marca"
        )
        return

    logo_prompt = f"""
minimal futuristic luxury logo,
clean branding,
streetwear premium identity,
white background,
high-end fashion logo.

{prompt}
"""

    await update.message.reply_text(
        "🔥 Criando logo..."
    )

    image_url = gerar_imagem_url(
        logo_prompt
    )

    await update.message.reply_photo(
        photo=image_url
    )

# ====================================

async def nome(update: Update, context: ContextTypes.DEFAULT_TYPE):

    niche = " ".join(context.args)

    prompt = f"""
Crie 10 nomes premium,
modernos e fortes para:
{niche}

Os nomes devem parecer:
- marcas globais;
- fashion brands;
- startups bilionárias;
- marcas futuristas.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": MASTER_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

# ====================================

async def slogan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    niche = " ".join(context.args)

    prompt = f"""
Crie slogans premium,
curtos, fortes e cinematográficos
para:
{niche}
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": MASTER_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

# ====================================

async def post(update: Update, context: ContextTypes.DEFAULT_TYPE):

    niche = " ".join(context.args)

    prompt = f"""
Crie um post viral premium para Instagram.

Tema:
{niche}

Estrutura:
- headline forte;
- legenda;
- CTA;
- estilo futurista;
- branding premium.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": MASTER_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

# ====================================

async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):

    niche = " ".join(context.args)

    prompt = f"""
Crie um prompt cinematográfico
para gerar um vídeo IA viral.

Tema:
{niche}

Estilo:
- luxo futurista;
- cyberpunk premium;
- campanha global;
- vertical TikTok/Reels;
- cinematográfico.
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": MASTER_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

# ====================================
# CHAT
# ====================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_message = update.message.text

    memory = load_memory()

    auto_memory(user_message, memory)

    memory_text = json.dumps(
        memory,
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
                "content": user_message
            }
        ],
        temperature=0.8,
        max_tokens=2000
    )

    reply = completion.choices[0].message.content

    await update.message.reply_text(reply)

# ====================================
# APP
# ====================================

app = ApplicationBuilder().token(
    TELEGRAM_TOKEN
).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("memoria", memoria))

app.add_handler(CommandHandler("imagem", imagem))
app.add_handler(CommandHandler("logo", logo))
app.add_handler(CommandHandler("nome", nome))
app.add_handler(CommandHandler("slogan", slogan))
app.add_handler(CommandHandler("post", post))
app.add_handler(CommandHandler("video", video))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

print("🔥 STREETCORE AI PREMIUM ONLINE")

app.run_polling()
