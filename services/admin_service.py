def painel_admin():
    return """
    <html>
    <head>
        <title>StreetCore OS V11</title>
        <style>
            body {
                background: #050505;
                color: white;
                font-family: Arial;
                padding: 30px;
            }
            .card {
                background: #111;
                padding: 20px;
                border-radius: 12px;
                margin-bottom: 15px;
                border: 1px solid #333;
            }
            h1 {
                color: #fff;
            }
            .ok {
                color: #00ff88;
            }
        </style>
    </head>
    <body>
        <h1>🔥 STREETCORE OS V11</h1>

        <div class="card">
            <h2>Status</h2>
            <p class="ok">Sistema online</p>
            <p>Telegram ativo</p>
            <p>Flask ativo</p>
            <p>Services conectados</p>
        </div>

        <div class="card">
            <h2>Funções</h2>
            <p>IA Conversacional</p>
            <p>Posts Instagram</p>
            <p>Stories</p>
            <p>Reels</p>
            <p>Roteiros de vídeo</p>
            <p>Campanhas</p>
            <p>Workflows</p>
            <p>Analytics</p>
            <p>Memória simples</p>
        </div>
    </body>
    </html>
    """