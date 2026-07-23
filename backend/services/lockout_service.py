"""
AYRIA - Lockout Service (anti brute-force progressivo)
Data: 22/07/2026 — Rafael pediu proteção contra tentativas de login

Regras:
  3 erros  → bloqueia 15 min
  4 erros  → 30 min
  5 erros  → 60 min
  6+ erros → 24 horas
  7+ erros → bloqueio total (só admin pode liberar)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

# Janela de tempo pra resetar contador (default 24h sem erro = libera)
RESET_WINDOW_HOURS = 24

# Tabela de bloqueio progressivo
LOCKOUT_LEVELS = {
    3: {"minutes": 15,  "level": 1, "label": "15 minutos"},
    4: {"minutes": 30,  "level": 2, "label": "30 minutos"},
    5: {"minutes": 60,  "level": 3, "label": "1 hora"},
    6: {"minutes": 1440,"level": 4, "label": "24 horas"},
    7: {"minutes": None,"level": 5, "label": "TOTAL (fale com suporte)"},  # None = sem auto-unlock
}


async def check_lockout(
    db: AsyncSession,
    identifier: str,
    identifier_type: str = "email"
) -> Tuple[bool, Optional[dict]]:
    """
    Verifica se identifier (email/IP) está bloqueado.
    Retorna (is_locked, lockout_info).
    """
    from models import LoginLockout

    res = await db.execute(
        select(LoginLockout)
        .where(LoginLockout.identifier == identifier, LoginLockout.identifier_type == identifier_type)
    )
    lock = res.scalar_one_or_none()
    if not lock:
        return False, None

    # Sem bloqueio ativo
    if not lock.locked_until:
        # Reset de janela (24h sem erro → zera contador)
        hours_since_last = (datetime.now(timezone.utc) - lock.last_failed_at).total_seconds() / 3600
        if hours_since_last >= RESET_WINDOW_HOURS:
            lock.failed_attempts = 0
            lock.lockout_level = 0
            await db.commit()
        return False, None

    # Bloqueio expirou?
    if lock.locked_until <= datetime.now(timezone.utc):
        # Libera mas mantém histórico (não zera)
        lock.locked_until = None
        await db.commit()
        return False, None

    # Bloqueado
    return True, {
        "locked_until": lock.locked_until.isoformat(),
        "level": lock.lockout_level,
        "label": LOCKOUT_LEVELS.get(lock.failed_attempts, LOCKOUT_LEVELS[6])["label"],
        "failed_attempts": lock.failed_attempts,
    }


async def record_failed_attempt(
    db: AsyncSession,
    identifier: str,
    identifier_type: str = "email"
) -> dict:
    """
    Registra tentativa falha e retorna info de bloqueio (se aplicável).
    Retorna {locked, locked_until, level, label, failed_attempts, next_threshold}
    """
    from models import LoginLockout

    res = await db.execute(
        select(LoginLockout)
        .where(LoginLockout.identifier == identifier, LoginLockout.identifier_type == identifier_type)
    )
    lock = res.scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if not lock:
        lock = LoginLockout(
            identifier=identifier,
            identifier_type=identifier_type,
            failed_attempts=1,
            first_failed_at=now,
            last_failed_at=now,
            locked_until=None,
            lockout_level=0,
        )
        db.add(lock)
    else:
        lock.failed_attempts += 1
        lock.last_failed_at = now

    # Aplica regra de bloqueio progressivo
    cfg = LOCKOUT_LEVELS.get(lock.failed_attempts)
    if cfg:
        lock.lockout_level = cfg["level"]
        if cfg["minutes"] is None:
            # Bloqueio total — sem auto-unlock
            lock.locked_until = None  # NULL mas lockout_level=5 = permanente
        else:
            lock.locked_until = now + timedelta(minutes=cfg["minutes"])

    await db.commit()

    # Próximo threshold pra UI mostrar
    next_threshold = None
    if lock.failed_attempts < 3:
        next_threshold = f"mais {3 - lock.failed_attempts} erro(s) → bloqueio de 15 minutos"
    elif lock.failed_attempts < 4:
        next_threshold = "mais 1 erro → bloqueio de 30 minutos"
    elif lock.failed_attempts < 5:
        next_threshold = "mais 1 erro → bloqueio de 1 hora"
    elif lock.failed_attempts < 6:
        next_threshold = "mais 1 erro → bloqueio de 24 horas"
    elif lock.failed_attempts < 7:
        next_threshold = "mais 1 erro → BLOQUEIO TOTAL (fale com suporte)"
    else:
        next_threshold = "Conta bloqueada. Fale com o suporte."

    return {
        "locked": lock.lockout_level >= 1 and (lock.locked_until is not None or lock.lockout_level >= 5),
        "locked_until": lock.locked_until.isoformat() if lock.locked_until else None,
        "level": lock.lockout_level,
        "label": cfg["label"] if cfg else "Conta bloqueada",
        "failed_attempts": lock.failed_attempts,
        "next_threshold": next_threshold,
    }


async def record_success(db: AsyncSession, identifier: str, identifier_type: str = "email"):
    """Zera tentativas após login bem-sucedido."""
    from models import LoginLockout

    res = await db.execute(
        select(LoginLockout)
        .where(LoginLockout.identifier == identifier, LoginLockout.identifier_type == identifier_type)
    )
    lock = res.scalar_one_or_none()
    if lock:
        lock.failed_attempts = 0
        lock.locked_until = None
        lock.lockout_level = 0
        await db.commit()


async def admin_unlock(db: AsyncSession, identifier: str, identifier_type: str, admin_email: str, reason: str = None) -> bool:
    """Admin libera manualmente."""
    from models import LoginLockout

    res = await db.execute(
        select(LoginLockout)
        .where(LoginLockout.identifier == identifier, LoginLockout.identifier_type == identifier_type)
    )
    lock = res.scalar_one_or_none()
    if not lock:
        return False
    lock.failed_attempts = 0
    lock.locked_until = None
    lock.lockout_level = 0
    lock.unlocked_by = admin_email
    lock.unlocked_at = datetime.now(timezone.utc)
    lock.unlock_reason = reason
    await db.commit()
    return True
