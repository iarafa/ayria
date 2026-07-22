"""
AYRIA - Rate Limiter Service (19/07/2026)

Sliding-window rate limiter + geo lookup + blacklist.

Componentes:
- RateLimitStore: controla tentativas por (ip, endpoint) em janela deslizante
- is_bypass: IPs em RATE_LIMIT_BYPASS_IPS não entram na conta (desenvolvimento)
- is_blacklisted: checa bloqueio permanente em ip_blacklist
- lookup_geo: ip-api.com (free, sem key), com cache 30 dias em memória

Regra anti-trava do Rafael (29/06/2026):
- Whitelist de IPs (loopback + LAN) isentos
- Bypass aplicável por env var, sem reiniciar
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal

logger = logging.getLogger(__name__)


# ============================================================
# Configuração
# ============================================================

@dataclass
class RateLimitConfig:
    """Política por endpoint."""
    max_failures: int       # falhas permitidas antes do bloqueio
    window_seconds: int     # janela deslizante
    block_seconds: int      # quanto tempo fica bloqueado após estourar

    @staticmethod
    def from_env() -> Dict[str, "RateLimitConfig"]:
        return {
            "/auth/login": RateLimitConfig(
                max_failures=int(os.getenv("RL_LOGIN_MAX_FAILURES", "5")),
                window_seconds=int(os.getenv("RL_LOGIN_WINDOW_SECONDS", "60")),
                block_seconds=int(os.getenv("RL_LOGIN_BLOCK_SECONDS", "300")),
            ),
            "/auth/register": RateLimitConfig(
                max_failures=int(os.getenv("RL_REGISTER_MAX_FAILURES", "3")),
                window_seconds=int(os.getenv("RL_REGISTER_WINDOW_SECONDS", "3600")),
                block_seconds=int(os.getenv("RL_REGISTER_BLOCK_SECONDS", "3600")),
            ),
            "/auth/forgot-password": RateLimitConfig(
                max_failures=int(os.getenv("RL_FORGOT_MAX_FAILURES", "3")),
                window_seconds=int(os.getenv("RL_FORGOT_WINDOW_SECONDS", "3600")),
                block_seconds=int(os.getenv("RL_FORGOT_BLOCK_SECONDS", "3600")),
            ),
        }


CONFIG = RateLimitConfig.from_env()


def _bypass_ips() -> set[str]:
    raw = os.getenv("RATE_LIMIT_BYPASS_IPS", "127.0.0.1,::1,192.168.3.37")
    return {ip.strip() for ip in raw.split(",") if ip.strip()}


BYPASS_IPS = _bypass_ips()


# ============================================================
# Estado em memória
# ============================================================

@dataclass
class AttemptRecord:
    """Sliding window: lista de timestamps de falhas."""
    failures: List[float] = field(default_factory=list)
    blocked_until: Optional[float] = None     # epoch seconds
    total_successes: int = 0


class RateLimitStore:
    """Thread-safe-ish (asyncio) sliding window por (ip, endpoint)."""

    def __init__(self):
        self._attempts: Dict[Tuple[str, str], AttemptRecord] = {}
        self._lock = asyncio.Lock()
        self._geo_cache: Dict[str, Tuple[float, str]] = {}  # ip -> (cached_at, geo_str)

    async def check(self, ip: str, endpoint: str) -> Tuple[bool, Optional[int]]:
        """
        Retorna (allowed, retry_in_seconds).
        Se allowed=False, retry_in_seconds é o tempo até desbloquear.
        """
        if ip in BYPASS_IPS:
            return True, None

        cfg = CONFIG.get(endpoint)
        if not cfg:
            return True, None    # endpoint sem política

        async with self._lock:
            key = (ip, endpoint)
            now = time.time()
            rec = self._attempts.get(key)
            if not rec:
                rec = AttemptRecord()
                self._attempts[key] = rec

            # Checa bloqueio ativo
            if rec.blocked_until and now < rec.blocked_until:
                retry = int(rec.blocked_until - now)
                return False, retry

            # Janela deslizante
            cutoff = now - cfg.window_seconds
            rec.failures = [t for t in rec.failures if t > cutoff]
            return True, None

    async def record_failure(self, ip: str, endpoint: str) -> int:
        """Registra falha. Retorna o retry_in_seconds se bloqueou agora."""
        if ip in BYPASS_IPS:
            return 0

        cfg = CONFIG.get(endpoint)
        if not cfg:
            return 0

        async with self._lock:
            key = (ip, endpoint)
            now = time.time()
            rec = self._attempts.get(key) or AttemptRecord()
            cutoff = now - cfg.window_seconds
            rec.failures = [t for t in rec.failures if t > cutoff]
            rec.failures.append(now)
            self._attempts[key] = rec

            if len(rec.failures) >= cfg.max_failures:
                rec.blocked_until = now + cfg.block_seconds
                logger.warning(
                    f"🔒 RATE LIMIT: ip={ip} endpoint={endpoint} "
                    f"BLOQUEADO por {cfg.block_seconds}s "
                    f"(após {len(rec.failures)} falhas em {cfg.window_seconds}s)"
                )
                return cfg.block_seconds
            return 0

    async def record_success(self, ip: str, endpoint: str) -> None:
        """Reset contador após sucesso."""
        if ip in BYPASS_IPS:
            return

        async with self._lock:
            key = (ip, endpoint)
            rec = self._attempts.get(key)
            if rec:
                rec.failures.clear()
                rec.blocked_until = None
                rec.total_successes += 1

    async def unblock(self, ip: str, endpoint: Optional[str] = None) -> int:
        """Desbloqueio manual. Retorna qtd de entries limpas."""
        cleared = 0
        async with self._lock:
            keys = list(self._attempts.keys())
            for key in keys:
                k_ip, k_ep = key
                if k_ip != ip:
                    continue
                if endpoint and k_ep != endpoint:
                    continue
                rec = self._attempts[key]
                if rec.blocked_until or rec.failures:
                    rec.blocked_until = None
                    rec.failures.clear()
                    cleared += 1
        return cleared

    def snapshot(self) -> Dict:
        """Resumo público do estado atual."""
        now = time.time()
        blocked = []
        alert = []
        for (ip, ep), rec in self._attempts.items():
            if ip in BYPASS_IPS:
                continue
            if rec.blocked_until and now < rec.blocked_until:
                blocked.append({
                    "ip": ip, "endpoint": ep,
                    "blocked_until": rec.blocked_until,
                    "retry_in_seconds": int(rec.blocked_until - now),
                    "failures_in_window": len(rec.failures),
                })
            elif rec.failures:
                # Em alerta: tem falhas recentes mas não bloqueado
                cutoff = now - CONFIG.get(ep, RateLimitConfig(99, 60, 0)).window_seconds
                recent_failures = [t for t in rec.failures if t > cutoff]
                if recent_failures:
                    alert.append({
                        "ip": ip, "endpoint": ep,
                        "failures_in_window": len(recent_failures),
                    })
        return {"blocked": blocked, "alert": alert}


# Singleton global
STORE = RateLimitStore()


# ============================================================
# Geo lookup (ip-api.com)
# ============================================================

async def lookup_geo(ip: str) -> str:
    """Retorna string curta tipo 'Itatiba/SP' ou 'Desconhecido' se falhar."""
    if ip in BYPASS_IPS:
        return "Local (bypass)"
    if ip.startswith("192.168.") or ip.startswith("10.") or ip == "127.0.0.1" or ip == "::1":
        return "Rede local"

    now = time.time()
    cached = STORE._geo_cache.get(ip)
    if cached and (now - cached[0]) < 30 * 86400:
        return cached[1]

    try:
        # ip-api.com free, sem key, 45 req/min. Sem HTTPS mas tudo bem (não é secreto).
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"http://ip-api.com/json/{ip}?fields=city,regionName,country")
            if r.status_code == 200:
                data = r.json()
                geo = f"{data.get('city') or '?'}/{data.get('regionName') or '?'}"
                STORE._geo_cache[ip] = (now, geo)
                return geo
    except Exception as e:
        logger.debug(f"geo lookup failed for {ip}: {e}")
    return "Desconhecido"


# ============================================================
# Persistência (eventos + blacklist)
# ============================================================

async def log_event(
    ip: str, endpoint: str, success: bool,
    email_attempted: Optional[str] = None, user_agent: Optional[str] = None,
) -> None:
    """Grava evento de rate limit no banco (append-only)."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(
                text("""
                    INSERT INTO rate_limit_events
                        (ip, endpoint, success, email_attempted, user_agent)
                    VALUES
                        (CAST(:ip AS INET), :ep, :ok, :email, :ua)
                """),
                {"ip": ip, "ep": endpoint, "ok": success, "email": email_attempted, "ua": user_agent},
            )
            await db.commit()
    except Exception as e:
        logger.warning(f"rate_limit_events INSERT falhou: {e}")


async def get_blacklist() -> List[dict]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(text("""
            SELECT ip::text, reason, added_by, added_at, expires_at
            FROM ip_blacklist
            ORDER BY added_at DESC
        """))
        return [
            {
                "ip": r[0], "reason": r[1], "added_by": r[2],
                "added_at": r[3].isoformat() if r[3] else None,
                "expires_at": r[4].isoformat() if r[4] else None,
            }
            for r in result.fetchall()
        ]


async def is_blacklisted(ip: str) -> bool:
    """Checa se IP está bloqueado permanentemente."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT 1 FROM ip_blacklist
                    WHERE ip = CAST(:ip AS INET)
                      AND (expires_at IS NULL OR expires_at > NOW())
                    LIMIT 1
                """),
                {"ip": ip},
            )
            return result.scalar() is not None
    except Exception as e:
        logger.warning(f"is_blacklisted falhou: {e}")
        return False


async def add_blacklist(ip: str, reason: str, added_by: str, expires_at: Optional[str] = None) -> None:
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("""
                INSERT INTO ip_blacklist (ip, reason, added_by, expires_at)
                VALUES (CAST(:ip AS INET), :reason, :by, CAST(:expires AS TIMESTAMPTZ))
                ON CONFLICT (ip) DO UPDATE
                SET reason = EXCLUDED.reason, expires_at = EXCLUDED.expires_at
            """),
            {"ip": ip, "reason": reason, "by": added_by, "expires": expires_at},
        )
        await db.commit()


async def remove_blacklist(ip: str) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("DELETE FROM ip_blacklist WHERE ip = CAST(:ip AS INET)"),
            {"ip": ip},
        )
        await db.commit()
        return result.rowcount or 0
