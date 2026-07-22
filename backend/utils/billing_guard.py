"""
AYRIA - Billing Guard (19/07/2026)

Middleware / helper que checa se o user tem acesso ao conteúdo pago
(baseado em billing_status + blocked_until + credit_balance).

Lógica de acesso (regra de negócio):
- billing_status = 'active' ou 'trialing' → LIBERADO (mesmo com credit_balance = 0; pode usar Chat)
- billing_status = 'past_due':
    - Se blocked_until > NOW() → LIBERADO (tolerância 3 dias pra trocar cartão)
    - Se blocked_until <= NOW() → BLOQUEADO
- billing_status = 'unpaid' ou 'incomplete_expired' → BLOQUEADO
- billing_status = 'canceled':
    - Se current_period_end > NOW() → LIBERADO (até fim do período)
    - Caso contrário → BLOQUEADO
- billing_status = 'incomplete' → BLOQUEADO
- billing_status = 'billing_not_enabled':
    - Se credit_balance > 0 → LIBERADO (trial free / saldo pré-pago)
    - Se credit_balance = 0 → BLOQUEADO
"""
from datetime import datetime, timezone
from typing import Tuple
import models

# Status que LIBERAM acesso independente do resto
_FREELY_OPEN_STATUSES = {"active", "trialing"}


def check_access(user: models.User) -> Tuple[bool, str]:
    """
    Retorna (has_access: bool, reason: str).

    Não lança exceção — o caller decide se quer 200 com aviso ou 403.
    """
    now = datetime.now(timezone.utc)
    status = user.billing_status or "billing_not_enabled"

    # 1. Status livremente abertos
    if status in _FREELY_OPEN_STATUSES:
        return True, f"billing_status={status}"

    # 2. past_due → checa tolerância
    if status == "past_due":
        if user.blocked_until and user.blocked_until > now:
            return True, f"past_due + tolerancia ate {user.blocked_until.isoformat()}"
        return False, "past_due sem tolerancia — cartao precisa ser atualizado"

    # 3. canceled → checa se ainda dentro do período pago
    if status == "canceled":
        if user.blocked_until and user.blocked_until > now:
            return True, f"canceled mas ainda dentro do periodo (ate {user.blocked_until.isoformat()})"
        return False, "assinatura cancelada e periodo expirado"

    # 4. Bloqueados diretos
    if status in ("unpaid", "incomplete_expired", "incomplete"):
        return False, f"billing_status={status} bloqueia acesso"

    # 5. billing_not_enabled → depende do saldo
    if status == "billing_not_enabled":
        if (user.credit_balance or 0) > 0:
            return True, f"sem assinatura mas tem {user.credit_balance} creditos"
        return False, "sem assinatura e sem creditos — contratar plano"

    # Fallback conservador
    return False, f"billing_status='{status}' desconhecido"


def has_access(user: models.User) -> bool:
    """Wrapper só com bool."""
    return check_access(user)[0]