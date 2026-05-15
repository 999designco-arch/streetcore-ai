import os
import json
import urllib.parse
import threading

from flask import Flask, jsonify, request, render_template_string
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters
)

from groq import Groq

# =========================================
# CONFIG
# =========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))

client = Groq(api_key=GROQ_API_KEY)

# =========================================
# FILES
# =========================================

FILES = {
    "memory": "memory.json",
    "tasks": "tasks.json",
    "items": "items.json"
}

# =========================================
# HELPERS
# =========================================

def load_json(file, default):
    if not os.path.exists(file):
        return default

    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =========================================
# MEMORY
# =========================================

def get_memory():
    mem = load_json(FILES["memory"], {})

    mem.setdefault("perfil", {})
    mem.setdefault("objetivos", [])
    mem.setdefault("preferencias", [])

    return mem

def save_memory(mem):
    save_json(FILES["memory"], mem)

# =========================================
# AGENTS
# =========================================

AGENTS = {

    "ceo":
    """
    Você é um CEO bilionário especialista em:
    - crescimento
    - monetização
    - SaaS
    - negócios digitais
    - IA
    - escala
    """,

    "marketing":
    """
    Você é um especialista extremo em:
    - marketing
    - branding
    - viralização
    - conteúdo
    - copywriting
    - funis
    """,

    "dev":
    """
    Você é um engenheiro de software especialista em:
    - Python
    - IA
    - automação
    - SaaS
    - APIs
    - arquitetura
    """,

    "design":
    """
    Você é diretor criativo premium especialista em:
    - branding
    - design futurista
    - cyberpunk premium
    - cinematic
    - thumbnails
    - logos
    """,

    "automation":
    """
    Você é especialista em:
    - automações
    - produtividade
    - agentes IA
    - sistemas autônomos
    - workflows
    """
}

# =========================================
# MASTER PROMPT
# =========================================

MASTER_PROMPT = """
Você é StreetCore OS.

Um sistema operacional IA avançado.

Responda sempre:
- em português;
- de forma prática;
- passo a passo;
- como se estivesse fazendo pelo usuário.

Você possui:
- inteligência de CEO;
- engenharia de IA;
- branding premium;
- automação;
- growth hacking;
- criação de conteúdo;
- direção criativa;
- produtividade extrema.

Use apenas ferramentas gratuitas ou plano grátis.

Seja extremamente estratégico.
"""

# =========================================
# IA
# =========================================

def ask_ai(prompt, role="ceo"):

    memory = json.dumps(get_memory(), ensure_ascii=False)

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",

        messages=[

            {
                "role":"system",
                "content":
                MASTER_PROMPT +
                "\n\n" +
                AGENTS.get(role, "")
            },

            {
                "role":"system",
                "content":
                f"MEMÓRIA:\n{memory}"
            },

            {
                "role":"user",
                "content":prompt
            }
        ],

        temperature=0.8,
        max_tokens=3000
    )

    return response.choices[0].message.content

# =========================================
# IMAGE AI
# =========================================

def image_url(prompt):

    encoded = urllib.parse.quote(prompt)

    return f"https://image.pollinations.ai/prompt/{encoded}"

# =========================================
# TELEGRAM
# =========================================

async def start(update, context):

    await update.message.reply_text(
        "🔥 StreetCore OS online.\n\nDigite /menu"
    )

async def menu(update, context):

    await update.message.reply_text(
"""
🔥 STREETCORE OS

/completo ideia
/ceo ideia
/marketing ideia
/dev ideia
/design ideia
/auto ideia

/imagem tema
/logo marca
/thumb tema

/tarefa texto
/tarefas

/memoria
/status
"""
)

# =========================================
# STATUS
# =========================================

async def status(update, context):

    tasks = load_json(FILES["tasks"], [])
    items = load_json(FILES["items"], [])

    await update.message.reply_text(
f"""
🔥 STREETCORE STATUS

Tarefas: {len(tasks)}
Itens: {len(items)}

Sistema:
✅ Online
✅ IA ativa
✅ Dashboard ativo
✅ Multi Agents ativo
"""
)

# =========================================
# MEMORY
# =========================================

async def memoria(update, context):

    mem = get_memory()

    text = json.dumps(mem, ensure_ascii=False, indent=2)

    await update.message.reply_text(text[:4000])

# =========================================
# TASKS
# =========================================

async def tarefa(update, context):

    text = " ".join(context.args)

    tasks = load_json(FILES["tasks"], [])

    tasks.append({
        "task": text
    })

    save_json(FILES["tasks"], tasks)

    await update.message.reply_text(
        "✅ tarefa salva"
    )

async def tarefas(update, context):

    tasks = load_json(FILES["tasks"], [])

    if not tasks:

        await update.message.reply_text(
            "Nenhuma tarefa."
        )

        return

    text = "🧠 TAREFAS\n\n"

    for i, task in enumerate(tasks):

        text += f"{i+1}. {task['task']}\n"

    await update.message.reply_text(text)

# =========================================
# GENERIC AGENT
# =========================================

async def generic_agent(update, context, role):

    prompt = " ".join(context.args)

    if not prompt:

        await update.message.reply_text(
            "Digite algo."
        )

        return

    response = ask_ai(prompt, role)

    items = load_json(FILES["items"], [])

    items.append({
        "agent": role,
        "prompt": prompt,
        "response": response
    })

    save_json(FILES["items"], items)

    for i in range(0, len(response), 3900):

        await update.message.reply_text(
            response[i:i+3900]
        )

# =========================================
# MULTI AGENT
# =========================================

async def completo(update, context):

    prompt = " ".join(context.args)

    if not prompt:

        await update.message.reply_text(
            "Digite algo."
        )

        return

    final = ""

    for role in AGENTS.keys():

        result = ask_ai(prompt, role)

        final += f"\n\n### {role.upper()}\n\n{result}"

    items = load_json(FILES["items"], [])

    items.append({
        "agent":"multi",
        "prompt":prompt,
        "response":final
    })

    save_json(FILES["items"], items)

    for i in range(0, len(final), 3900):

        await update.message.reply_text(
            final[i:i+3900]
        )

# =========================================
# IMAGE COMMANDS
# =========================================

async def imagem(update, context):

    prompt = " ".join(context.args)

    await update.message.reply_photo(
        photo=image_url(
            f"""
            cinematic futuristic image,
            ultra realistic,
            cyberpunk premium,
            8k,
            {prompt}
            """
        )
    )

async def logo(update, context):

    prompt = " ".join(context.args)

    await update.message.reply_photo(
        photo=image_url(
            f"""
            minimal luxury logo,
            futuristic branding,
            clean vector,
            white background,
            premium brand,
            {prompt}
            """
        )
    )

async def thumb(update, context):

    prompt = " ".join(context.args)

    await update.message.reply_photo(
        photo=image_url(
            f"""
            youtube thumbnail,
            cinematic,
            high ctr,
            viral,
            futuristic,
            dramatic,
            {prompt}
            """
        )
    )

# =========================================
# COMMANDS
# =========================================

async def ceo(update, context):
    await generic_agent(update, context, "ceo")

async def marketing(update, context):
    await generic_agent(update, context, "marketing")

async def dev(update, context):
    await generic_agent(update, context, "dev")

async def design(update, context):
    await generic_agent(update, context, "design")

async def auto(update, context):
    await generic_agent(update, context, "automation")

# =========================================
# NORMAL CHAT
# =========================================

async def normal_chat(update, context):

    text = update.message.text

    response = ask_ai(text)

    for i in range(0, len(response), 3900):

        await update.message.reply_text(
            response[i:i+3900]
        )

# =========================================
# FLASK WEB
# =========================================

web = Flask(__name__)

HTML = """
<!doctype html>

<html>

<head>

<title>StreetCore OS</title>

<style>

*{
margin:0;
padding:0;
box-sizing:border-box;
font-family:Arial;
}

body{
background:#050510;
color:white;
display:flex;
height:100vh;
overflow:hidden;
}

.sidebar{
width:260px;
background:#0d0d18;
padding:20px;
border-right:1px solid #222;
display:flex;
flex-direction:column;
gap:12px;
}

.logo{
font-size:28px;
font-weight:bold;
color:#9333ea;
margin-bottom:10px;
}

.btn{
padding:14px;
background:#151525;
border:none;
border-radius:12px;
color:white;
text-align:left;
cursor:pointer;
}

.btn:hover{
background:#222240;
}

.main{
flex:1;
display:flex;
flex-direction:column;
}

.top{
height:70px;
background:#0d0d18;
display:flex;
align-items:center;
padding:0 20px;
border-bottom:1px solid #222;
font-size:20px;
font-weight:bold;
}

.chat{
flex:1;
overflow:auto;
padding:30px;
display:flex;
flex-direction:column;
gap:20px;
}

.msg{
padding:18px;
border-radius:18px;
max-width:850px;
line-height:1.6;
white-space:pre-wrap;
}

.user{
background:#1f1f35;
align-self:flex-end;
}

.ai{
background:#111827;
align-self:flex-start;
border:1px solid #333;
}

.input-area{
padding:20px;
background:#0d0d18;
display:flex;
gap:15px;
border-top:1px solid #222;
}

input{
flex:1;
padding:18px;
border:none;
border-radius:14px;
background:#151525;
color:white;
font-size:16px;
}

button{
padding:18px 24px;
border:none;
border-radius:14px;
background:#9333ea;
color:white;
cursor:pointer;
font-weight:bold;
}

button:hover{
background:#7e22ce;
}

.status{
margin-top:auto;
font-size:13px;
opacity:.7;
}

</style>

</head>

<body>

<div class="sidebar">

<div class="logo">
🔥 StreetCore OS
</div>

<button class="btn">
Dashboard
</button>

<button class="btn">
Agentes IA
</button>

<button class="btn">
Automação
</button>

<button class="btn">
Marketing
</button>

<button class="btn">
Branding
</button>

<button class="btn">
Conteúdo
</button>

<button class="btn">
Vídeos
</button>

<button class="btn">
Imagens
</button>

<div class="status">
ONLINE • GOD MODE
</div>

</div>

<div class="main">

<div class="top">
StreetCore AI Operating System
</div>

<div class="chat" id="chat">

<div class="msg ai">
🔥 StreetCore OS online.

Sistema operacional IA iniciado.

Pronto para:
- criar empresas;
- automatizar tarefas;
- criar conteúdo;
- criar imagens;
- criar estratégias;
- gerar branding;
- gerar negócios.
</div>

</div>

<div class="input-area">

<input
id="prompt"
placeholder="Digite sua ideia..."
>

<button onclick="sendMessage()">
Enviar
</button>

</div>

</div>

<script>

async function sendMessage(){

const input =
document.getElementById("prompt");

const text = input.value;

if(!text) return;

const chat =
document.getElementById("chat");

chat.innerHTML += `
<div class="msg user">${text}</div>
`;

input.value = "";

const response =
await fetch("/ask",{

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({
prompt:text
})

});

const data =
await response.json();

chat.innerHTML += `
<div class="msg ai">${data.response}</div>
`;

chat.scrollTop =
chat.scrollHeight;

}

</script>

</body>

</html>
"""

@web.route("/")
def home():

    return render_template_string(HTML)

@web.route("/ask", methods=["POST"])
def ask_web():

    data = request.get_json()

    prompt = data.get("prompt", "")

    response = ask_ai(prompt)

    return jsonify({
        "response":response
    })

@web.route("/api/status")
def api_status():

    return jsonify({

        "memory":
        get_memory(),

        "tasks":
        load_json(
            FILES["tasks"],
            []
        ),

        "items":
        load_json(
            FILES["items"],
            []
        )
    })

# =========================================
# RUN WEB
# =========================================

def run_web():

    web.run(
        host="0.0.0.0",
        port=PORT
    )

# =========================================
# TELEGRAM APP
# =========================================

app = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .build()
)

# =========================================
# HANDLERS
# =========================================

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("memoria", memoria))

app.add_handler(CommandHandler("tarefa", tarefa))
app.add_handler(CommandHandler("tarefas", tarefas))

app.add_handler(CommandHandler("imagem", imagem))
app.add_handler(CommandHandler("logo", logo))
app.add_handler(CommandHandler("thumb", thumb))

app.add_handler(CommandHandler("ceo", ceo))
app.add_handler(CommandHandler("marketing", marketing))
app.add_handler(CommandHandler("dev", dev))
app.add_handler(CommandHandler("design", design))
app.add_handler(CommandHandler("auto", auto))

app.add_handler(CommandHandler("completo", completo))

app.add_handler(
    MessageHandler(
        filters.TEXT &
        ~filters.COMMAND,
        normal_chat
    )
)

# =========================================
# START
# =========================================

threading.Thread(
    target=run_web,
    daemon=True
).start()

print("🔥 STREETCORE OS ONLINE")

app.run_polling()