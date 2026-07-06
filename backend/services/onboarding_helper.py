"""
AYRIA - Helper: Detectar respostas de perguntas pendentes no chat

Quando user envia msg no chat normal, este helper checa se tem pergunta
pendente ativa (pending_current_chat ou pending_next_chat) e se a msg
parece ser uma resposta válida.

Suporta:
- text: aceita qualquer texto com > 2 chars não-vazio
- date: regex DD/MM/AAAA com data válida
- number: parseável como int
- select: match exato com options.values
- multiselect: match com algum option.values

Se user diz "pula", "agora não", "depois", "continuar sem" → marca como pending_next_chat (snooze 24h)
"""
import re
from datetime import datetime, timedelta
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

import models

logger = logging.getLogger(__name__)

# Palavras que indicam "pular" / "adiar"
SKIP_KEYWORDS = {"pula", "pular", "agora não", "agora nao", "depois", "continuar sem", "continua sem", "pode pular", "pode ser depois", "skip"}
SNOOZE_KEYWORDS = {"depois", "agora não", "agora nao", "snooze", "mais tarde", "amanhã", "amanha"}


def _eh_skip(texto: str) -> bool:
    t = texto.strip().lower()
    return any(kw in t for kw in SKIP_KEYWORDS) and len(t) < 50


def _eh_snooze(texto: str) -> bool:
    t = texto.strip().lower()
    return any(kw in t for kw in SNOOZE_KEYWORDS) and len(t) < 50


def _validar_date(texto: str) -> Optional[str]:
    """Aceita DD/MM/AAAA ou DD-MM-AAAA. Retorna ISO ou None."""
    m = re.match(r'^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$', texto.strip())
    if not m:
        return None
    try:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        dt = datetime(y, mo, d)
        if dt.year < 1900 or dt.year > datetime.now().year:
            return None
        return dt.strftime('%Y-%m-%d')
    except ValueError:
        return None


def _validar_time(texto: str) -> Optional[str]:
    """Aceita HH:MM ou HH. Retorna HH:MM ou None."""
    t = texto.strip()
    # HH:MM ou H:MM
    m = re.match(r'^(\d{1,2}):(\d{2})$', t)
    if m:
        try:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
        except ValueError:
            pass
    # HH.MM ou H.MM
    m = re.match(r'^(\d{1,2})\.(\d{2})$', t)
    if m:
        try:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
        except ValueError:
            pass
    # Palavras tipo "3 horas", "3h", "15h30"
    m = re.match(r'^(\d{1,2})\s*[hH](\d{2})?$', t)
    if m:
        try:
            h = int(m.group(1))
            mi = int(m.group(2)) if m.group(2) else 0
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{h:02d}:{mi:02d}"
        except ValueError:
            pass
    return None


def _validar_number(texto: str) -> Optional[float]:
    """Aceita número. Retorna float ou None."""
    try:
        return float(texto.strip().replace(',', '.'))
    except ValueError:
        return None


def _validar_texto(texto: str) -> Optional[str]:
    """Aceita texto com pelo menos 2 chars."""
    t = texto.strip()
    if len(t) >= 2:
        return t
    return None


def _validar_select(texto: str, options: list) -> Optional[str]:
    """Match exato (case-insensitive) com algum valor."""
    if not options:
        return None
    t = texto.strip().lower()
    for opt in options:
        v = (opt.get('value') if isinstance(opt, dict) else opt) or ''
        label = (opt.get('label') if isinstance(opt, dict) else '') or ''
        if t == str(v).lower() or t == str(label).lower():
            return v
    return None


async def validar_e_gravar_resposta_chat(
    db: AsyncSession,
    user: models.User,
    user_msg_content: str,
    chat_id: Optional[str] = None,  # NOVO v3: pra registrar skip por chat
) -> Tuple[bool, Optional[str]]:
    """
    Detecta se a mensagem do user responde uma pergunta pendente (Sistema 2).
    
    Returns:
        (detectou, attribute_code)
        - detectou=True se marcou como answered/skipped/snoozed
        - attribute_code é o código da pergunta tratada
    """
    now = datetime.utcnow()
    
    # 1. Busca pergunta ativa (pending_current_chat OU pending_next_chat OU snoozed expirada)
    pending_res = await db.execute(
        select(models.UserAttribute, models.AttributeDefinition)
        .join(models.AttributeDefinition, models.UserAttribute.attribute_definition_id == models.AttributeDefinition.id)
        .where(
            models.UserAttribute.user_id == user.id,
            (
                models.UserAttribute.status.in_(['pending_next_chat', 'pending_current_chat']) |
                (
                    (models.UserAttribute.status == 'snoozed') &
                    (models.UserAttribute.snooze_until <= now)
                )
            ),
        )
        .order_by(models.UserAttribute.last_asked_at.asc().nulls_first())
        .limit(1)
    )
    row = pending_res.first()
    if not row:
        return False, None
    
    ua, attr_def = row
    
    # 2. Detecta intenção do user
    texto = user_msg_content.strip()
    if not texto:
        return False, None
    
    # Caso 1: user quer pular/snoozar
    if _eh_snooze(texto):
        # Snooze: adia 24h, mantém na fila pra próxima sessão
        ua.status = 'snoozed'
        ua.snooze_until = now + timedelta(hours=24)
        ua.updated_at = now
        await db.flush()
        logger.info(f"⏸️ Sistema 2: user snooze'd '{attr_def.code}' por 24h")
        return True, attr_def.code
    
    if _eh_skip(texto) and not _eh_snooze(texto):
        # Sistema 2 v3: skip é POR CHAT. NÃO pergunta mais NESTE chat.
        # Em chat novo → volta a perguntar.
        ua.status = 'skipped'  # mantém status skipped pra histórico
        ua.skipped_at = now
        ua.updated_at = now
        await db.flush()
        # Grava também em chat_question_skip pra filtrar perguntas neste chat
        if chat_id:
            try:
                # Verifica se já não existe
                from sqlalchemy import select as _sel
                exists_res = await db.execute(
                    _sel(models.ChatQuestionSkip).where(
                        models.ChatQuestionSkip.chat_id == chat_id,
                        models.ChatQuestionSkip.attribute_code == attr_def.code,
                    )
                )
                if not exists_res.scalar_one_or_none():
                    skip_row = models.ChatQuestionSkip(
                        chat_id=chat_id,
                        user_id=user.id,
                        attribute_code=attr_def.code,
                        skipped_at=now,
                    )
                    db.add(skip_row)
                    await db.flush()
            except AttributeError:
                # Model ainda não existe (versão sem v3)
                pass
            except Exception as e:
                logger.warning(f"Não conseguiu registrar skip no chat: {e}")
        logger.info(f"⏭️ Sistema 2 v3: user skipped '{attr_def.code}' neste chat {chat_id[:8] if chat_id else 'N/A'}...")
        return True, attr_def.code
    
    # Caso 2: user tá respondendo → valida por tipo
    valor = None
    q_type = attr_def.attribute_type or 'text'
    
    if q_type == 'date':
        valor = _validar_date(texto)
    elif q_type == 'time':
        valor = _validar_time(texto)
    elif q_type in ('number', 'int', 'float'):
        valor = _validar_number(texto)
    elif q_type == 'select':
        valor = _validar_select(texto, attr_def.options or [])
    elif q_type == 'multiselect':
        # Pra multiselect, exige pelo menos 1 match
        valor = _validar_select(texto, attr_def.options or [])
    else:  # text (default)
        valor = _validar_texto(texto)
    
    if valor is None:
        # Não reconheceu como resposta válida → deixa IA decidir
        return False, None
    
    # Gravou resposta válida
    ua.value = valor
    ua.status = 'answered'
    ua.skipped_at = None
    ua.snooze_until = None
    ua.updated_at = now
    
    # Sincroniza com profile.attributes
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    if profile:
        attrs = dict(profile.attributes or {})
        attrs[attr_def.code] = valor
        profile.attributes = attrs
    
    await db.flush()
    logger.info(f"✅ Sistema 2: user respondeu pendente '{attr_def.code}' = {valor!r}")
    return True, attr_def.code