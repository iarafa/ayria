"""
AYRIA - Auto Migration System (v2 — inteligente)

Detecta automaticamente o que já foi aplicado, mesmo em bancos antigos
onde a tabela `schema_migrations` não existia.

ESTRATÉGIA:
1. Tenta criar tabela `schema_migrations` (idempotente)
2. Para cada migration:
   - Se já está marcada em `schema_migrations` → pula
   - Se não está, mas a "marca no schema" (tabela/coluna-âncora) já existe
     → marca como aplicada (sem executar) e pula
   - Senão, executa o SQL

Marcas no schema por migration:
  002 → tabela `attribute_definitions` existe
  003 → coluna `users.profile_status` existe
  005 → tabela `plans` existe
  006 → tabela `supervisor_analysis` existe
  007 → tabela `user_attributes` existe (era pra ter sido renomeada)
  008 → tabela `ayria_prompt_config` existe
  009 → tabela `ayria_modular_prompts` ou `ayria_prompt_modules` existe
  010 → coluna `supervisor_analysis.risk_sublevel` existe
  011 → índice idx_ayria_prompt_active_key existe
  012 → coluna `users.blocked_until` existe
  013 → coluna `users.verification_token` existe
"""
import os
import glob
import logging
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"
SCHEMA_TABLE = "schema_migrations"

# Para cada migration, define COMO detectar se já foi aplicada.
# Se a verificação for None → não dá pra detectar (sempre roda, mas é idempotente por IF EXISTS)
SCHEMA_MARKERS = {
    "002_alignment.sql":          "TABLE attribute_definitions",
    "003_astrology.sql":          "COLUMN users.profile_status",
    "004_user_avatar.sql":        "COLUMN users.avatar_url",
    "005_plans_credits.sql":      "TABLE plans",
    "006_supervisor.sql":         "TABLE supervisor_analysis",
    "007_onboarding_skip.sql":    "TABLE user_attributes",
    "008_ayria_prompt_config.sql":"TABLE ayria_prompt_config",
    "009_ayria_modular_prompts.sql": "TABLE ayria_modular_prompts",
    "010_supervisor_risk_sublevel.sql": "COLUMN supervisor_analysis.risk_sublevel",
    "011_prompt_unique_fix.sql":  "INDEX idx_ayria_prompt_active_key",
    "012_user_block.sql":         "COLUMN users.blocked_until",
    "013_email_verification.sql": "COLUMN users.verification_token",
    "014_backfill_verified.sql": "is_verified_users_backfilled",
    "015_sub_alma_user.sql": "TABLE user_supervisor_notes",
    "016_rate_limit.sql": "TABLE rate_limit_events",
    "020_action_types_and_usage.sql": "TABLE action_types",
}


async def _check_marker(db: AsyncSession, marker: str | None) -> bool:
    """Retorna True se a marca existe no schema atual."""
    if not marker:
        return False

    parts = marker.split(maxsplit=1)
    if len(parts) != 2:
        return False
    kind, target = parts

    try:
        if kind == "TABLE":
            table = target.strip("`")
            result = await db.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = :name LIMIT 1
            """), {"name": table})
            return result.scalar() is not None

        elif kind == "COLUMN":
            table, col = target.split(".")
            result = await db.execute(text("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = :t AND column_name = :c LIMIT 1
            """), {"t": table, "c": col})
            return result.scalar() is not None

        elif kind == "INDEX":
            result = await db.execute(text("""
                SELECT 1 FROM pg_indexes
                WHERE indexname = :name LIMIT 1
            """), {"name": target})
            return result.scalar() is not None

        # Marcadores especiais (não-ANSI)
        elif marker == "is_verified_users_backfilled":
            # Considera aplicada se NÃO existe nenhum user com is_verified=FALSE E verification_token IS NULL
            # (esses são os "antigos sem verificar" que precisam do backfill)
            result = await db.execute(text("""
                SELECT 1 FROM users
                WHERE is_verified = FALSE AND verification_token IS NULL
                LIMIT 1
            """))
            return result.scalar() is None

    except Exception as e:
        logger.warning(f"   ⚠️ Erro ao verificar marca {marker}: {e}")

    return False


async def ensure_schema_table(db: AsyncSession):
    """Cria tabela de controle de migrations (idempotente)."""
    await db.execute(text(f"""
        CREATE TABLE IF NOT EXISTS {SCHEMA_TABLE} (
            name VARCHAR(255) PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
    """))
    await db.commit()


async def get_applied_migrations(db: AsyncSession) -> set[str]:
    """Retorna conjunto de migrations já aplicadas (registradas)."""
    try:
        result = await db.execute(text(f"SELECT name FROM {SCHEMA_TABLE}"))
        return {row[0] for row in result.fetchall()}
    except Exception:
        return set()


async def mark_applied(db: AsyncSession, name: str):
    """Marca uma migration como aplicada na tabela de controle."""
    await db.execute(
        text(f"INSERT INTO {SCHEMA_TABLE} (name) VALUES (:name) ON CONFLICT DO NOTHING"),
        {"name": name},
    )
    await db.commit()


async def run_pending_migrations(db: AsyncSession) -> dict:
    """
    Detecta e aplica migrations pendentes.
    Idempotente e tolerante a bancos legados.
    """
    stats = {"applied": [], "skipped_existing": [], "skipped_recorded": [], "failed": None, "skipped": []}

    # 1. Tabela de controle
    await ensure_schema_table(db)
    recorded = await get_applied_migrations(db)

    # 2. Lista arquivos
    if not MIGRATIONS_DIR.exists():
        logger.warning(f"⚠️ Diretório de migrations não encontrado: {MIGRATIONS_DIR}")
        return stats

    files = sorted(glob.glob(str(MIGRATIONS_DIR / "*.sql")))
    files = [f for f in files if not os.path.basename(f).startswith("init")]

    logger.info(f"📋 Migrations: {len(files)} arquivo(s) | {len(recorded)} já registradas")

    # 3. Para cada migration, decide se aplica
    # Alias de conveniência (compat com main.py)
    stats["skipped"] = []  # preenchido dinamicamente ao final

    for filepath in files:
        filename = os.path.basename(filepath)
        marker = SCHEMA_MARKERS.get(filename)

        # CASO 1: já registrada em schema_migrations → pula
        if filename in recorded:
            stats["skipped_recorded"].append(filename)
            logger.debug(f"   ⏭️  {filename} (registrada)")
            continue

        # CASO 2: marker existe no schema → marca como aplicada sem executar
        if marker and await _check_marker(db, marker):
            await mark_applied(db, filename)
            stats["skipped_existing"].append(filename)
            logger.info(f"   🔍 {filename} (já no schema — marcada retroativamente)")
            continue

        # CASO 3: aplica de fato
        logger.info(f"   ▶️  Aplicando {filename}...")
        try:
            sql = Path(filepath).read_text(encoding="utf-8")

            from database import engine
            async with engine.begin() as conn:
                statements = [s.strip() for s in sql.split(";") if s.strip()]
                for stmt in statements:
                    lines = [l for l in stmt.split("\n") if l.strip() and not l.strip().startswith("--")]
                    if not lines:
                        continue
                    clean_stmt = "\n".join(lines)
                    await conn.execute(text(clean_stmt))

            await mark_applied(db, filename)
            stats["applied"].append(filename)
            logger.info(f"   ✅ {filename} aplicada")

        except Exception as e:
            logger.error(f"   ❌ FALHA ao aplicar {filename}: {e}")
            stats["failed"] = {"name": filename, "error": str(e)}
            raise

    return stats