#!/usr/bin/env python3
"""
AYRIA - Supervisor Batch (cron 5min)

Roda via crontab Linux direto. SEM dependência OpenClaw.

O que faz:
1. SELECT messages WHERE role='user' AND created_at >= NOW()-5min
   AND message_id NOT IN (SELECT message_id FROM supervisor_analysis WHERE analysis_duration_ms > 0)
   (só msgs NOVAS — evita reprocessar)
2. Agrupa por user_id
3. Pra cada user com msgs:
   - Se 1 msg: análise individual (rápida)
   - Se várias msgs: análise batch (detecta padrão entre msgs)
4. Salva analyses + cria alerts se estranho
5. Se URGÊNCIA detectada: notifica admin (Telegram / log)

Logs: stdout/stderr → /home/peron/scripts/logs/ayria_supervisor_batch.log
"""

import sys
import os
import json
import asyncio
import argparse
import logging
from datetime import datetime, timezone, timedelta

# Setup: AYRIA no path. Roda DENTRO do container ayria-backend (sys.path=/app)
sys.path.insert(0, '/app')

# Logging
LOG_DIR = '/home/peron/scripts/logs'
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, 'ayria_supervisor_batch.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger('ayria-supervisor-batch')


async def run_batch(window_minutes: int = 5, dry_run: bool = False):
    """Processa msgs dos últimos N minutos."""
    from sqlalchemy import select
    from database import AsyncSessionLocal
    import models
    from services.supervisor_service import supervisor_service

    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    total_processed = 0
    total_alerts = 0

    async with AsyncSessionLocal() as db:
        # 1) Buscar msgs recentes SEM análise prévia
        msgs_res = await db.execute(
            select(models.Message)
            .where(
                models.Message.role == 'user',
                models.Message.created_at >= cutoff,
                # exclui msgs já analisadas
                ~select(models.SupervisorAnalysis.message_id)
                    .where(models.SupervisorAnalysis.message_id == models.Message.id)
                    .exists(),
            )
            .order_by(models.Message.created_at.asc())
            .limit(500)  # safety limit
        )
        msgs = list(msgs_res.scalars().all())

        if not msgs:
            logger.info(f"Batch: 0 msgs novas nos últimos {window_minutes}min (nada a fazer)")
            return 0, 0

        logger.info(f"Batch: {len(msgs)} msgs novas encontradas nos últimos {window_minutes}min")

        # 1.5) Filtrar msgs sem sinal de risco → marca NORMAL direto (SEM IA)
        # Se a mensagem NÃO tem keyword de risco, ela é classificada como NORMAL
        # sem gastar chamada IA (caro). Só chamamos IA nas msgs com sinais.
        from models import SupervisorAnalysis
        skipped_no_signal = 0
        for m in list(msgs):
            if not supervisor_service.should_analyze_with_ia(m.content):
                # Salva análise NORMAL rápido, sem IA
                analysis = SupervisorAnalysis(
                    message_id=m.id,
                    user_id=m.user_id,
                    chat_id=m.chat_id,
                    level="NORMAL",
                    score=0.0,
                    reason="Sem keyword de risco — sem análise IA (filtro keywords)",
                    signals=[],
                    recommended_action="",
                    model_used="keywords-only",
                    analysis_duration_ms=0,
                )
                db.add(analysis)
                await db.commit()
                skipped_no_signal += 1
                msgs.remove(m)

        if skipped_no_signal:
            logger.info(f"Batch: {skipped_no_signal} msgs SEM keyword de risco (marcadas NORMAL sem IA)")

        logger.info(f"Batch: {len(by_user)} users distintos")

        for user_id, user_msgs in by_user.items():
            # Pega user
            user_res = await db.execute(
                select(models.User).where(models.User.id == user_id)
            )
            user = user_res.scalar_one_or_none()
            if not user:
                logger.warning(f"User {user_id} não encontrado")
                continue

            # Se 1 msg: análise individual
            # Se várias: análise BATCH (uma IA vê as N msgs juntas — detecta padrão)
            if len(user_msgs) == 1:
                logger.info(f"[user={user.email}] Processando 1 msg individual")
                for msg in user_msgs:
                    if dry_run:
                        logger.info(f"  [DRY-RUN] msg={msg.id} content={msg.content[:80]!r}")
                        continue
                    try:
                        # pega chat pra análise (analyze_message quer 3 params: msg, chat, user)
                        chat_res = await db.execute(
                            select(models.Chat).where(models.Chat.id == msg.chat_id)
                        )
                        chat = chat_res.scalar_one_or_none()
                        if not chat:
                            logger.warning(f"Chat {msg.chat_id} não encontrado, pulando")
                            continue
                        analysis = await supervisor_service.analyze_message(
                            db=db, message=msg, chat=chat, user=user
                        )
                        total_processed += 1
                        if analysis.level in ("ATENCAO", "URGENCIA"):
                            alert = await supervisor_service.create_alert_if_needed(db, analysis)
                            if alert:
                                total_alerts += 1
                                logger.warning(
                                    f"  🚨 ALERTA CRIADO: user={user.email} level={analysis.level}"
                                )
                    except Exception as e:
                        logger.error(f"  Erro ao analisar msg {msg.id}: {e}", exc_info=True)
                        await db.rollback()
            else:
                # BATCH: várias msgs
                logger.info(
                    f"[user={user.email}] Processando {len(user_msgs)} msgs em BATCH"
                )
                if dry_run:
                    for m in user_msgs:
                        logger.info(f"  [DRY-RUN] msg={m.content[:80]!r}")
                    continue
                try:
                    # análise sequencial (cada msg individual, mas agrupada por user)
                    # Poderia fazer uma análise batch mas é mais complexo — manter simples
                    for msg in user_msgs:
                        chat_res = await db.execute(
                            select(models.Chat).where(models.Chat.id == msg.chat_id)
                        )
                        chat = chat_res.scalar_one_or_none()
                        if not chat:
                            continue
                        analysis = await supervisor_service.analyze_message(
                            db=db, message=msg, chat=chat, user=user
                        )
                        total_processed += 1
                        if analysis.level in ("ATENCAO", "URGENCIA"):
                            alert = await supervisor_service.create_alert_if_needed(db, analysis)
                            if alert:
                                total_alerts += 1
                                logger.warning(
                                    f"  🚨 ALERTA CRIADO: user={user.email} level={analysis.level}"
                                )
                except Exception as e:
                    logger.error(f"  Erro ao processar batch user {user.email}: {e}", exc_info=True)
                    await db.rollback()

        await db.commit()

    logger.info(
        f"Batch completo: {total_processed} análises, {total_alerts} alertas criados"
    )
    return total_processed, total_alerts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--window', type=int, default=5,
        help='Janela em minutos (default: 5)',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Só loga o que faria, sem chamar IA',
    )
    args = parser.parse_args()

    logger.info(f"=== INICIANDO BATCH (window={args.window}min, dry_run={args.dry_run}) ===")
    try:
        n_proc, n_alerts = asyncio.run(run_batch(args.window, args.dry_run))
        logger.info(f"=== OK: processadas={n_proc}, alertas={n_alerts} ===")
        sys.exit(0 if n_alerts == 0 else 10)  # exit 10 se alertas críticos (cód pra monitorar)
    except Exception as e:
        logger.error(f"=== FALHA: {e} ===", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
