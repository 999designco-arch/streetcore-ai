from services.auth_service import obter_api_key

def painel_admin():

    api_key = obter_api_key()

    return f"""
    <html>

    <head>

        <title>StreetCore OS V19 FREE MEGA</title>

        <style>

            body {{
                background: #050505;
                color: white;
                font-family: Arial;
                padding: 30px;
            }}

            .card {{
                background: #111;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
                border: 1px solid #333;
            }}

            .ok {{
                color: #00ff88;
                font-weight: bold;
            }}

            h1 {{
                font-size: 34px;
            }}

        </style>

    </head>

    <body>

        <h1>🔥 STREETCORE OS V19 FREE MEGA</h1>

        <div class="card">

            <h2>Status</h2>

            <p class="ok">
                Sistema online
            </p>

            <p>Telegram ativo</p>
            <p>Flask ativo</p>
            <p>SQLite ativo</p>
            <p>Railway ativo</p>

        </div>

        <div class="card">

            <h2>Novidades V19</h2>

            <p>CRM de Leads</p>
            <p>Pipeline comercial</p>
            <p>Catálogo persistente</p>
            <p>Pacotes de conteúdo IA</p>
            <p>Geração em massa</p>
            <p>Operação comercial avançada</p>

        </div>

        <div class="card">

            <h2>API KEY</h2>

            <p>{api_key}</p>

        </div>

    </body>

    </html>
    """