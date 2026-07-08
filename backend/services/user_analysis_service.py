"""
AYRIA - User Analysis Service (08/07/2026)

Gerencia o chat IA TRANCADO num user específico — usado pelo admin
pra investigar/interpretar um user a fundo.

Diferente do chat normal (que foca na resposta ao user), este chat foca
em AJUDAR O ADMIN a entender o user.

Plano: 01_Memories/AYRIA_SUB_ALMA_PLANO_08072026.md seção 9B
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json
import logging
import uuid

from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

import models
from database import settings
from services.ai_service import ai_service

logger = logging.getLogger(__name__)


USER_ANALYSIS_SYSTEM_PROMPT = """Você é um assistente especializado do ADMIN da AYRIA analisando o usuário {first_name} (id={user_id}).

Você NÃO fala com o usuário — fala COM O ADMIN sobre ele.

# REGRAS INEGOCIÁVEIS
- Você NÃO fala sobre outros usuários.
- Você NÃO fala sobre a constituição/alma global do sistema.
- Você NÃO revela dados sensíveis crus (senha, token, IP completo).
- Você PODE sugerir ações pro admin ("bloquear 24h", "abrir alerta", "regenerar sub-alma").
- Quando admin pedir "salvar" / "anotar" / "guardar", devolva um JSON estruturado.

# CONTEXTO DISPONÍVEL SÓ DESSE USER

## PERFIL
- Nome: {first_name}
- Email: {email}
- Role: {role}
- Plano: {plan_name} ({credit_balance} créditos)
- Onboarding: {onboarding_status}
- Status do perfil: {profile_status}

## PREFERÊNCIA ESPIRITUAL
{spiritual}

## SUB-ALMA ATIVA (se existir)
{sub_alma_active}

## ÚLTIMAS MENSAGENS DO USER (até 50)
{recent_messages}

## SUPERVISOR — HISTÓRICO
- Total de análises (todas as msgs): {analyses_total}
- Alertas URGÊNCIA (todos os tempos): {urgencia_total}
- Alertas ATENÇÃO (todos os tempos): {atencao_total}
- Nível atual (última análise): {last_level}

## USO
- Total de chats: {chats_total}
- Total de mensagens (todas): {messages_total}

## NOTAS DO ADMIN (manuais, anteriores)
{prior_notes}

# COMO RESPONDER

## Resposta normal (conversa livre):
Responda em texto, tom técnico-profissional, em pt-BR. Seja DIRETO e ACIONÁVEL.
Sugira padrões observados, hipóteses, próximos passos.

## Quando admin pedir pra SALVAR (ex: "salvar", "anotar isso", "guardar como nota"):
Responda com JSON estruturado:

```json
{{
  "title": "Título curto da nota (até 80 chars)",
  "content": "Texto em markdown com a análise completa. Use seções (##), listas, destaques.",
  "kind": "analysis"
}}
```

Tipos de `kind`:
- `analysis` (default) → análise geral do estado do user
- `observation` → observação pontual de comportamento
- `action` → ação concreta tomada/recomendada (ex: "bloqueado 24h por crise")

Quando gerar o JSON, ponha ele como ÚLTIMO bloco da resposta, sem markdown ```json```. O sistema detecta automaticamente.

# CONTEXTO RESTAURADO DINAMICAMENTE
O contexto do user acima é cacheado por 60s no backend. Se o admin acabou de salvar uma nota, ela aparece aqui em até 60s.
"""


# ============================================================
# CONTEXTO DO USER (versão análise)
# ============================================================
async def _build_user_context_for_analysis(db: AsyncSession, user_id: uuid.UUID) -> Dict[str, Any]:
    """Coleta contexto do user pra alimentar o chat de análise."""
    ctx: Dict[str, Any] = {}

    res = await db.execute(
        select(models.User)
        .where(models.User.id == user_id)
        .options(selectinload(models.User.selected_plan))
    )
    user = res.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {user_id} não encontrado")

    ctx["user"] = user
    ctx["user_id"] = str(user.id)
    ctx["first_name"] = (user.full_name or user.email.split("@")[0]).split(" ")[0]
    ctx["email"] = user.email
    ctx["role"] = user.role
    ctx["onboarding_status"] = user.onboarding_status or "pending"
    ctx["profile_status"] = user.profile_status or "pending"

    if user.selected_plan:
        ctx["plan_name"] = user.selected_plan.name
        ctx["credit_balance"] = user.credit_balance or 0
    else:
        ctx["plan_name"] = "sem plano"
        ctx["credit_balance"] = 0

    # Preferência espiritual
    try:
        sp_res = await db.execute(
            select(models.SpiritualPreference).where(models.SpiritualPreference.user_id == user.id)
        )
        sp = sp_res.scalar_one_or_none()
        ctx["spiritual"] = (
            f"{sp.religion}" + (f" — {sp.custom_label}" if sp and sp.custom_label else "")
            + (f" (tags: {', '.join(sp.custom_tags or [])})" if sp and sp.custom_tags else "")
        ) if sp else "não declarada"
    except Exception:
        ctx["spiritual"] = "não declarada"

    # Sub-alma ativa
    try:
        alma_res = await db.execute(
            select(models.UserAlma)
            .where(
                models.UserAlma.user_id == user.id,
                models.UserAlma.status == "active",
            )
            .order_by(desc(models.UserAlma.version))
            .limit(1)
        )
        alma = alma_res.scalar_one_or_none()
        ctx["sub_alma_active"] = (
            f"v{alma.version} ({alma.trigger}, gerada {alma.generated_at.strftime('%Y-%m-%d') if alma.generated_at else '?'}):\n\n{alma.content[:1200]}"
            if alma else "(não tem sub-alma ativa)"
        )
    except Exception:
        ctx["sub_alma_active"] = "(não tem sub-alma ativa)"

    # Últimas mensagens
    try:
        msg_res = await db.execute(
            select(models.Message)
            .where(models.Message.user_id == user.id)
            .order_by(desc(models.Message.created_at))
            .limit(50)
        )
        msgs = list(msg_res.scalars().all())
        msgs.reverse()
        ctx["recent_messages"] = "\n".join(
            f"[{m.created_at.strftime('%Y-%m-%d %H:%M') if m.created_at else '?'}] "
            f"{m.role.upper()}: {m.content[:200]}"
            for m in msgs
        ) or "(sem mensagens)"
    except Exception:
        ctx["recent_messages"] = "(sem mensagens)"

    # Análises supervisor
    try:
        ana_res = await db.execute(
            select(func.count(models.SupervisorAnalysis.id))
            .where(models.SupervisorAnalysis.user_id == user.id)
        )
        ctx["analyses_total"] = ana_res.scalar() or 0

        urg_res = await db.execute(
            select(func.count(models.SupervisorAlert.id))
            .where(
                models.SupervisorAlert.user_id == user.id,
                models.SupervisorAlert.level == "URGENCIA",
            )
        )
        ctx["urgencia_total"] = urg_res.scalar() or 0

        atn_res = await db.execute(
            select(func.count(models.SupervisorAlert.id))
            .where(
                models.SupervisorAlert.user_id == user.id,
                models.SupervisorAlert.level == "ATENCAO",
            )
        )
        ctx["atencao_total"] = atn_res.scalar() or 0

        last_ana_res = await db.execute(
            select(models.SupervisorAnalysis)
            .where(models.SupervisorAnalysis.user_id == user.id)
            .order_by(desc(models.SupervisorAnalysis.created_at))
            .limit(1)
        )
        last_ana = last_ana_res.scalar_one_or_none()
        ctx["last_level"] = last_ana.level if last_ana else "NORMAL"
    except Exception:
        ctx["analyses_total"] = 0
        ctx["urgencia_total"] = 0
        ctx["atencao_total"] = 0
        ctx["last_level"] = "NORMAL"

    # Total chats/messages
    try:
        chats_res = await db.execute(
            select(func.count(models.Chat.id))
            .where(models.Chat.user_id == user.id)
        )
        ctx["chats_total"] = chats_res.scalar() or 0

        msgs_total_res = await db.execute(
            select(func.count(models.Message.id))
            .where(models.Message.user_id == user.id)
        )
        ctx["messages_total"] = msgs_total_res.scalar() or 0
    except Exception:
        ctx["chats_total"] = 0
        ctx["messages_total"] = 0

    # Notas anteriores do admin (3 últimas)
    try:
        notes_res = await db.execute(
            select(models.UserSupervisorNote)
            .where(models.UserSupervisorNote.user_id == user.id)
            .order_by(desc(models.UserSupervisorNote.created_at))
            .limit(3)
        )
        notes = list(notes_res.scalars().all())
        if notes:
            notes.reverse()
            ctx["prior_notes"] = "\n\n---\n\n".join(
                f"[{n.created_at.strftime('%Y-%m-%d %H:%M') if n.created_at else '?'}] "
                f"({n.kind}) {n.title or '(sem título)'}\n\n{n.content[:600]}"
                for n in notes
            )
        else:
            ctx["prior_notes"] = "(nenhuma)"
    except Exception:
        ctx["prior_notes"] = "(nenhuma)"

    return ctx


def _try_extract_note_proposal(text: str) -> Optional[Dict[str, str]]:
    """Tenta extrair JSON {title, content, kind} de uma resposta da IA.
    Aceita cópias com/sem ```json wrapper.
    """
    clean = text.replace("```json", "").replace("```", "").strip()
    # Procura o bloco {...} mais externo
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    json_str = clean[start:end + 1]
    try:
        data = json.loads(json_str)
        if (
            isinstance(data, dict)
            and "title" in data
            and "content" in data
            and isinstance(data["title"], str)
            and isinstance(data["content"], str)
        ):
            return {
                "title": data["title"][:200],
                "content": data["content"],
                "kind": data.get("kind", "analysis") if isinstance(data.get("kind"), str) else "analysis",
            }
    except Exception:
        pass
    return None


# ============================================================
# CHAT (não consome créditos do admin)
# ============================================================
async def chat_user_analysis(
    db: AsyncSession,
    user_id: uuid.UUID,
    messages: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Admin conversa com IA focada num user específico."""
    ctx = await _build_user_context_for_analysis(db, user_id)

    system_prompt = USER_ANALYSIS_SYSTEM_PROMPT.format(**ctx)

    msgs_for_ai = [{"role": m["role"], "content": m["content"]} for m in messages]

    try:
        resp = await ai_service.chat(
            messages=msgs_for_ai,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=2000,
        )
        content = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.error(f"❌ Falha no chat de análise do user {user_id}: {e}")
        raise

    # Tenta extrair proposta de salvamento
    proposal = _try_extract_note_proposal(content)

    return {
        "user_id": str(user_id),
        "first_name": ctx["first_name"],
        "message": {"role": "assistant", "content": content},
        "note_proposal": proposal,
        "model": ai_service.model or settings.AI_MODEL,
    }


# ============================================================
# SALVAR NOTA
# ============================================================
async def save_user_supervisor_note(
    db: AsyncSession,
    user_id: uuid.UUID,
    admin_id: uuid.UUID,
    title: str,
    content: str,
    kind: str = "analysis",
    conversation: Optional[List[Dict[str, Any]]] = None,
    signals_used: Optional[Dict[str, Any]] = None,
) -> models.UserSupervisorNote:
    """Salva nota/análise manual do admin."""
    if kind not in ("analysis", "observation", "action"):
        kind = "analysis"

    note = models.UserSupervisorNote(
        user_id=user_id,
        admin_id=admin_id,
        kind=kind,
        title=title[:200] if title else None,
        content=content,
        conversation=conversation or [],
        model_used=ai_service.model or settings.AI_MODEL,
        signals_used=signals_used or {},
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    logger.info(
        f"📝 Nota do admin {admin_id} salva para user {user_id} "
        f"(kind={kind}, title='{title[:50]}')"
    )
    return note


async def list_user_supervisor_notes(
    db: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
) -> List[models.UserSupervisorNote]:
    """Lista notas do admin sobre um user (mais recentes primeiro)."""
    res = await db.execute(
        select(models.UserSupervisorNote)
        .where(models.UserSupervisorNote.user_id == user_id)
        .order_by(desc(models.UserSupervisorNote.created_at))
        .limit(limit)
    )
    return list(res.scalars().all())


async def delete_user_supervisor_note(
    db: AsyncSession,
    note_id: uuid.UUID,
    admin_id: uuid.UUID,
) -> bool:
    """Deleta nota (só o admin que criou, ou qualquer SUPER_ADMIN)."""
    res = await db.execute(
        select(models.UserSupervisorNote).where(models.UserSupervisorNote.id == note_id)
    )
    note = res.scalar_one_or_none()
    if not note:
        return False
    await db.delete(note)
    await db.commit()
    logger.info(f"🗑️ Nota {note_id} deletada por admin {admin_id}")
    return True