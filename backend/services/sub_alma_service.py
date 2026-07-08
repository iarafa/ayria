"""
AYRIA - Sub-Alma Service (08/07/2026)

Gera e gerencia a SUB-ALMA individual de cada usuário.
Modula a constituição base com base no perfil, histórico e sinais.

Plano: 01_Memories/AYRIA_SUB_ALMA_PLANO_08072026.md
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import json
import logging
import uuid

from sqlalchemy import select, desc, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

import models
from database import settings
from services.ai_service import ai_service

logger = logging.getLogger(__name__)


SUB_ALMA_GENERATION_PROMPT = """Você é um assistente especializado em PERSONALIDADE E COMUNICAÇÃO.

Gere a SUB-ALMA de um usuário da AYRIA — uma camada de personalização INDIVIDUAL
que vai modular a forma como a AYRIA fala com ESTE usuário específico.

# DADOS DO USUÁRIO
- Nome: {first_name}
- Email: {email}
- Preferência espiritual: {spiritual}
- Onboarding completo: {onboarding_done}
- Numerologia: {numerology_summary}
- Astrologia: {astrology_summary}
- Plano: {plan_name} ({credit_balance} créditos)
- Role: {role}

# PERFIL (JSONB do onboarding)
{profile_json}

# ÚLTIMAS MENSAGENS DO USER (recentes primeiro)
{recent_messages}

# SINAIS DETECTADOS
{signals_summary}

# ALMAS ANTERIORES (se houver — pra preservar tom e ajustes manuais)
{previous_almas}

# CAMPOS TRAVADOS PELO USER (manual_lock — NÃO altere)
{manual_lock}

# SUA TAREFA
Escreva a sub-alma em MARKDOWN estruturado com as seções abaixo. Seja ESPECÍFICO
a este user — nada genérico. Se faltar informação, escreva "indefinido" em vez de inventar.

Use tom direto, em português, sem floreio. Cada seção 2-5 bullets curtos.

# ESTRUTURA OBRIGATÓRIA
```markdown
# SUB-ALMA de {first_name}

## Tom preferido
- (formal/informal/direto/leve/profundo, com base no que user demonstrou)

## Como chamar
- Apelido preferido: (ou "indefinido")
- Evitar: (o que NÃO usar)

## Espiritualidade
- (numerologia sim/não, astrologia sim/não, religião, abordagem)

## Gatilhos emocionais observados
- (com base em sinais — NUNCA inventar coisa grave sem sinal claro)

## Estilo de resposta ideal
- (frases curtas/longas, emojis sim/não, disclaimers, etc)

## Última atualização
Gerada em {generated_at} baseado em {messages_count} mensagens.
```

# REGRAS
1. JAMAIS cite dados sensíveis (senha, email completo se tiver @admin, telefone, token).
2. Se houver `manual_lock`, NÃO sobrescreva os campos travados.
3. Se houver alma anterior, MANTENHA continuidade (não inverta o que já estava).
4. NUNCA mencione ao user que existe "sub-alma" ou que a IA foi instruída por análise.
5. NÃO invente personalidade — se faltam sinais, escreva "indefinido".

Responda APENAS o markdown da sub-alma, sem explicações extras, sem ```markdown```."""


# ============================================================
# CONTEXTO DO USER
# ============================================================
async def _collect_user_context(db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Coleta todos os dados do user pra gerar a sub-alma."""
    ctx: Dict[str, Any] = {}

    # User base (com plano eager loaded pra evitar greenlet)
    from sqlalchemy.orm import selectinload
    res = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
        .options(selectinload(models.User.selected_plan))
    )
    user = res.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {user_id} não encontrado")

    ctx["user"] = user
    ctx["first_name"] = (user.full_name or user.email.split("@")[0]).split(" ")[0]
    ctx["email"] = user.email
    ctx["role"] = user.role
    ctx["onboarding_done"] = user.onboarding_status == "completed"

    # Plano (relationship já carregado via selectinload)
    if user.selected_plan:
        ctx["plan_name"] = user.selected_plan.name
        ctx["credit_balance"] = user.credit_balance or 0
    else:
        ctx["plan_name"] = "sem plano"
        ctx["credit_balance"] = 0

    # Numerologia + astrologia (resumo curto)
    if user.numerology_data:
        n = user.numerology_data
        nums = []
        if isinstance(n, dict):
            for k, v in n.items():
                if isinstance(v, dict) and "numero" in v:
                    nums.append(f"{k}={v['numero']}")
                elif isinstance(v, (int, float)):
                    nums.append(f"{k}={v}")
        ctx["numerology_summary"] = ", ".join(nums[:8]) if nums else str(n)[:200]
    else:
        ctx["numerology_summary"] = "não calculada"

    if user.astrology_data:
        a = user.astrology_data
        if isinstance(a, dict):
            ctx["astrology_summary"] = (
                f"Sol {a.get('sol', '?')}, "
                f"Lua {a.get('lua', '?')}, "
                f"Asc {a.get('ascendente', '?')}"
            )
        else:
            ctx["astrology_summary"] = str(a)[:200]
    else:
        ctx["astrology_summary"] = "não calculada"

    # Preferência espiritual
    try:
        sp_res = await db.execute(
            select(models.SpiritualPreference).where(models.SpiritualPreference.user_id == user.id)
        )
        sp = sp_res.scalar_one_or_none()
        ctx["spiritual"] = sp.religion if sp else "indefinido"
    except Exception:
        ctx["spiritual"] = "indefinido"

    # Perfil (JSONB do onboarding)
    try:
        prof_res = await db.execute(
            select(models.UserProfile).where(models.UserProfile.user_id == user.id)
        )
        prof = prof_res.scalar_one_or_none()
        ctx["profile_json"] = json.dumps(prof.attributes or {}, ensure_ascii=False, indent=2)[:2000]
    except Exception:
        ctx["profile_json"] = "{}"

    # Últimas mensagens (até 30)
    try:
        msg_res = await db.execute(
            select(models.Message)
            .where(models.Message.user_id == user.id, models.Message.role == "user")
            .order_by(desc(models.Message.created_at))
            .limit(30)
        )
        msgs = list(msg_res.scalars().all())
        msgs.reverse()  # cronológico
        ctx["recent_messages"] = "\n".join(
            f"[{m.created_at.strftime('%Y-%m-%d %H:%M') if m.created_at else '?'}] {m.content[:200]}"
            for m in msgs
        )
        ctx["messages_count"] = len(msgs)
    except Exception:
        ctx["recent_messages"] = "(sem mensagens ainda)"
        ctx["messages_count"] = 0

    # Alertas do supervisor
    try:
        from sqlalchemy import func
        alerts_res = await db.execute(
            select(func.count(models.SupervisorAlert.id))
            .where(
                models.SupervisorAlert.user_id == user.id,
                models.SupervisorAlert.level.in_(["ATENCAO", "URGENCIA"]),
            )
        )
        ctx["alerts_count"] = alerts_res.scalar() or 0
    except Exception:
        ctx["alerts_count"] = 0

    # Última alma ativa (se houver)
    try:
        prev_res = await db.execute(
            select(models.UserAlma)
            .where(
                models.UserAlma.user_id == user.id,
                models.UserAlma.status.in_(["active", "superseded"]),
            )
            .order_by(desc(models.UserAlma.version))
            .limit(1)
        )
        prev = prev_res.scalar_one_or_none()
        if prev:
            ctx["previous_alma"] = {
                "version": prev.version,
                "content": prev.content,
                "trigger": prev.trigger,
                "manual_lock": prev.manual_lock or {},
            }
            ctx["previous_almas"] = (
                f"Versão {prev.version} ({prev.trigger}):\n\n{prev.content[:1500]}\n\n"
                f"manual_lock: {json.dumps(prev.manual_lock or {}, ensure_ascii=False)}"
            )
        else:
            ctx["previous_alma"] = None
            ctx["previous_almas"] = "(primeira geração)"
    except Exception:
        ctx["previous_alma"] = None
        ctx["previous_almas"] = "(primeira geração)"

    # Manual lock da alma atual
    ctx["manual_lock"] = json.dumps(
        (ctx["previous_alma"] or {}).get("manual_lock", {}),
        ensure_ascii=False,
    )

    # Resumo de sinais
    ctx["signals_summary"] = (
        f"- Mensagens analisadas: {ctx['messages_count']}\n"
        f"- Alertas (ATENCAO+URGENCIA) totais: {ctx['alerts_count']}\n"
        f"- Onboarding completo: {ctx['onboarding_done']}"
    )

    ctx["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    return ctx


# ============================================================
# GERAÇÃO
# ============================================================
async def _call_ai_generate_sub_alma(ctx: Dict[str, Any]) -> str:
    """Chama a IA pra gerar a sub-alma."""
    prompt = SUB_ALMA_GENERATION_PROMPT.format(
        first_name=ctx["first_name"],
        email=ctx["email"],
        spiritual=ctx["spiritual"],
        onboarding_done=ctx["onboarding_done"],
        numerology_summary=ctx["numerology_summary"],
        astrology_summary=ctx["astrology_summary"],
        plan_name=ctx["plan_name"],
        credit_balance=ctx["credit_balance"],
        role=ctx["role"],
        profile_json=ctx["profile_json"],
        recent_messages=ctx["recent_messages"],
        signals_summary=ctx["signals_summary"],
        previous_almas=ctx["previous_almas"],
        manual_lock=ctx["manual_lock"],
        generated_at=ctx["generated_at"],
        messages_count=ctx["messages_count"],
    )

    resp = await ai_service.chat(
        messages=[{"role": "user", "content": "Gere a sub-alma agora."}],
        system_prompt=prompt,
        temperature=0.5,
        max_tokens=1500,
    )
    content = (resp.choices[0].message.content or "").strip()
    # Limpa markdown wrapper se a IA colocar
    content = content.replace("```markdown", "").replace("```", "").strip()
    return content


async def generate_user_sub_alma(
    db: AsyncSession,
    user_id: uuid.UUID,
    trigger: str = "admin_manual",
    created_by: Optional[uuid.UUID] = None,
    auto_approve: bool = False,
) -> models.UserAlma:
    """Gera nova versão da sub-alma do user.

    - Cria registro com status='draft' (ou 'active' se auto_approve=True).
    - Marca a alma anterior 'active' como 'superseded'.
    - trigger: origem da geração.
    """
    ctx = await _collect_user_context(db, user_id)

    # 1) Marca alma ativa anterior como superseded (via Core update async-safe)
    try:
        await db.execute(
            update(models.UserAlma)
            .where(
                and_(
                    models.UserAlma.user_id == user_id,
                    models.UserAlma.status == "active",
                )
            )
            .values(status="superseded")
        )
    except Exception as e:
        logger.warning(f"   ⚠️ Falha ao superseded alma anterior (pode ser normal se não existe): {e}")

    # 2) Calcula próxima versão
    try:
        last_ver_res = await db.execute(
            select(models.UserAlma.version)
            .where(models.UserAlma.user_id == user_id)
            .order_by(desc(models.UserAlma.version))
            .limit(1)
        )
        last_ver = last_ver_res.scalar() or 0
    except Exception:
        last_ver = 0
    next_version = last_ver + 1

    # 3) Chama IA
    try:
        content = await _call_ai_generate_sub_alma(ctx)
    except Exception as e:
        logger.error(f"❌ Falha na geração de sub-alma do user {user_id}: {e}")
        raise

    # 4) Cria nova alma
    signals_used = {
        "messages_analyzed": ctx.get("messages_count", 0),
        "alerts_count": ctx.get("alerts_count", 0),
        "profile_filled": bool(ctx.get("profile_json") and ctx["profile_json"] != "{}"),
        "onboarding_done": ctx.get("onboarding_done", False),
        "previous_version": ctx.get("previous_alma", {}).get("version") if ctx.get("previous_alma") else None,
    }

    now = datetime.now(timezone.utc)
    expires_at = None if auto_approve else (now + timedelta(days=7))

    new_alma = models.UserAlma(
        user_id=user_id,
        version=next_version,
        status="active" if auto_approve else "draft",
        content=content,
        signals_used=signals_used,
        trigger=trigger,
        model_used=ai_service.model or settings.AI_MODEL,
        generated_at=now,
        approved_at=now if auto_approve else None,
        approved_by=created_by if auto_approve else None,
        created_by=created_by,
        expires_at=expires_at,
        manual_lock=ctx.get("previous_alma", {}).get("manual_lock", {}) if ctx.get("previous_alma") else {},
    )
    db.add(new_alma)
    await db.commit()
    await db.refresh(new_alma)
    logger.info(
        f"✅ Sub-alma v{next_version} gerada para user {user_id} "
        f"(trigger={trigger}, auto_approve={auto_approve}, status={new_alma.status})"
    )
    return new_alma


# ============================================================
# LEITURA
# ============================================================
async def get_user_active_alma(db: AsyncSession, user_id: uuid.UUID) -> Optional[models.UserAlma]:
    """Retorna a alma ativa do user (None se não houver)."""
    res = await db.execute(
        select(models.UserAlma)
        .where(
            models.UserAlma.user_id == user_id,
            models.UserAlma.status == "active",
        )
        .order_by(desc(models.UserAlma.version))
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_user_draft_alma(db: AsyncSession, user_id: uuid.UUID) -> Optional[models.UserAlma]:
    """Retorna a draft pendente do user (se houver)."""
    res = await db.execute(
        select(models.UserAlma)
        .where(
            models.UserAlma.user_id == user_id,
            models.UserAlma.status == "draft",
        )
        .order_by(desc(models.UserAlma.version))
        .limit(1)
    )
    return res.scalar_one_or_none()


async def get_user_alma_history(db: AsyncSession, user_id: uuid.UUID, limit: int = 5) -> List[models.UserAlma]:
    """Histórico de versões (default: últimas 5)."""
    res = await db.execute(
        select(models.UserAlma)
        .where(models.UserAlma.user_id == user_id)
        .order_by(desc(models.UserAlma.version))
        .limit(limit)
    )
    return list(res.scalars().all())


# ============================================================
# APROVAÇÃO / REJEIÇÃO / ROLLBACK
# ============================================================
async def approve_draft_alma(
    db: AsyncSession,
    user_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> Optional[models.UserAlma]:
    """Aprova draft pendente → vira active. Superseded a anterior."""
    draft = await get_user_draft_alma(db, user_id)
    if not draft:
        return None

    # Superseded a ativa anterior
    try:
        await db.execute(
            update(models.UserAlma)
            .where(
                and_(
                    models.UserAlma.user_id == user_id,
                    models.UserAlma.status == "active",
                )
            )
            .values(status="superseded")
        )
    except Exception as e:
        logger.warning(f"   ⚠️ Falha ao superseded ativa anterior: {e}")

    now = datetime.now(timezone.utc)
    draft.status = "active"
    draft.approved_at = now
    draft.approved_by = admin_id
    draft.expires_at = None
    await db.commit()
    await db.refresh(draft)
    logger.info(f"✅ Sub-alma v{draft.version} aprovada para user {user_id} por admin {admin_id}")
    return draft


async def reject_draft_alma(
    db: AsyncSession,
    user_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> Optional[models.UserAlma]:
    """Rejeita draft pendente → vai pra archived."""
    draft = await get_user_draft_alma(db, user_id)
    if not draft:
        return None

    draft.status = "archived"
    draft.expires_at = None
    await db.commit()
    await db.refresh(draft)
    logger.info(f"🗑️ Sub-alma v{draft.version} rejeitada/arquivada para user {user_id}")
    return draft


async def rollback_alma(
    db: AsyncSession,
    user_id: uuid.UUID,
    target_version: int,
    admin_id: uuid.UUID,
) -> Optional[models.UserAlma]:
    """Volta a uma versão específica: supersedea a ativa, ativa a target."""
    res = await db.execute(
        select(models.UserAlma)
        .where(
            models.UserAlma.user_id == user_id,
            models.UserAlma.version == target_version,
        )
    )
    target = res.scalar_one_or_none()
    if not target:
        return None

    # Superseded a ativa atual
    try:
        await db.execute(
            update(models.UserAlma)
            .where(
                and_(
                    models.UserAlma.user_id == user_id,
                    models.UserAlma.status == "active",
                )
            )
            .values(status="superseded")
        )
    except Exception as e:
        logger.warning(f"   ⚠️ Falha ao superseded ativa no rollback: {e}")

    # Ativa a target
    target.status = "active"
    target.approved_at = datetime.now(timezone.utc)
    target.approved_by = admin_id
    target.expires_at = None
    await db.commit()
    await db.refresh(target)
    logger.info(f"↩️ Rollback pra sub-alma v{target_version} do user {user_id} por admin {admin_id}")
    return target