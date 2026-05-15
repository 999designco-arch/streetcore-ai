import os
import json
import sqlite3
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
from pypdf import PdfReader

# =========================================
# CONFIG
# =========================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))

client = Groq(api_key=GROQ_API_KEY)

# =========================================
# DATABASE
# =========================================

conn = sqlite3.connect(
    "streetcore.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS memory(
id INTEGER PRIMARY KEY AUTOINCREMENT,
content TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY AUTOINCREMENT,
task TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
agent TEXT,
prompt TEXT,
response TEXT
)
""")

conn.commit()

# =========================================
# MASTER PROMPT
# =========================================

MASTER_PROMPT = """
Você é StreetCore OS.

Um sistema operacional IA avançado.

Você possui:
- inteligência de CEO;
- branding premium;
- automação;
- programação;
- growth hacking;
- criação de conteúdo;
- engenharia de IA;
- marketing;
- direção criativa.

Responda:
- em português;
- de forma prática;
- passo a passo;
- como se estivesse fazendo pelo usuário.

Use ferramentas gratuitas.
"""

# =========================================
# AGENTS
# =========================================

AGENTS = {

"ceo":
"""
Você é um CEO especialista em:
- negócios digitais
- monetização
- SaaS
- crescimento
- IA
- escala
""",

"marketing":
"""
Você é especialista em:
- branding
- marketing
- conteúdo
- viralização
- copywriting
""",

"dev":
"""
Você é engenheiro especialista em:
- Python
- APIs
- IA
- automação
- SaaS
""",

"design":
"""
Você é diretor criativo premium especialista em:
- cyberpunk premium
- branding
- thumbnails
- logos
- cinematic
""",

"automation":
"""
Você é especialista em:
- agentes IA
- automações
- produtividade
- workflows
"""
}

# =========================================
# AI
# =========================================

def ask_ai(prompt, role="ceo"):

    memories = cursor.execute(
        "SELECT content FROM memory ORDER BY id DESC LIMIT 20"
    ).fetchall()

    memory_text = "\n".join(
        [m[0] for m in memories]
    )

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
                f"MEMÓRIA:\n{memory_text}"
            },

            {
                "role":"user",
                "content":prompt
            }
        ],

        temperature=0.8,
        max_tokens=3000
    )

    result = response.choices[0].message.content

    cursor.execute(
        "INSERT INTO history(agent,prompt,response) VALUES(?,?,?)",
        (role,prompt,result)
    )

    conn.commit()

    return result

# =========================================
# IMAGE
# =========================================

def image_url(prompt):

    encoded = urllib.parse.quote(prompt)

    return f"https://image.pollinations.ai/prompt/{encoded}"

# =========================================
# TELEGRAM
# =========================================

async def start(update, context):

    await update.message.reply_text(
"""
🔥 StreetCore OS V3 online.

Digite:
/menu
"""
)

async def menu(update, context):

    await update.message.reply_text(
"""
🔥 STREETCORE OS V3

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

/salvar memoria
/memorias

/historico

/status
"""
)

# =========================================
# STATUS
# =========================================

async def status(update, context):

    task_count = cursor.execute(
        "SELECT COUNT(*) FROM tasks"
    ).fetchone()[0]

    history_count = cursor.execute(
        "SELECT COUNT(*) FROM history"
    ).fetchone()[0]

    mem_count = cursor.execute(
        "SELECT COUNT(*) FROM memory"
    ).fetchone()[0]

    await update.message.reply_text(
f"""
🔥 STREETCORE STATUS

Memórias: {mem_count}
Tarefas: {task_count}
Histórico: {history_count}

Sistema:
✅ Online
✅ Dashboard
✅ Multi Agents
✅ Banco SQLite
✅ IA ativa
"""
)

# =========================================
# TASKS
# =========================================

async def tarefa(update, context):

    text = " ".join(context.args)

    cursor.execute(
        "INSERT INTO tasks(task) VALUES(?)",
        (text,)
    )

    conn.commit()

    await update.message.reply_text(
        "✅ tarefa salva"
    )

async def tarefas(update, context):

    tasks = cursor.execute(
        "SELECT * FROM tasks ORDER BY id DESC LIMIT 30"
    ).fetchall()

    if not tasks:

        await update.message.reply_text(
            "Nenhuma tarefa."
        )

        return

    text = "🧠 TAREFAS\n\n"

    for task in tasks:

        text += f"{task[0]}. {task[1]}\n"

    await update.message.reply_text(text)

# =========================================
# MEMORY
# =========================================

async def salvar(update, context):

    text = " ".join(context.args)

    cursor.execute(
        "INSERT INTO memory(content) VALUES(?)",
        (text,)
    )

    conn.commit()

    await update.message.reply_text(
        "🧠 memória salva"
    )

async def memorias(update, context):

    memories = cursor.execute(
        "SELECT * FROM memory ORDER BY id DESC LIMIT 20"
    ).fetchall()

    text = "🧠 MEMÓRIAS\n\n"

    for mem in memories:

        text += f"{mem[0]}. {mem[1]}\n\n"

    await update.message.reply_text(
        text[:4000]
    )

# =========================================
# HISTORY
# =========================================

async def historico(update, context):

    data = cursor.execute(
        "SELECT * FROM history ORDER BY id DESC LIMIT 10"
    ).fetchall()

    text = "📚 HISTÓRICO\n\n"

    for item in data:

        text += f"""
ID: {item[0]}
AGENTE: {item[1]}
PROMPT: {item[2][:80]}

-------------------
"""

    await update.message.reply_text(
        text[:4000]
    )

# =========================================
# AGENT
# =========================================

async def generic_agent(update, context, role):

    prompt = " ".join(context.args)

    if not prompt:

        await update.message.reply_text(
            "Digite algo."
        )

        return

    response = ask_ai(prompt, role)

    for i in range(0, len(response), 3900):

        await update.message.reply_text(
            response[i:i+3900]
        )

# =========================================
# MULTI AGENT
# =========================================

async def completo(update, context):

    prompt = " ".join(context.args)

    final = ""

    for role in AGENTS.keys():

        result = ask_ai(prompt, role)

        final += f"\n\n### {role.upper()}\n\n{result}"

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
            futuristic luxury logo,
            minimal,
            clean vector,
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
# WEB
# =========================================

web = Flask(__name__)

HTML = """
<!doctype html>

<html>

<head>

<title>StreetCore OS</title>

<style>

body{
background:#050510;
color:white;
font-family:Arial;
margin:0;
display:flex;
height:100vh;
}

.sidebar{
width:260px;
background:#0d0d18;
padding:20px;
border-right:1px solid #222;
}

.logo{
font-size:28px;
font-weight:bold;
color:#9333ea;
margin-bottom:20px;
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
}

.chat{
flex:1;
padding:30px;
overflow:auto;
display:flex;
flex-direction:column;
gap:20px;
}

.msg{
padding:18px;
border-radius:18px;
max-width:850px;
white-space:pre-wrap;
line-height:1.6;
}

.user{
background:#1f1f35;
align-self:flex-end;
}

.ai{
background:#111827;
border:1px solid #333;
}

.input-area{
padding:20px;
display:flex;
gap:15px;
background:#0d0d18;
}

input{
flex:1;
padding:18px;
border:none;
border-radius:14px;
background:#151525;
color:white;
}

button{
padding:18px 24px;
background:#9333ea;
border:none;
border-radius:14px;
color:white;
cursor:pointer;
}

</style>

</head>

<body>

<div class="sidebar">

<div class="logo">
🔥 StreetCore OS
</div>

<p>ONLINE • GOD MODE</p>

</div>

<div class="main">

<div class="top">
StreetCore AI Operating System
</div>

<div class="chat" id="chat">

<div class="msg ai">
🔥 StreetCore OS V3 online.

Sistema operacional IA iniciado.
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

const text =
input.value;

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

    prompt = data.get("prompt","")

    response = ask_ai(prompt)

    return jsonify({
        "response":response
    })

@web.route("/api/status")
def api_status():

    return jsonify({

        "tasks":
        cursor.execute(
            "SELECT COUNT(*) FROM tasks"
        ).fetchone()[0],

        "history":
        cursor.execute(
            "SELECT COUNT(*) FROM history"
        ).fetchone()[0],

        "memory":
        cursor.execute(
            "SELECT COUNT(*) FROM memory"
        ).fetchone()[0]
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
# TELEGRAM
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

app.add_handler(CommandHandler("tarefa", tarefa))
app.add_handler(CommandHandler("tarefas", tarefas))

app.add_handler(CommandHandler("salvar", salvar))
app.add_handler(CommandHandler("memorias", memorias))

app.add_handler(CommandHandler("historico", historico))

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

print("🔥 STREETCORE OS V3 ONLINE")

app.run_polling()