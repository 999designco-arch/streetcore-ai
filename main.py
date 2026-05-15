import os, sqlite3, urllib.parse, threading, math, json, secrets, csv, io
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string, redirect, session, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from groq import Groq
from pypdf import PdfReader

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
PORT = int(os.getenv("PORT", 8080))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "streetcore123")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

client = Groq(api_key=GROQ_API_KEY)

conn = sqlite3.connect("streetcore_v8.db", check_same_thread=False)
cursor = conn.cursor()

TABLES = [

"""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
email TEXT UNIQUE,
password TEXT,
role TEXT,
plan TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS memory(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
content TEXT,
vector TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS tasks(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
task TEXT,
status TEXT,
priority TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS history(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
agent TEXT,
prompt TEXT,
response TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS files(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
filename TEXT,
content TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS posts(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
platform TEXT,
theme TEXT,
content TEXT,
status TEXT,
scheduled_date TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS videos(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
theme TEXT,
script TEXT,
status TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS workflows(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
name TEXT,
steps TEXT,
status TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS approvals(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
action TEXT,
status TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS gallery(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
type TEXT,
prompt TEXT,
url TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS analytics(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
event TEXT,
data TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS api_keys(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
token TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS leads(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
name TEXT,
email TEXT,
phone TEXT,
stage TEXT,
notes TEXT,
created_at TEXT
)""",

"""CREATE TABLE IF NOT EXISTS content_calendar(
id INTEGER PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
title TEXT,
platform TEXT,
publish_date TEXT,
status TEXT,
created_at TEXT
)"""

]

for t in TABLES:
    cursor.execute(t)

conn.commit()

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def uid():
    return session.get("user_id", 1)

def ensure_admin():

    row = cursor.execute(
        "SELECT id FROM users WHERE email=?",
        ("admin@streetcore.ai",)
    ).fetchone()

    if not row:

        cursor.execute(
            """
            INSERT INTO users(
            name,email,password,role,plan,created_at
            ) VALUES(?,?,?,?,?,?)
            """,
            (
                "Admin",
                "admin@streetcore.ai",
                generate_password_hash(ADMIN_PASSWORD),
                "admin",
                "god",
                now()
            )
        )

        conn.commit()

ensure_admin()

MASTER_PROMPT = """
Você é StreetCore OS V8.
Sistema operacional empresarial IA.
Atue como:
CEO,
CMO,
CTO,
Diretor Criativo,
Automação,
Growth,
SaaS Architect,
Copywriter,
Operador IA.

Use ferramentas gratuitas.
Explique passo a passo.
Pense como empresa multimilionária.
"""

AGENTS = {
    "ceo":"CEO estratégico",
    "marketing":"Especialista em marketing",
    "dev":"Arquiteto SaaS",
    "design":"Diretor criativo premium",
    "video":"Especialista em vídeos virais",
    "automation":"Engenheiro de automação",
    "sales":"Especialista em vendas",
    "finance":"Especialista financeiro",
    "ops":"Diretor operacional"
}

def log_event(event, data="", user_id=None):

    cursor.execute(
        """
        INSERT INTO analytics(
        user_id,event,data,created_at
        ) VALUES(?,?,?,?)
        """,
        (
            user_id or uid(),
            event,
            data,
            now()
        )
    )

    conn.commit()

def text_vector(text, size=128):

    vec = [0.0] * size

    for w in text.lower().split():
        vec[hash(w) % size] += 1.0

    norm = math.sqrt(sum(x*x for x in vec)) or 1

    return [x / norm for x in vec]

def cosine(a, b):
    return sum(x*y for x, y in zip(a, b))

def save_memory(content, user_id=None):

    user_id = user_id or uid()

    cursor.execute(
        """
        INSERT INTO memory(
        user_id,content,vector,created_at
        ) VALUES(?,?,?,?)
        """,
        (
            user_id,
            content,
            json.dumps(text_vector(content)),
            now()
        )
    )

    conn.commit()

def vector_search(query, user_id=None, limit=6):

    user_id = user_id or uid()

    qv = text_vector(query)

    rows = cursor.execute(
        """
        SELECT content,vector
        FROM memory
        WHERE user_id=?
        """,
        (user_id,)
    ).fetchall()

    scored = []

    for content, v in rows:

        try:
            scored.append(
                (
                    cosine(qv, json.loads(v)),
                    content
                )
            )
        except:
            pass

    scored.sort(reverse=True)

    return [x[1] for x in scored[:limit]]

def ask_ai(prompt, role="ceo", user_id=None):

    user_id = user_id or uid()

    memories = "\n".join(
        vector_search(prompt, user_id)
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role":"system",
                "content":MASTER_PROMPT
            },
            {
                "role":"system",
                "content":AGENTS.get(role, "")
            },
            {
                "role":"system",
                "content":"MEMÓRIA:\n" + memories
            },
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0.8,
        max_tokens=3500
    )

    result = response.choices[0].message.content

    cursor.execute(
        """
        INSERT INTO history(
        user_id,agent,prompt,response,created_at
        ) VALUES(?,?,?,?,?)
        """,
        (
            user_id,
            role,
            prompt,
            result,
            now()
        )
    )

    conn.commit()

    log_event("ai_response", role, user_id)

    return result

def image_url(prompt):

    return (
        "https://image.pollinations.ai/prompt/"
        + urllib.parse.quote(prompt)
    )

def count_table(table):

    return cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM {table}
        WHERE user_id=?
        """,
        (uid(),)
    ).fetchone()[0]

web = Flask(__name__)

web.secret_key = (
    "streetcore-v8-"
    + secrets.token_hex(8)
)

CSS = """
<style>

*{
box-sizing:border-box;
font-family:Arial;
}

body{
margin:0;
background:#050510;
color:white;
min-height:100vh;
}

a{
text-decoration:none;
color:white;
}

.app{
display:flex;
min-height:100vh;
}

.sidebar{
width:280px;
background:#0d0d18;
padding:20px;
border-right:1px solid #222;
}

.logo{
font-size:26px;
font-weight:bold;
color:#a855f7;
margin-bottom:10px;
}

.status{
font-size:12px;
opacity:.7;
margin-bottom:20px;
}

.nav a{
display:block;
padding:14px;
background:#151525;
margin-bottom:10px;
border-radius:12px;
}

.nav a:hover{
background:#222240;
}

.main{
flex:1;
}

.top{
height:70px;
background:#0d0d18;
border-bottom:1px solid #222;
display:flex;
align-items:center;
justify-content:space-between;
padding:0 20px;
}

.content{
padding:22px;
}

.grid{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
gap:16px;
}

.card{
background:#111827;
border:1px solid #333;
border-radius:18px;
padding:18px;
}

.big{
font-size:36px;
font-weight:bold;
color:#a855f7;
}

.chat{
height:calc(100vh - 240px);
overflow:auto;
display:flex;
flex-direction:column;
gap:14px;
padding:15px;
}

.msg{
padding:15px;
border-radius:16px;
white-space:pre-wrap;
line-height:1.5;
max-width:900px;
}

.ai{
background:#111827;
border:1px solid #333;
}

.user{
background:#1f1f35;
align-self:flex-end;
}

.bottom{
padding:14px;
background:#0d0d18;
border-top:1px solid #222;
display:flex;
flex-direction:column;
gap:10px;
}

.row{
display:flex;
gap:10px;
}

input,select,textarea{
width:100%;
padding:14px;
border:0;
border-radius:12px;
background:#151525;
color:white;
}

button{
padding:14px 18px;
border:0;
border-radius:12px;
background:#9333ea;
color:white;
font-weight:bold;
cursor:pointer;
}

.upload{
background:#2563eb;
}

table{
width:100%;
border-collapse:collapse;
background:#111827;
border-radius:12px;
overflow:hidden;
}

td,th{
padding:12px;
border-bottom:1px solid #333;
text-align:left;
vertical-align:top;
}

.login{
max-width:450px;
margin:80px auto;
background:#111827;
padding:30px;
border-radius:20px;
border:1px solid #333;
}

.gallery{
display:grid;
grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:16px;
}

.gallery img{
width:100%;
border-radius:16px;
border:1px solid #333;
}

.pipeline{
display:grid;
grid-template-columns:repeat(4,1fr);
gap:14px;
}

.stage{
background:#111827;
padding:14px;
border-radius:16px;
min-height:300px;
}

.lead{
background:#1f1f35;
padding:12px;
border-radius:12px;
margin-bottom:10px;
}

@media(max-width:900px){

.app{
flex-direction:column;
}

.sidebar{
width:100%;
}

.row{
flex-direction:column;
}

.pipeline{
grid-template-columns:1fr;
}

.chat{
height:55vh;
}

}

</style>
"""

def logged():
    return session.get("user_id")

def current_user():

    if not logged():
        return None

    return cursor.execute(
        """
        SELECT id,name,email,role,plan
        FROM users
        WHERE id=?
        """,
        (session["user_id"],)
    ).fetchone()

def require_login():
    return bool(logged())

def layout(title, body):

    user = current_user()

    name = user[1] if user else "Usuário"

    return f"""
<!doctype html>
<html>
<head>
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
{CSS}
</head>
<body>

<div class="app">

<div class="sidebar">

<div class="logo">
🔥 StreetCore OS
</div>

<div class="status">
V8 • AI COMPANY SYSTEM
<br>
{name}
</div>

<div class="nav">

<a href="/">Dashboard</a>

<a href="/chat">Chat IA</a>

<a href="/command">Command Center</a>

<a href="/calendar">Calendário</a>

<a href="/crm">CRM</a>

<a href="/posts">Posts</a>

<a href="/videos">Vídeos</a>

<a href="/workflows">Workflows</a>

<a href="/memory">Memória</a>

<a href="/files">Arquivos</a>

<a href="/gallery">Galeria</a>

<a href="/analytics-page">Analytics</a>

<a href="/api-keys">API</a>

<a href="/billing">Stripe Ready</a>

<a href="/logout">Sair</a>

</div>

</div>

<div class="main">

<div class="top">

<b>{title}</b>

<span>
StreetCore OS V8
</span>

</div>

<div class="content">
{body}
</div>

</div>

</div>

</body>
</html>
"""

@web.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        try:

            cursor.execute(
                """
                INSERT INTO users(
                name,email,password,role,plan,created_at
                ) VALUES(?,?,?,?,?,?)
                """,
                (
                    request.form.get("name"),
                    request.form.get("email"),
                    generate_password_hash(
                        request.form.get("password")
                    ),
                    "user",
                    "free",
                    now()
                )
            )

            conn.commit()

            return redirect("/login")

        except:
            pass

    return f"""
<!doctype html>
<html>
<head>
<title>Cadastro</title>
{CSS}
</head>
<body>

<div class="login">

<h1>
🔥 StreetCore OS
</h1>

<p>
Criar conta
</p>

<form method="POST">

<input
name="name"
placeholder="Nome"
>

<br><br>

<input
name="email"
placeholder="Email"
>

<br><br>

<input
name="password"
type="password"
placeholder="Senha"
>

<br><br>

<button>
Cadastrar
</button>

</form>

</div>

</body>
</html>
"""

@web.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        row = cursor.execute(
            """
            SELECT id,password
            FROM users
            WHERE email=?
            """,
            (email,)
        ).fetchone()

        if row and check_password_hash(
            row[1],
            password
        ):

            session["user_id"] = row[0]

            return redirect("/")

    return f"""
<!doctype html>
<html>
<head>
<title>Login</title>
{CSS}
</head>
<body>

<div class="login">

<h1>
🔥 StreetCore OS V8
</h1>

<p>
Login SaaS
</p>

<form method="POST">

<input
name="email"
placeholder="Email"
value="admin@streetcore.ai"
>

<br><br>

<input
name="password"
type="password"
placeholder="Senha"
>

<br><br>

<button>
Entrar
</button>

</form>

<p>
Senha padrão:
streetcore123
</p>

</div>

</body>
</html>
"""

@web.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

@web.route("/")
def dashboard():

    if not require_login():
        return redirect("/login")

    cards = ""

    for t in [
        "memory",
        "tasks",
        "history",
        "files",
        "posts",
        "videos",
        "workflows",
        "approvals",
        "gallery",
        "analytics",
        "leads"
    ]:

        cards += f"""
<div class="card">
<h3>{t}</h3>
<div class="big">
{count_table(t)}
</div>
</div>
"""

    return layout(
        "Dashboard Executivo",
        f"<div class='grid'>{cards}</div>"
    )

@web.route("/chat")
def chat_page():

    if not require_login():
        return redirect("/login")

    return layout(
        "Chat IA",
        """
<div class="card">

<div class="chat" id="chat">

<div class="msg ai">
🔥 StreetCore OS V8 online.
</div>

</div>

<div class="bottom">

<div class="row">

<select id="agent">

<option value="ceo">CEO</option>
<option value="marketing">Marketing</option>
<option value="dev">Dev</option>
<option value="design">Design</option>
<option value="video">Video</option>
<option value="automation">Automation</option>
<option value="sales">Sales</option>
<option value="finance">Finance</option>
<option value="ops">Ops</option>

</select>

<input
id="prompt"
placeholder="Digite sua ideia..."
>

<button onclick="sendMessage()">
Enviar
</button>

</div>

<div class="row">

<input type="file" id="file">

<button
class="upload"
onclick="uploadFile()"
>
Upload IA
</button>

</div>

</div>

</div>

<script>

function add(cls,text){

document.getElementById('chat').innerHTML += `
<div class="msg ${cls}">
${text}
</div>
`;

document.getElementById(
'chat'
).scrollTop = 999999;

}

async function sendMessage(){

const text =
document.getElementById(
'prompt'
).value;

const agent =
document.getElementById(
'agent'
).value;

if(!text) return;

add('user',text);

document.getElementById(
'prompt'
).value = '';

const r =
await fetch('/ask',{

method:'POST',

headers:{
'Content-Type':'application/json'
},

body:JSON.stringify({
prompt:text,
agent:agent
})

});

const d =
await r.json();

add('ai',d.response);

}

async function uploadFile(){

const f =
document.getElementById(
'file'
).files[0];

if(!f){

alert('Escolha um arquivo');

return;

}

const fd =
new FormData();

fd.append('file',f);

const r =
await fetch('/upload',{

method:'POST',
body:fd

});

const d =
await r.json();

add('ai',d.response);

}

</script>
"""
    )

@web.route("/crm")
def crm():

    if not require_login():
        return redirect("/login")

    stages = [
        "Novo",
        "Contato",
        "Proposta",
        "Fechado"
    ]

    html = '<div class="pipeline">'

    for stage in stages:

        html += f"""
<div class="stage">

<h3>
{stage}
</h3>
"""

        leads = cursor.execute(
            """
            SELECT id,name,email
            FROM leads
            WHERE user_id=?
            AND stage=?
            ORDER BY id DESC
            """,
            (
                uid(),
                stage
            )
        ).fetchall()

        for lead in leads:

            html += f"""
<div class="lead">

<b>
{lead[1]}
</b>

<br>

{lead[2]}

</div>
"""

        html += "</div>"

    html += "</div>"

    html += """

<br><br>

<div class="card">

<h2>
Novo Lead
</h2>

<form method="POST" action="/add-lead">

<input
name="name"
placeholder="Nome"
>

<br><br>

<input
name="email"
placeholder="Email"
>

<br><br>

<input
name="phone"
placeholder="Telefone"
>

<br><br>

<textarea
name="notes"
placeholder="Notas"
></textarea>

<br><br>

<button>
Salvar Lead
</button>

</form>

</div>
"""

    return layout("CRM", html)

@web.route("/add-lead", methods=["POST"])
def add_lead():

    cursor.execute(
        """
        INSERT INTO leads(
        user_id,name,email,phone,stage,notes,created_at
        ) VALUES(?,?,?,?,?,?,?)
        """,
        (
            uid(),
            request.form.get("name"),
            request.form.get("email"),
            request.form.get("phone"),
            "Novo",
            request.form.get("notes"),
            now()
        )
    )

    conn.commit()

    return redirect("/crm")

@web.route("/calendar")
def calendar():

    if not require_login():
        return redirect("/login")

    rows = cursor.execute(
        """
        SELECT title,platform,publish_date,status
        FROM content_calendar
        WHERE user_id=?
        ORDER BY publish_date
        """,
        (uid(),)
    ).fetchall()

    html = """
<div class="card">

<h2>
Calendário de Conteúdo
</h2>

<table>

<tr>

<th>Título</th>
<th>Plataforma</th>
<th>Data</th>
<th>Status</th>

</tr>
"""

    for r in rows:

        html += f"""
<tr>
<td>{r[0]}</td>
<td>{r[1]}</td>
<td>{r[2]}</td>
<td>{r[3]}</td>
</tr>
"""

    html += """
</table>

</div>

<br><br>

<div class="card">

<h2>
Novo Conteúdo
</h2>

<form method="POST" action="/add-calendar">

<input
name="title"
placeholder="Título"
>

<br><br>

<input
name="platform"
placeholder="Instagram"
>

<br><br>

<input
name="publish_date"
placeholder="2026-01-01"
>

<br><br>

<button>
Salvar
</button>

</form>

</div>
"""

    return layout("Calendário", html)

@web.route("/add-calendar", methods=["POST"])
def add_calendar():

    cursor.execute(
        """
        INSERT INTO content_calendar(
        user_id,title,platform,publish_date,status,created_at
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            uid(),
            request.form.get("title"),
            request.form.get("platform"),
            request.form.get("publish_date"),
            "planejado",
            now()
        )
    )

    conn.commit()

    return redirect("/calendar")

@web.route("/command")
def command():

    if not require_login():
        return redirect("/login")

    return layout(
        "Command Center",
        """
<div class="grid">

<div class="card">
<h3>Criar Empresa IA</h3>
<button onclick="cmd('empresa')">
Executar
</button>
</div>

<div class="card">
<h3>Criar SaaS</h3>
<button onclick="cmd('saas')">
Executar
</button>
</div>

<div class="card">
<h3>Criar Campanha</h3>
<button onclick="cmd('campanha')">
Executar
</button>
</div>

<div class="card">
<h3>Criar Funil</h3>
<button onclick="cmd('funil')">
Executar
</button>
</div>

<div class="card">
<h3>Criar Marca</h3>
<button onclick="cmd('marca')">
Executar
</button>
</div>

<div class="card">
<h3>Criar Produto</h3>
<button onclick="cmd('produto')">
Executar
</button>
</div>

</div>

<br>

<div class="card">

<input
id="idea"
placeholder="Digite sua ideia..."
>

<br><br>

<div
id="out"
class="msg ai"
>
Resultado aparecerá aqui.
</div>

</div>

<script>

async function cmd(type){

const idea =
document.getElementById(
'idea'
).value || 'empresa IA';

document.getElementById(
'out'
).innerText = 'Gerando...';

const r =
await fetch('/command-api',{

method:'POST',

headers:{
'Content-Type':'application/json'
},

body:JSON.stringify({
type:type,
idea:idea
})

});

const d =
await r.json();

document.getElementById(
'out'
).innerText = d.response;

}

</script>
"""
    )

def table_page(title, table, columns):

    if not require_login():
        return redirect("/login")

    rows = cursor.execute(
        f"""
        SELECT {','.join(columns)}
        FROM {table}
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 100
        """,
        (uid(),)
    ).fetchall()

    head = "".join([
        f"<th>{c}</th>"
        for c in columns
    ])

    body = ""

    for r in rows:

        body += (
            "<tr>"
            + "".join([
                f"<td>{str(x)[:500]}</td>"
                for x in r
            ])
            + "</tr>"
        )

    export_link = f"/export/{table}"

    return layout(
        title,
        f"""
<div class="card">

<a href="{export_link}">
<button>
Exportar CSV
</button>
</a>

<br><br>

<table>

<tr>
{head}
</tr>

{body}

</table>

</div>
"""
    )

@web.route("/posts")
def posts_page():
    return table_page(
        "Posts",
        "posts",
        [
            "id",
            "platform",
            "theme",
            "status",
            "scheduled_date",
            "created_at"
        ]
    )

@web.route("/videos")
def videos_page():
    return table_page(
        "Vídeos",
        "videos",
        [
            "id",
            "theme",
            "status",
            "created_at"
        ]
    )

@web.route("/workflows")
def workflows_page():
    return table_page(
        "Workflows",
        "workflows",
        [
            "id",
            "name",
            "status",
            "created_at"
        ]
    )

@web.route("/memory")
def memory_page():
    return table_page(
        "Memória",
        "memory",
        [
            "id",
            "content",
            "created_at"
        ]
    )

@web.route("/files")
def files_page():
    return table_page(
        "Arquivos",
        "files",
        [
            "id",
            "filename",
            "created_at"
        ]
    )

@web.route("/analytics-page")
def analytics_page():
    return table_page(
        "Analytics",
        "analytics",
        [
            "id",
            "event",
            "data",
            "created_at"
        ]
    )

@web.route("/gallery")
def gallery():

    if not require_login():
        return redirect("/login")

    rows = cursor.execute(
        """
        SELECT type,prompt,url
        FROM gallery
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 100
        """,
        (uid(),)
    ).fetchall()

    html = '<div class="gallery">'

    for r in rows:

        html += f"""
<div class="card">

<img src="{r[2]}">

<h3>
{r[0]}
</h3>

<p>
{r[1]}
</p>

</div>
"""

    html += "</div>"

    return layout("Galeria", html)

@web.route("/api-keys")
def api_keys():

    if not require_login():
        return redirect("/login")

    token = secrets.token_hex(24)

    cursor.execute(
        """
        INSERT INTO api_keys(
        user_id,token,created_at
        ) VALUES(?,?,?)
        """,
        (
            uid(),
            token,
            now()
        )
    )

    conn.commit()

    return layout(
        "API System",
        f"""
<div class="card">

<h2>
API TOKEN
</h2>

<p>
{token}
</p>

</div>
"""
    )

@web.route("/billing")
def billing():

    return layout(
        "Stripe Ready",
        """
<div class="card">

<h2>
Stripe Ready
</h2>

<p>
Sistema preparado para:
Free,
Pro,
Agency.
</p>

</div>
"""
    )

@web.route("/export/<table>")
def export_table(table):

    allowed = [
        "posts",
        "videos",
        "workflows",
        "memory",
        "files",
        "analytics",
        "leads"
    ]

    if table not in allowed:
        return "invalid"

    rows = cursor.execute(
        f"""
        SELECT *
        FROM {table}
        WHERE user_id=?
        """,
        (uid(),)
    ).fetchall()

    output = io.StringIO()

    writer = csv.writer(output)

    for r in rows:
        writer.writerow(r)

    output.seek(0)

    return send_file(
        io.BytesIO(
            output.getvalue().encode()
        ),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{table}.csv"
    )

@web.route("/ask", methods=["POST"])
def ask_web():

    data = request.get_json()

    prompt = data.get("prompt")
    agent = data.get("agent","ceo")

    response = ask_ai(
        prompt,
        agent,
        uid()
    )

    return jsonify({
        "response":response
    })

@web.route("/command-api", methods=["POST"])
def command_api():

    data = request.get_json()

    kind = data.get("type")
    idea = data.get("idea")

    prompts = {

        "empresa":
        "Crie uma empresa IA multimilionária.",

        "saas":
        "Crie um SaaS completo.",

        "campanha":
        "Crie campanha viral.",

        "funil":
        "Crie funil completo.",

        "marca":
        "Crie branding premium.",

        "produto":
        "Crie produto digital premium."

    }

    result = ask_ai(
        prompts.get(kind)
        + "\n\nIdeia:\n"
        + idea,
        "ceo",
        uid()
    )

    return jsonify({
        "response":result
    })

@web.route("/upload", methods=["POST"])
def upload():

    file = request.files.get("file")

    if not file:
        return jsonify({
            "response":"Nenhum arquivo."
        })

    filename = secure_filename(file.filename)

    path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    file.save(path)

    content = ""

    if filename.lower().endswith(".pdf"):

        reader = PdfReader(path)

        for p in reader.pages:

            try:
                content += (
                    p.extract_text()
                    + "\n"
                )
            except:
                pass

    elif filename.lower().endswith(".txt"):

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            content = f.read()

    cursor.execute(
        """
        INSERT INTO files(
        user_id,filename,content,created_at
        ) VALUES(?,?,?,?)
        """,
        (
            uid(),
            filename,
            content[:60000],
            now()
        )
    )

    conn.commit()

    save_memory(
        f"Arquivo {filename}: {content[:3000]}",
        uid()
    )

    analysis = ask_ai(
        f"""
        Analise profundamente:
        {filename}

        {content[:14000]}

        Gere:
        resumo,
        insights,
        riscos,
        oportunidades,
        monetização,
        automações,
        estratégia.
        """,
        "ceo",
        uid()
    )

    return jsonify({
        "response":analysis
    })

@web.route("/health")
def health():
    return "OK STREETCORE V8 ONLINE", 200

def run_telegram():

    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    async def start(update, context):
        await update.message.reply_text(
            "🔥 StreetCore OS V8 online."
        )

    async def status(update, context):

        text = "🚀 STREETCORE V8\n\n"

        for t in [
            "memory",
            "tasks",
            "posts",
            "videos",
            "workflows",
            "leads"
        ]:

            total = cursor.execute(
                f"SELECT COUNT(*) FROM {t}"
            ).fetchone()[0]

            text += f"{t}: {total}\n"

        await update.message.reply_text(text)

    async def generic(update, context, role):

        prompt = " ".join(context.args)

        if not prompt:

            await update.message.reply_text(
                "Digite algo."
            )

            return

        result = ask_ai(
            prompt,
            role,
            1
        )

        for i in range(
            0,
            len(result),
            3900
        ):

            await update.message.reply_text(
                result[i:i+3900]
            )

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("status", status)
    )

    app.add_handler(
        CommandHandler(
            "ceo",
            lambda u,c: generic(u,c,"ceo")
        )
    )

    app.add_handler(
        CommandHandler(
            "marketing",
            lambda u,c: generic(u,c,"marketing")
        )
    )

    app.add_handler(
        CommandHandler(
            "dev",
            lambda u,c: generic(u,c,"dev")
        )
    )

    app.run_polling(stop_signals=None)

threading.Thread(
    target=run_telegram,
    daemon=True
).start()

print(
    "🔥 STREETCORE OS V8 ONLINE"
)

web.run(
    host="0.0.0.0",
    port=PORT
)