from services.analytics_service import resumo_analytics
from services.finance_service import resumo_financeiro
from services.order_service import listar_pedidos
from services.lead_service import listar_leads
from services.production_service import listar_producao
from services.inventory_service import listar_estoque

def cerebro_operacional(pergunta):
    return (
        "🧠 CÉREBRO OPERACIONAL V20\n\n"
        f"Pergunta recebida:\n{pergunta}\n\n"
        "Análise rápida:\n"
        "✅ Verificar leads\n"
        "✅ Criar campanha\n"
        "✅ Gerar conteúdo\n"
        "✅ Conferir pedidos\n"
        "✅ Conferir produção\n"
        "✅ Conferir financeiro\n\n"
        "Decisão sugerida:\n"
        "1. Gere uma campanha com /campanha\n"
        "2. Crie conteúdo em massa com /batch\n"
        "3. Cadastre leads com /lead\n"
        "4. Acompanhe pedidos com /orders\n"
        "5. Acompanhe lucro com /finance\n\n"
        "Resumo do sistema:\n"
        f"{resumo_analytics()}\n\n"
        f"{resumo_financeiro()}\n\n"
        f"Leads:\n{listar_leads()}\n\n"
        f"Pedidos:\n{listar_pedidos()}\n\n"
        f"Produção:\n{listar_producao()}\n\n"
        f"Estoque:\n{listar_estoque()}"
    )