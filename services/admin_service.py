from services.auth_service import obter_api_key

def painel_admin():
    api_key = obter_api_key()

    return f"""
    <html>
    <head>
        <title>StreetCore OS V17 FREE</title>
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
        </style>
    </head>
    <body>
        <h1>🔥 STREETCORE OS V17 FREE</h1>

        <div class="card">
            <h2>Status</h2>
            <p class="ok">Sistema online</p>
            <p>Telegram ativo</p>
            <p>Flask ativo</p>
            <p>SQLite ativo</p>
            <p>Railway ativo</p>
        </div>

        <div class="card">
            <h2>Novidades V17</h2>
            <p>Pedidos persistentes</p>
            <p>Orçamentos automáticos</p>
            <p>Estoque simples</p>
            <p>Notificações internas</p>
            <p>Operação comercial gratuita</p>
        </div>

        <div class="card">
            <h2>API KEY</h2>
            <p>{api_key}</p>
        </div>
    </body>
    </html>
    """