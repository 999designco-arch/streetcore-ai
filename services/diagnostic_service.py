from services.finance_service import resumo_financeiro
from services.order_service import listar_pedidos
from services.lead_service import listar_leads
from services.inventory_service import listar_estoque
from services.production_service import listar_producao

def diagnostico_empresa():
    return (
        "🩺 DIAGNÓSTICO STREETCORE V20\n\n"
        "FINANCEIRO:\n"
        f"{resumo_financeiro()}\n\n"
        "LEADS:\n"
        f"{listar_leads()}\n\n"
        "PEDIDOS:\n"
        f"{listar_pedidos()}\n\n"
        "PRODUÇÃO:\n"
        f"{listar_producao()}\n\n"
        "ESTOQUE:\n"
        f"{listar_estoque()}\n\n"
        "AÇÕES RECOMENDADAS:\n"
        "✅ Aumentar geração de leads\n"
        "✅ Criar campanha semanal\n"
        "✅ Publicar reels diariamente\n"
        "✅ Atualizar status dos pedidos\n"
        "✅ Controlar despesas\n"
        "✅ Fazer backup semanal"
    )