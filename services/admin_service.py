from services.auth_service import obter_api_key

def painel_admin():
    api_key = obter_api_key()

    return f"""
    <html>
    <head>
        <title>StreetCore OS V20 ULTRA FREE</title>
        <style>
            body {{
                background: #050505;
                color: white;
                font-family: Arial;
                padding: 30px;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
                gap: 15px;
            }}
            .card {{
                background: #111;
                padding: 20px;
                border-radius: 14px;
                border: 1px solid #333;
            }}
            .ok {{
                color: #00ff88;
                font-weight: bold;
            }}
            h1 {{
                font-size: 36px;
            }}
            a {{
                color: #00ff88;
            }}
        </style>
    </head>

    <body>
        <h1>🔥 STREETCORE OS V20 ULTRA FREE</h1>
        <p class="ok">Sistema online, modular, gratuito e operacional.</p>

        <div class="grid">
            <div class="card">
                <h2>Status</h2>
                <p>Telegram ativo</p>
                <p>Flask ativo</p>
                <p>SQLite ativo</p>
                <p>Railway ativo</p>
            </div>

            <div class="card">
                <h2>Operação</h2>
                <p>Pedidos</p>
                <p>Produção</p>
                <p>Estoque</p>
                <p>Fornecedores</p>
            </div>

            <div class="card">
                <h2>Comercial</h2>
                <p>Leads</p>
                <p>Pipeline</p>
                <p>Orçamentos</p>
                <p>Catálogo</p>
            </div>

            <div class="card">
                <h2>IA Operacional</h2>
                <p>Cérebro operacional</p>
                <p>Diagnóstico automático</p>
                <p>Plano automático</p>
                <p>Metas e KPIs</p>
            </div>

            <div class="card">
                <h2>Links</h2>
                <p><a href="/health">Health</a></p>
                <p><a href="/analytics">Analytics</a></p>
                <p><a href="/finance">Financeiro</a></p>
                <p><a href="/orders">Pedidos</a></p>
                <p><a href="/leads">Leads</a></p>
                <p><a href="/production">Produção</a></p>
            </div>

            <div class="card">
                <h2>API KEY</h2>
                <p>{api_key}</p>
            </div>
        </div>
    </body>
    </html>
    """