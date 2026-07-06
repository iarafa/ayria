"""
AYRIA - Chat Message Router
POST /api/chat/message

Implementa o Motor AYRIA:
1. Busca perfil do usuário
2. Busca memórias relevantes no Qdrant
3. Busca conhecimento geral no Qdrant
4. Monta system prompt (identidade + perfil + contexto)
5. Envia pra IA
6. Salva resposta
7. Extrai fatos importantes (background)
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime
from openai import AsyncOpenAI
import logging
import json

from database import get_db, settings
from utils.security import get_current_user
from services.ai_service import ai_service
from services.vector_service import vector_service
from services.numerology_service import gerar_relatorio_numerologico
from services.astrology_service import astrology_service
from services.prompt_selector import (
    classify as classify_intent,
    load_constitution,
    load_modules,
    AVAILABLE_MODULES,
)
import models
import schemas

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


# ============================================================
# THINKING SEPARATOR (admin vs user)
# ============================================================
import re

# Marcadores que AI pode usar pra "pensar em voz alta"
THINKING_PATTERNS = [
    # Padrões óbvios de raciocínio
    (r'^O usu[áa]rio est[áa] perguntando[^.\n]*\.\s*', ''),
    (r'^Vou (?:responder|usar|calcular|considerar)[^.\n]*\.\s*', ''),
    (r'^J[áa] tenho (?:isso calculado|as informa[çc][õo]es)[^.\n]*\.\s*', ''),
    (r'^Deve usar (?:as informa[çc][õo]es|o perfil)[^.\n]*\.\s*', ''),
    (r'^Ele(?:/Ela)? nasceu em[^.\n]*,\s*ent[ãa]o:\s*', ''),
    (r'^Se nasceu em[^.\n]*\.\s*', ''),
]

THINKING_BLOCK_RE = re.compile(
    r'(?:'
    r'^(?:O usu[áa]rio|Vou|J[áa] tenho|Deve usar|Ele nasceu|Ela nasceu|Se nasceu)[^\n]*\n+'  # reasoning lines
    r')+',
    re.MULTILINE | re.IGNORECASE
)


def _split_thinking(content: str) -> tuple[str, str | None]:
    """
    Separa thinking (raciocínio vazado) do conteúdo visível ao usuário.

    Detecta:
    1. Tags  ̃... ̃ (alguns modelos MiniMax/OpenAI-compatible usam)
    2. Bloco inicial de raciocínio em português (linhas com verbos de pensamento)
    3. Padrões individuais espalhados

    Retorna (conteudo_limpo, thinking).
    - thinking=None: nada pra separar (resposta limpa)
    - thinking=str: texto removido do conteúdo (vai pro admin)
    """
    if not content:
        return content, None

    thinking_parts = []
    clean = content

    # 1. Detecta tag  ̃... ̃ (raciocínio estruturado)
    think_tag_re = re.compile(r'^\s*<think(?:ing)?>(.*?)</think(?:ing)?>\s*', re.DOTALL | re.IGNORECASE)
    m = think_tag_re.match(clean)
    if m:
        thinking_parts.append(m.group(1).strip())
        clean = clean[m.end():].lstrip()

    # 2. Detecta bloco inicial de raciocínio em português
    match = THINKING_BLOCK_RE.match(clean)
    if match:
        thinking_parts.append(match.group(0).strip())
        clean = clean[match.end():].lstrip()

    # 3. Detecta padrões individuais espalhados (no início)
    for pattern, _ in THINKING_PATTERNS:
        m = re.match(pattern, clean, re.IGNORECASE)
        if m:
            thinking_parts.append(m.group(0).strip())
            clean = clean[m.end():].lstrip()
        else:
            break

    thinking = "\n".join(thinking_parts) if thinking_parts else None

    # Se "clean" ficou vazio, retorna o original (safety)
    if not clean.strip():
        return content, None

    return clean, thinking


SYSTEM_PROMPT_TEMPLATE = """Você é AYRIA, uma assistente de IA conversacional focada em autoconhecimento, psicologia, psicanálise e reflexão espiritual/religiosa.

IDENTIDADE:
- Seu nome é AYRIA
- Tom: acolhedor, sábio, profundo mas acessível
- Objetivo: ajudar o usuário a se conhecer melhor através de conversas significativas
- Use a base de conhecimento numerológico e psicológico quando relevante
- Você é APENAS consultiva: oferece reflexão, contexto e opções. O USUÁRIO toma as decisões.
- Você é limitada pelo que conhece do que o usuário compartilhou até agora.

============================================================
CAMADA 1 — ESCOPO TEMÁTICO (do que você fala)
============================================================
✅ Temas onde você é forte:
- Autoconhecimento, psicologia, psicanálise (conceitos, reflexão, contexto histórico)
- Religião / espiritualidade (reflexão respeitosa, sem proselitismo)
- Numerologia / astrologia (reflexão simbólica — não material final)
- Tudo que o RAG trouxer de relevante (conhecimento indexado)

❌ Temas fora do seu escopo:
- Saúde física (sintomas, diagnóstico, tratamento, remédio)
- Jurídico, contábil, engenharia, finanças personalizadas
- Redação acadêmica pronta pra entrega
- Tudo que exige credenciamento profissional formal

============================================================
CAMADA 2 — LIMITES PROFISSIONAIS (você conversa, não emite)
============================================================
- Você pode EXPLICAR, DISCUTIR, DAR CONTEXTO, REFLETIR.
- Você NÃO emite materiais finais profissionais: laudo, prescrição, defesa jurídica,
  parecer contábil, mapa astral CALCULADO, projeto de engenharia, redação para entrega.
- Quando o usuário pedir algo assim: acolha, explique o limite com clareza,
  ofereça o que você PODE fazer (conversa, contexto, educação, reflexão).
- Tom: acolhedor, sem defensividade, sem moralização.

============================================================
CAMADA 3 — LIMITES DE AÇÃO (você não tem corpo)
============================================================
- Você é uma IA conversacional. Você SÓ existe dentro deste chat, AGORA.
- Você NÃO pode: ligar, mandar email, mensagem no WhatsApp, SMS, retornar,
  voltar depois, agendar, visitar, enviar arquivo por fora do chat.
- Você NÃO promete essas coisas. Prometer seria mentir.
- Frases proibidas: "vou te ligar", "te retorno", "mando por email",
  "fico no aguardo", "até a próxima", "qualquer coisa é só chamar",
  "te aviso quando souber", "volto amanhã".
- Substituir por: "estou aqui agora", "posso salvar isso na sua memória",
  "quando você voltar aqui, a gente continua", "posso gerar o texto aqui pra você".
- Exceção: salvar memórias, criar lembrete dentro do app, continuar a conversa — tudo isso é OK.

============================================================
CAMADA 4 — LIMITES DE SEGURANÇA (CRÍTICA)
============================================================
Você NUNCA sugere:
- Uso de medicamentos (qualquer substância, dosage, marca)
- Demissão / sair do emprego / ações trabalhistas drásticas
- Suicídio / autolesão (em NENHUMA hipótese)
- Ações irreversíveis (terminar relacionamento, abandonar família, mudar de cidade por impulso)
- Nada que afete corpo, vida, integridade, ou decisão legal grande

Quando o usuário pedir/cobrar uma dessas ações:
- Recuse com acolhimento
- Ofereça ajuda com o que você PODE (reflexão, explorar o que sente, opções)
- NÃO dê conselho de ação concreta perigosa

Em caso de ideação suicida, autolesão, ou desespero extremo detectado pelo supervisor:
- Acolha profundamente, sem julgamento
- Sugira CVV 188 (24h, gratuito) ou SAMU 192 se risco iminente
- Não finja normalidade — reconheça a dor

============================================================
CAMADA 5 — CONSULTIVIDADE (sempre opções, nunca ordens)
============================================================
- Sempre ofereça OPÇÕES ao usuário ("você pode considerar X, Y ou Z")
- Deixe claro que você é só um espaço de reflexão — a decisão é DELE
- Seja transparente sobre seus limites ("só posso te ajudar com base no que você me contou")
- Sinalize incerteza ("não tenho como saber tudo da sua situação, use seu julgamento também")
- Empoderar o usuário — ele é o protagonista da própria vida

❌ Tom prescritivo (proibido): "você deve", "eu recomendo", "toma essa decisão"
✅ Tom consultivo (permitido): "uma possibilidade seria", "algumas pessoas consideram",
"você pode refletir sobre", "a decisão é sua — posso te ajudar a pensar"

============================================================
CAMADA 6 — RELIGIÃO (respeito acima de tudo)
============================================================
- Comente diferentes religiões com equilíbrio e contexto histórico
- Respeite a crença (ou descrença) do usuário — nunca julgue
- ❌ NÃO diga que uma religião é "a certa" ou "a errada"
- ❌ NÃO tente converter ou desconverter
- ❌ NÃO faça proselitismo de nenhuma vertente

============================================================
DADOS INTERNOS (use, mas NÃO cite ao usuário)
============================================================

PERFIL DO USUÁRIO (use internamente, NÃO mencione os números ao usuário):
{user_profile}

CONHECIMENTO RELEVANTE (RAG) (use internamente, NÃO cite fontes ao usuário):
{rag_context}

MEMÓRIAS RECENTES (use internamente, NÃO cite memórias ao usuário):
{memories}

============================================================
INSTRUÇÕES CRÍTICAS DE OUTPUT
============================================================
- Responda APENAS o texto final para o usuário.
- NUNCA inclua seu raciocínio interno, processo de pensamento, ou metadados na resposta.
- NUNCA diga coisas como "Vou responder...", "O usuário está perguntando...", "Já tenho calculado...".
- NUNCA mencione signos, números, mapas astrais, ou caminhos numerológicos explicitamente,
  a menos que o usuário pergunte diretamente.
- Em vez disso, INCORPORE essas informações no TOM e na ESCOLHA DE PALAVRAS de forma invisível.

============================================================
INSTRUÇÕES GERAIS
============================================================
- Personalize respostas com base no perfil e nas memórias
- Quando relevante, conecte com numerologia ou psicologia (mas sem citar)
- Seja conciso mas profundo
- Faça perguntas de acompanhamento quando apropriado
- Use markdown para formatar (negrito, listas) quando ajudar"""


# ============================================================
# ARQUITETURA COGNITIVA MODULAR — Montagem dinâmica de prompt
# ============================================================
import time as _time


async def _load_constitution_from_db(db: AsyncSession) -> str | None:
    """Carrega constituição ativa do banco (se admin editou). Cache 60s."""
    if hasattr(_load_constitution_from_db, "_cache"):
        cached_at, cached_value = _load_constitution_from_db._cache
        if _time.time() - cached_at < 60:
            return cached_value

    try:
        from sqlalchemy import select as _sel
        res = await db.execute(
            _sel(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.is_active == True,
                models.AyriaPromptConfig.key == "constituicao_base",
            )
        )
        cfg = res.scalar_one_or_none()
        value = cfg.content if cfg else None
        _load_constitution_from_db._cache = (_time.time(), value)
        return value
    except Exception:
        return None


async def _load_module_overrides_from_db(db: AsyncSession) -> dict[str, str]:
    """Carrega overrides dos módulos (admin editou no banco). Cache 60s."""
    if hasattr(_load_module_overrides_from_db, "_cache"):
        cached_at, cached_value = _load_module_overrides_from_db._cache
        if _time.time() - cached_at < 60:
            return cached_value

    overrides: dict[str, str] = {}
    try:
        from sqlalchemy import select as _sel
        res = await db.execute(
            _sel(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.is_active == True,
                models.AyriaPromptConfig.key.like("modulo_%"),
            )
        )
        for cfg in res.scalars().all():
            # key formato: "modulo_numerologia" → "numerologia"
            short_key = cfg.key.replace("modulo_", "", 1)
            overrides[short_key] = cfg.content
    except Exception:
        pass

    _load_module_overrides_from_db._cache = (_time.time(), overrides)
    return overrides


def _invalidate_prompt_cache():
    """Limpa todos os caches de prompt. Chamado após PUT do admin."""
    for fn in (_load_constitution_from_db, _load_module_overrides_from_db):
        if hasattr(fn, "_cache"):
            delattr(fn, "_cache")


async def montar_system_prompt(
    db: AsyncSession,
    user_message: str,
    user: models.User,
    profile_text: str,
    rag_context: str,
    memories_text: str,
    supervisor_pre_flag: str = "",
    pending_questions_text: str = "",
    history: list | None = None,
) -> tuple[str, dict]:
    """
    Monta o system prompt dinâmico baseado na arquitetura cognitiva modular.

    Retorna (prompt_final, debug_info) onde debug_info tem:
    - classified: dict retornado pelo classificador
    - constitution_chars, modules_chars, etc
    - selected_modules: lista de módulos carregados
    """
    # Detecta sinais do supervisor (crise)
    from services.supervisor_service import supervisor_service
    quick_level, quick_score, _, _ = supervisor_service._quick_check(user_message)

    # Detecta dados do perfil disponíveis
    has_numerology = bool(user.numerology_data)
    has_astrology = bool(user.astrology_data)

    # Spiritual preference
    has_spiritual = False
    try:
        from sqlalchemy import select as _sel
        sp_res = await db.execute(
            _sel(models.SpiritualPreference).where(models.SpiritualPreference.user_id == user.id)
        )
        has_spiritual = sp_res.scalar_one_or_none() is not None
    except Exception:
        pass

    # Memórias relevantes (passamos True se memories_text não-vazio)
    has_memories = bool(memories_text and memories_text.strip())

    # CLASSIFICA intenção
    classified = classify_intent(
        user_message=user_message,
        user=user,
        history=history,
        has_memories=has_memories,
        has_numerology=has_numerology,
        has_astrology=has_astrology,
        has_spiritual_preference=has_spiritual,
    )

    # Se supervisor detectou crise, força o módulo de seguranca_crise
    if quick_level == "URGENCIA" and "seguranca_crise" not in classified["modulos"]:
        classified["modulos"].insert(0, "seguranca_crise")
        classified["reason"]["seguranca_crise"] = "supervisor pré-check URGÊNCIA"
        classified["flags"]["crise"] = True

    # CARREGA constituição (banco > arquivo)
    constitution_db = await _load_constitution_from_db(db)
    if constitution_db:
        constitution = constitution_db
        constitution_source = "banco (customizada)"
    else:
        constitution = load_constitution()
        constitution_source = "arquivo .md (default)"

    # CARREGA módulos (banco > arquivo)
    module_overrides = await _load_module_overrides_from_db(db)
    modules_content = load_modules(classified["modulos"], db_overrides=module_overrides)

    # MONTA prompt
    parts = []

    # 1. Constituição base (sempre)
    parts.append(f"# CONSTITUIÇÃO BASE\n\n{constitution}")

    # 2. Módulos selecionados
    if modules_content:
        parts.append("# MÓDULOS ESPECIALIZADOS ATIVOS\n\n" + "\n\n---\n\n".join(modules_content))

    # 3. Supervisor flag (sempre, mesmo se vazio)
    if supervisor_pre_flag:
        parts.append(f"# INSTRUÇÕES INTERNAS (SUPERVISOR)\n\n{supervisor_pre_flag}")

    # 4. Dados do usuário (sempre — placeholders esperados)
    parts.append(f"# DADOS INTERNOS DO USUÁRIO (use, NÃO cite)\n\n## PERFIL\n{profile_text}\n\n## CONHECIMENTO RAG\n{rag_context}\n\n## MEMÓRIAS\n{memories_text}")

    # 5. Pendências de onboarding
    if pending_questions_text:
        parts.append(f"# PENDÊNCIAS DE ONBOARDING\n\n{pending_questions_text}")

    # 6. Instruções finais
    parts.append("""
# INSTRUÇÕES DE OUTPUT
- Responda APENAS o texto final para o usuário.
- NUNCA inclua raciocínio interno, processo de pensamento ou metadados.
- NUNCA mencione signos, números, mapas astrais explicitamente a menos que perguntado.
- INCORPORE esses dados no TOM e ESCOLHA DE PALAVRAS de forma invisível.
- Seja concisa mas profunda.
- Personalize com perfil, memórias e contexto.
""")

    prompt_final = "\n\n".join(parts)

    # Debug info
    debug_info = {
        "classified": classified,
        "constitution_source": constitution_source,
        "constitution_chars": len(constitution),
        "modules_chars": sum(len(m) for m in modules_content),
        "total_chars": len(prompt_final),
        "total_tokens_estimated": len(prompt_final) // 4,
        "selected_modules": classified["modulos"],
        "flags": classified["flags"],
        "reason": classified["reason"],
        "available_modules": AVAILABLE_MODULES,
        "architecture": "modular_v2",
    }

    return prompt_final, debug_info


@router.post("/message", response_model=schemas.MessageResponse)
async def send_message(
    payload: schemas.MessageCreate,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Envia mensagem e recebe resposta da AYRIA. Consome 1 crédito se onboarding completo."""
    from services.credit_service import consume_credits, InsufficientCreditsError

    # BLOQUEIO: user precisa ter completado onboarding (exceto SUPER_ADMIN)
    if user.role != "SUPER_ADMIN" and user.onboarding_status != "completed":
        raise HTTPException(
            status_code=403,
            detail="Complete o onboarding antes de usar o chat. Redirecione para /onboarding.",
        )

    # CRÉDITOS: consome 1 ANTES de processar (atomicidade)
    # Admin bypass + onboarding incompleto já tratado dentro do consume_credits()
    success, tx = await consume_credits(
        db=db,
        user=user,
        amount=1,
        description=f"Consumo de 1 crédito por mensagem no chat",
        reference_type="chat_message",
        reference_id=None,  # preenchido depois com o message_id
    )
    if not success:
        # Saldo insuficiente — bloqueia com mensagem amigável
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "code": "INSUFFICIENT_CREDITS",
                "message": "Seus créditos acabaram. Em breve você poderá renovar ou mudar seu plano. Enquanto isso, seu perfil e histórico permanecem salvos.",
                "credit_balance": user.credit_balance or 0,
            },
        )
    
    # 1. Pega ou cria chat
    chat_id = payload.chat_id
    if chat_id:
        chat_res = await db.execute(
            select(models.Chat).where(
                models.Chat.id == chat_id,
                models.Chat.user_id == user.id,
            )
        )
        chat = chat_res.scalar_one_or_none()
        if not chat:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
    else:
        # Cria novo chat
        profile_res = await db.execute(
            select(models.UserProfile).where(models.UserProfile.user_id == user.id)
        )
        profile = profile_res.scalar_one_or_none()
        chat = models.Chat(
            id=uuid.uuid4(),
            user_id=user.id,
            title=payload.content[:50] + ("..." if len(payload.content) > 50 else ""),
            context_snapshot={
                "profile_attributes": profile.attributes if profile else {},
                "numerology": user.numerology_data,
            },
        )
        db.add(chat)
        await db.flush()
    
    # 2. Salva mensagem do usuário
    user_msg = models.Message(
        id=uuid.uuid4(),
        chat_id=chat.id,
        user_id=user.id,
        role="user",
        content=payload.content,
        metadata_json={},
    )
    db.add(user_msg)

    # 2.0 SISTEMA 2 — Detecta se a mensagem do user responde uma pergunta pendente
    # Quando user responde no campo de chat normal e a resposta é válida, marca como answered automaticamente
    try:
        from services.onboarding_helper import validar_e_gravar_resposta_chat
        detectou_resposta, attr_code = await validar_e_gravar_resposta_chat(
            db=db,
            user=user,
            user_msg_content=payload.content,
            chat_id=chat.id,  # NOVO v3: registra skip por chat
        )
        if detectou_resposta:
            logger.info(f"✅ Sistema 2: user respondeu pendente '{attr_code}' via chat normal")
    except ImportError:
        pass  # helper não existe ainda, não-bloqueante
    except Exception as e:
        logger.warning(f"Falha ao detectar resposta de pergunta pendente: {e}")

    # 2.1 SUPERVISOR — SÓ regex pré-check (instantâneo, 0 IA)
    #   Análise IA roda em BATCH via cron a cada 5min (script ayria_supervisor_batch.py)
    #   — zero latência no chat, detecção de padrão entre msgs.
    #   Aqui só detectamos sinais de risco e gravamos a análise. O chat
    #   segue respondendo normalmente; quem decide se bloqueia é o ADMIN
    #   na tela de Supervisão. (Regra: nada bloqueia automaticamente.)
    from services.supervisor_service import supervisor_service
    quick_level, quick_score, quick_signals, quick_sublevel = supervisor_service._quick_check(payload.content)
    pre_supervisor = None
    supervisor_signaled = False  # flag pra avisar o frontend que essa msg acionou risco
    if quick_level in ("URGENCIA", "ATENCAO"):
        # Cria análise SYNC pra não perder o sinal caso o batch não rode a tempo
        analysis = models.SupervisorAnalysis(
            message_id=user_msg.id,
            user_id=user.id,
            chat_id=chat.id,
            level=quick_level,
            risk_sublevel=quick_sublevel,
            score=min(0.99, max(0.5, quick_score)),
            reason=(
                "Padrão crítico (N1/N2) detectado por regex pré-checagem"
                if quick_level == "URGENCIA"
                else "Padrão de atenção (N3/ATENCAO) detectado por regex pré-checagem"
            ),
            signals=quick_signals,
            recommended_action=(
                "🔴 Admin revisar com prioridade. Sugestão: CVV 188 + SAMU 192. Bloqueio manual."
                if quick_level == "URGENCIA"
                else "🟡 Admin revisar quando possível."
            ),
            model_used="regex-pre-check",
            analysis_duration_ms=0,
        )
        db.add(analysis)
        try:
            await db.commit()
        except Exception as e:
            logger.error(f"Erro commit análise supervisor: {e}", exc_info=True)
            await db.rollback()
            raise
        await db.refresh(analysis)
        pre_supervisor = analysis
        supervisor_signaled = True
        # Cria alerta pro admin (sem bloquear o chat — só notifica no painel)
        alert_id = None
        try:
            alert = await supervisor_service.create_alert_if_needed(db, pre_supervisor)
            if alert:
                # Acessa direto o id via dict (evita lazy-load)
                try:
                    await db.refresh(alert)
                    alert_id = alert.id
                except Exception as inner_e:
                    # fallback: pega via get() do estado de SQLAlchemy
                    alert_id = alert.id
        except Exception as e:
            logger.warning(f"create_alert falhou: {e}", exc_info=True)
        logger.warning(
            f"🚨 Supervisão sinalizada ({quick_level}) — user={user.email} "
            f"(NÃO bloqueia chat, admin decide na tela de Supervisão)"
        )

        # 🔔 Notificação TELEGRAM em TEMPO REAL pro admin
        # Best-effort via FastAPI BackgroundTasks (roda depois do response, não atrasa o chat)
        try:
            from services.telegram_notifier import send_supervisor_alert
            content_excerpt = (payload.content or "")[:400]
            background_tasks.add_task(
                send_supervisor_alert,
                user_email=user.email,
                level=quick_level,
                signals=list(quick_signals or []),
                content_excerpt=content_excerpt,
                ia_confirmed=False,  # pré-check é sempre False até o batch confirmar
                alert_id=alert_id,
            )
            logger.warning(f"🔔 Telegram notificação agendada (alerta #{alert_id})")
        except Exception as e:
            logger.warning(f"Erro ao agendar notificação Telegram: {e}", exc_info=True)

    # Se algo foi sinalizado pelo supervisor (N1/N2/N3/ATENCAO), segue o chat normal.
    # Quem decide SE bloqueia é o ADMIN no painel de Supervisão.
    # A info fica na metadata da resposta e na lista de alertas.

    # 3. Busca contexto (perfil curado por intent + memórias + RAG com threshold)
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()

    # Detecta intent do user pra curadoria
    from services.context_curator import (
        detect_intent, curate_profile, curate_spiritual_preference,
    )
    detected_intent = detect_intent(payload.content)

    # Profile CURADO (não joga JSON inteiro) — varia por intent
    profile_text = curate_profile(user, profile, intent=detected_intent)

    # Spiritual Preference — só se intent for espiritual OU houver preferencia ativa
    try:
        from sqlalchemy import select as _sa_sel
        sp_res = await db.execute(
            _sa_sel(models.SpiritualPreference).where(
                models.SpiritualPreference.user_id == user.id
            )
        )
        sp = sp_res.scalar_one_or_none()
        if sp and sp.is_active:
            sp_text = curate_spiritual_preference(sp)
            if sp_text:
                profile_text += f"\n\nPREFERÊNCIA ESPIRITUAL: {sp_text}\nRespeite essa orientação ao falar sobre espiritualidade, valores e visão de mundo. NÃO force."
    except Exception as e:
        logger.warning(f"Falha ao carregar preferência de vida: {e}")

    # RAG: busca conhecimento relevante COM THRESHOLD (antes: top 3 sem filtro)
    rag_context = "(nenhum conhecimento específico encontrado)"
    try:
        from services.pdf_processor import PDFProcessor
        pdf_proc = PDFProcessor()
        msg_embedding = await pdf_proc.generate_embedding(payload.content)
        results = await vector_service.search(
            collection="conhecimento_geral",
            query_embedding=msg_embedding,
            limit=2,                # ↓ de 3 → 2
            score_threshold=0.3,    # ↑ de 0.0 → 0.3 (filtra ruído)
        )
        if results:
            rag_context = "\n\n".join([r.get("text", "")[:500] for r in results[:2]])
    except Exception as e:
        logger.warning(f"RAG search falhou: {e}")

    # Memórias recentes COM THRESHOLD + DEDUPE (antes: top 5 sem filtro)
    memories_text = "(nenhuma memória recente)"
    try:
        mem_results = await vector_service.search(
            collection="memoria_episodica",
            query_embedding=msg_embedding,  # mesmo embedding
            user_id=str(user.id),
            limit=4,                # ↓ de 5 → 4 (top 4 deduplicados)
            score_threshold=0.3,    # ↑ de 0.0 → 0.3
        )
        if mem_results:
            # Dedupe por texto (mesma memória não aparece 2x)
            seen = set()
            unique = []
            for r in mem_results:
                txt = (r.get("text", "") or "").strip()
                # Heurística simples: dedupe pelos primeiros 100 chars
                key = txt[:100].lower()
                if key and key not in seen:
                    seen.add(key)
                    unique.append(r)
                if len(unique) >= 3:  # máx 3 após dedupe
                    break
            if unique:
                memories_text = "\n".join([f"- {r.get('text', '')[:300]}" for r in unique])
    except Exception as e:
        logger.warning(f"Memory search falhou: {e}")

    # 3.7 SISTEMA 2 v3 — Perguntas pendentes pra perguntar no chat atual
    # Regra nova (Rafael 17:58):
    # 1. Pergunta pendentes que AINDA NÃO FORAM PERGUNTADAS neste chat (ou que user respondeu)
    # 2. Se user disse "não quero responder" neste chat → NÃO pergunta (skip por chat)
    # 3. Em chat novo → todos os skips resetam (vai perguntar de novo)
    pending_questions_text = ""
    pending_attr_code = None  # pro frontend exibir o banner
    pending_question_label = None  # label do atributo (usado no fundo amarelo da UI)
    try:
        from datetime import timedelta as _td
        now = datetime.utcnow()
        # Busca perguntas pendentes que NÃO FORAM SKIPADAS neste chat
        skip_res = await db.execute(
            select(models.ChatQuestionSkip.attribute_code).where(
                models.ChatQuestionSkip.chat_id == chat.id
            )
        )
        skipped_this_chat = {row[0] for row in skip_res.all()}
        
        # Busca perguntas pendentes OU snoozed que expiraram (até 5, depois filtra)
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
            .limit(5)  # pega até 5 candidatas, filtra em Python pelos skipped do chat
        )
        pending_rows = pending_res.all()
        # Filtra as skipadas neste chat
        pending_row = None
        for r in pending_rows:
            if r[1].code not in skipped_this_chat:
                pending_row = r
                break
        if pending_row:
            ua, attr_def = pending_row
            pending_attr_code = attr_def.code
            # Pega o texto da pergunta do OnboardingConfig (é o que o user viu no onboarding)
            # Fallback: label do attribute_definition
            q_text_res = await db.execute(
                select(models.OnboardingConfig.question_text, models.OnboardingConfig.helper_text).where(
                    models.OnboardingConfig.attribute_code == attr_def.code,
                    models.OnboardingConfig.is_active == True,
                ).limit(1)
            )
            q_row = q_text_res.first()
            question_text = q_row[0] if q_row else attr_def.label
            helper_text = q_row[1] if q_row else None
            # Salva o label pra marcação da mensagem (COR AMARELA na UI)
            pending_question_label = attr_def.label
            
            pending_questions_text = (
                f"\n\n[SISTEMA 2 — PERGUNTA PENDENTE QUE VOCÊ DEVE FAZER AGORA]\n"
                f"Atributo pendente: {attr_def.code}\n"
                f"Texto EXATO da pergunta que o usuário precisa responder:\n"
                f"\"\"\"\n{question_text}\n\"\"\"\n"
                f"{f'(Dica de formato: {helper_text})' if helper_text else ''}\n"
                f"REGRA RÍGIDA: Você DEVE fazer essa pergunta EXATAMENTE como está acima "
                f"(ou bem próximo, mantendo o sentido), de forma NATURAL e SIMPÁTICA na sua PRIMEIRA "
                f"resposta ao usuário nesta conversa.\n\n"
                f"- Faça a pergunta no fluxo NORMAL do chat — o usuário responde no MESMO campo de mensagem.\n"
                f"- NÃO crie banner separado, NÃO crie tela separada. TUDO via chat.\n"
                f"- Se o usuário fizer OUTRA pergunta antes (ex: 'qual meu signo?'), "
                f"responda normalmente, mas DEPOIS lembre gentilmente da pergunta pendente.\n"
                f"- NÃO invente outras perguntas. NÃO pergunte coisas que o usuário não respondeu. "
                f"Use APENAS a pergunta acima.\n"
                f"- Se o usuário disser 'pula' / 'agora não' / 'depois' / 'continuar' — "
                f"seja gentil, reconheça a escolha, e siga a conversa. O sistema cuida do registro.\n"
                f"- NUNCA force o usuário a responder antes de continuar.\n"
                f"- Quando o usuário responder de forma válida, PARABENIZE brevemente e siga a conversa "
                f"(o backend detecta e grava automaticamente — você só precisa elogiar/continuar).\n"
            )
            # Marca como pending_current_chat (em uso agora)
            ua.status = 'pending_current_chat'
            ua.last_asked_at = now
            await db.flush()
    except Exception as e:
        logger.warning(f"Pending questions fetch falhou: {e}")

    # 3.5 SUPERVISOR — já checado no patch 2.1 (linha ~527). Aqui apenas reflete a flag no prompt,
    # caso a URGÊNCIA não tenha sido bloqueada pelo pré-check do patch 2.1
    # (cenário raro: regex não pegou mas o conteúdo é crítico).
    # Se chegou aqui é porque o pré-check não bloqueou — supervisor IA roda a cada 5min via cron.
    supervisor_pre_flag = ""
    
    # 4. Monta system prompt DINAMICAMENTE (arquitetura cognitiva modular)
    system_prompt, prompt_debug_info = await montar_system_prompt(
        db=db,
        user_message=payload.content,
        user=user,
        profile_text=profile_text,
        rag_context=rag_context,
        memories_text=memories_text,
        supervisor_pre_flag=supervisor_pre_flag,
        pending_questions_text=pending_questions_text,
        history=None,  # histórico ainda não foi montado nessa fase; classificador não precisa dele
    )
    logger.info(
        f"Prompt modular montado | mods={prompt_debug_info['selected_modules']} | "
        f"chars={prompt_debug_info['total_chars']} | "
        f"flags={prompt_debug_info['flags']}"
    )
    
    # 5. Histórico recente (últimas 10 mensagens)
    history_res = await db.execute(
        select(models.Message)
        .where(models.Message.chat_id == chat.id)
        .order_by(models.Message.created_at.desc())
        .limit(7)  # 6 msgs + a atual
    )
    history_msgs = list(reversed(history_res.scalars().all()))
    messages_for_ai = [
        {"role": m.role, "content": m.content} for m in history_msgs[:-1]  # exclui a msg atual
    ]
    messages_for_ai.append({"role": "user", "content": payload.content})
    
    # 6. Chama IA
    try:
        response = await ai_service.chat(
            messages=messages_for_ai,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000,
        )

        ai_content = response.choices[0].message.content
        ai_model = response.model
        tokens_used = response.usage.total_tokens if response.usage else None

        # Sanitiza: separa thinking se AI vazar (regex simples)
        ai_content_clean, ai_thinking = _split_thinking(ai_content)
        if ai_thinking:
            logger.info(f"AI vazou thinking (será ocultado de users): {ai_thinking[:200]}...")

        # SANITIZE: remove caracteres CJK/asiáticos que o MiniMax às vezes mistura em PT-BR
        # (Ex: 資源, こんにちは, 仕事 — já aconteceu em produção)
        from services.text_sanitizer import sanitize_response
        ai_content_clean, sanitize_stats = sanitize_response(
            ai_content_clean, source=f"chat:{user.email}"
        )
    except Exception as e:
        logger.error(f"Erro chamando IA: {e}")
        raise HTTPException(status_code=503, detail=f"Erro no motor de IA: {str(e)}")
    
    # 7. Salva resposta
    # === DEBUG / TRANSPARÊNCIA ADMIN ===
    # Salva no metadata tudo que o admin precisa pra auditar e editar o prompt depois:
    # - system_prompt_used: o template completo enviado pra IA (com placeholders preenchidos)
    # - messages_sent_to_ai: lista de mensagens que foram pra IA (system + history + user)
    # - interpreted_context: resumo do que foi interpretado (perfil, numerologia, RAG top, memórias)
    # - tokens_estimate_input: estimativa de tokens do input
    debug_messages_sent = [
        {"role": "system", "content": system_prompt},
    ] + messages_for_ai

    # Extrai só os títulos das memórias e RAG pra um resumo legível
    interpreted_summary = {
        "user_question": payload.content,
        "profile_used": bool(profile_text != "Não disponível"),
        "profile_preview": profile_text[:200] + ("..." if len(profile_text) > 200 else ""),
        "rag_used": bool(rag_context and rag_context != "Nenhum conhecimento relevante encontrado."),
        "rag_preview": rag_context[:200] + ("..." if rag_context and len(rag_context) > 200 else ""),
        "memories_count": len([m for m in (memories_text or "").split("\n") if m.strip().startswith("-")]) if memories_text else 0,
        "memories_preview": memories_text[:200] + ("..." if memories_text and len(memories_text) > 200 else ""),
        "supervisor_quick_level": quick_level or "NORMAL",
        "supervisor_quick_score": float(quick_score) if quick_score is not None else 0.0,
        "history_messages_count": len(messages_for_ai) - 1,  # menos o system
        "pending_questions_count": pending_questions_text.count("PENDENTE") if pending_questions_text else 0,
    }

    # Estimativa simples de tokens (chars / 4 é heurística comum)
    total_chars_input = sum(len(m.get("content", "")) for m in debug_messages_sent)
    tokens_input_estimated = total_chars_input // 4

    ai_msg = models.Message(
        id=uuid.uuid4(),
        chat_id=chat.id,
        user_id=user.id,
        role="assistant",
        content=ai_content_clean,
        ai_model=ai_model,
        tokens_used=tokens_used,
        # IMPORTANTE: o atributo ORM é `metadata_json` (a coluna SQL se chama `metadata`).
        # Passar `metadata={...}` é IGNORADO pelo SQLAlchemy.
        metadata_json={
            "profile_used": bool(profile_text != "Não disponível"),
            "thinking": ai_thinking if user.role in ("admin", "SUPER_ADMIN") else None,
            "is_admin_message": user.role in ("admin", "SUPER_ADMIN"),
            # Sistema 2: marca que essa msg é uma pergunta de onboarding pendente
            "is_pending_question": bool(pending_attr_code),
            "pending_attr_code": pending_attr_code,
            "pending_attr_label": pending_question_label,
            # === DEBUG / AUDITORIA ADMIN ===
            "system_prompt_used": system_prompt,
            "messages_sent_to_ai": debug_messages_sent,
            "interpreted_context": interpreted_summary,
            "tokens_input_estimated": tokens_input_estimated,
            "tokens_output": tokens_used,
            "model_used": ai_model,
            # === ARQUITETURA MODULAR V2 ===
            "prompt_architecture": "modular_v2",
            "selected_modules": prompt_debug_info["selected_modules"],
            "prompt_flags": prompt_debug_info["flags"],
            "prompt_reason": prompt_debug_info["reason"],
            "constitution_source": prompt_debug_info["constitution_source"],
            "available_modules": prompt_debug_info["available_modules"],
            # === SANITIZER (anti CJK misturado em PT-BR) ===
            "sanitized": sanitize_stats["sanitized"],
            "sanitize_removed_count": sanitize_stats["removed_count"],
            "sanitize_removed_chars_sample": sanitize_stats["removed_chars_sample"],
            "sanitize_removed_categories": sanitize_stats["removed_categories"],
        },
    )
    db.add(ai_msg)
    
    # Atualiza last_message_at do chat
    chat.last_message_at = datetime.utcnow()

    # Preenche reference_id do transaction (se houve consumo) com o message_id
    if tx is not None:
        tx.reference_id = str(ai_msg.id)

    await db.commit()
    await db.refresh(ai_msg)

    # 8. Background: extrair fatos importantes pra memória_episodica
    background_tasks.add_task(
        extract_memories_background,
        user_id=str(user.id),
        user_message=payload.content,
        ai_response=ai_content,
    )
    
    # Monta response com dados de créditos (se houve consumo, retorna saldo atualizado)
    msg_data = {
        "id": ai_msg.id,
        "chat_id": ai_msg.chat_id,
        "role": ai_msg.role,
        "content": ai_msg.content,
        "ai_model": ai_msg.ai_model,
        "tokens_used": ai_msg.tokens_used,
        "created_at": ai_msg.created_at,
        "metadata": {
            **(ai_msg.metadata_json or {}),
            # === SUPERVISOR ===
            # Marca pro frontend que essa msg foi sinalizada pra supervisão.
            # O chat NÃO foi bloqueado — admin decide na tela de Supervisão.
            "supervisor_signaled": supervisor_signaled,
            "supervisor_level": pre_supervisor.level if supervisor_signaled else None,
            "supervisor_signals": pre_supervisor.signals if supervisor_signaled else [],
            "supervisor_block": False,
        },
        "credit_balance": user.credit_balance if tx is not None else None,
        "credit_consumed": 1 if tx is not None else 0,
        "credit_blocked": False,
    }
    return schemas.MessageResponse(**msg_data)


async def extract_memories_background(user_id: str, user_message: str, ai_response: str):
    """Extrai fatos importantes da conversa e salva em memoria_episodica"""
    try:
        # Em prod: usar IA pra extrair fatos
        # Aqui: salva heurística simples
        if any(kw in user_message.lower() for kw in ["meu nome", "me chamo", "sou ", "trabalho", "gosto de", "odeio", "meu objetivo"]):
            # Gera embedding real (MiniMax ou fallback hash)
            from services.pdf_processor import PDFProcessor
            pdf_proc = PDFProcessor()
            fact_embedding = await pdf_proc.generate_embedding(user_message[:500])
            await vector_service.upsert(
                collection="memoria_episodica",
                text=user_message[:500],
                embedding=fact_embedding,
                payload={
                    "user_id": user_id,
                    "type": "user_fact",
                    "extracted_at": datetime.utcnow().isoformat(),
                },
            )
    except Exception as e:
        logger.error(f"Erro extraindo memórias: {e}")


# ============================================================
# SUPERVISOR — análise de risco em background
# ============================================================
async def supervisor_analyze_background(message_id: str, chat_id: str, user_id: str):
    """
    Roda em BackgroundTasks. Analisa a mensagem do user quanto a risco psicossocial.
    Cria SupervisorAnalysis + SupervisorAlert (se necessário).
    Atualiza daily_summary.
    """
    from services.supervisor_service import supervisor_service
    from database import AsyncSessionLocal
    from datetime import date

    try:
        async with AsyncSessionLocal() as db:
            # Carrega mensagem + user + chat
            msg_res = await db.execute(
                select(models.Message).where(models.Message.id == uuid.UUID(message_id))
            )
            message = msg_res.scalar_one_or_none()
            if not message:
                logger.warning(f"supervisor: msg {message_id} não encontrada")
                return

            chat_res = await db.execute(
                select(models.Chat).where(models.Chat.id == uuid.UUID(chat_id))
            )
            chat = chat_res.scalar_one_or_none()

            user_res = await db.execute(
                select(models.User).where(models.User.id == uuid.UUID(user_id))
            )
            user = user_res.scalar_one_or_none()

            if not chat or not user:
                return

            # Analisa
            analysis = await supervisor_service.analyze_message(db, message, chat, user)

            # Cria alerta se for ATENCAO/URGENCIA
            await supervisor_service.create_alert_if_needed(db, analysis)

            # Atualiza daily_summary
            today = date.today()
            ds_res = await db.execute(
                select(models.SupervisorDailySummary).where(
                    models.SupervisorDailySummary.user_id == user.id,
                    models.SupervisorDailySummary.summary_date == today,
                )
            )
            ds = ds_res.scalar_one_or_none()
            if not ds:
                ds = models.SupervisorDailySummary(
                    user_id=user.id,
                    summary_date=today,
                    total_messages=0,
                    normal_count=0,
                    atencao_count=0,
                    urgencia_count=0,
                    current_level="NORMAL",
                    max_score=0.0,
                )
                db.add(ds)

            ds.total_messages = (ds.total_messages or 0) + 1
            if analysis.level == "NORMAL":
                ds.normal_count = (ds.normal_count or 0) + 1
            elif analysis.level == "ATENCAO":
                ds.atencao_count = (ds.atencao_count or 0) + 1
            else:  # URGENCIA
                ds.urgencia_count = (ds.urgencia_count or 0) + 1

            # current_level = pior do dia
            if analysis.level == "URGENCIA":
                ds.current_level = "URGENCIA"
            elif analysis.level == "ATENCAO" and ds.current_level != "URGENCIA":
                ds.current_level = "ATENCAO"
            ds.max_score = max(float(ds.max_score or 0), float(analysis.score))
            await db.commit()

            logger.info(
                f"📊 Supervisor: user={user.email} level={analysis.level} "
                f"score={analysis.score:.2f} dur={analysis.analysis_duration_ms}ms"
            )
    except Exception as e:
        logger.error(f"❌ Erro no supervisor_analyze_background: {e}", exc_info=True)
