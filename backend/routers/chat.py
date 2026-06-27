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
import models
import schemas

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger(__name__)


SYSTEM_PROMPT_TEMPLATE = """Você é AYRIA, uma assistente de IA especializada em autoconhecimento, psicologia e numerologia.

IDENTIDADE:
- Seu nome é AYRIA
- Tom: acolhedor, sábio, profundo mas acessível
- Objetivo: ajudar o usuário a se conhecer melhor através de conversas significativas
- Use a base de conhecimento numerológico e psicológico quando relevante

PERFIL DO USUÁRIO:
{user_profile}

CONHECIMENTO RELEVANTE (RAG):
{rag_context}

MEMÓRIAS RECENTES:
{memories}

INSTRUÇÕES:
- Personalize respostas com base no perfil e nas memórias
- Quando relevante, conecte com numerologia ou psicologia
- Seja conciso mas profundo
- Faça perguntas de acompanhamento quando apropriado
- Use markdown para formatar (negrito, listas) quando ajudar"""


@router.post("/message", response_model=schemas.MessageResponse)
async def send_message(
    payload: schemas.MessageCreate,
    background_tasks: BackgroundTasks,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Envia mensagem e recebe resposta da AYRIA"""
    
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
        metadata={},
    )
    db.add(user_msg)
    
    # 3. Busca contexto (perfil + memórias + RAG)
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    
    # Monta perfil resumido
    profile_text = "Não disponível"
    if profile and profile.attributes:
        attrs = profile.attributes
        profile_parts = []
        for k, v in attrs.items():
            profile_parts.append(f"- {k}: {v}")
        profile_text = "\n".join(profile_parts)

    if user.numerology_data:
        # Usa relatório narrativo ao invés de JSON cru (mais legível pra IA)
        relatorio = gerar_relatorio_numerologico(user.numerology_data)
        profile_text += f"\n\nMAPA NUMEROLÓGICO CALCULADO:\n{relatorio}"
    
    # RAG: busca conhecimento relevante
    rag_context = "(nenhum conhecimento específico encontrado)"
    try:
        # Embedding da mensagem do usuário (placeholder - em prod usar text-embedding-3-small)
        # Vou usar busca por texto simples como fallback
        results = await vector_service.search(
            collection="conhecimento_geral",
            query_embedding=[0.0] * 1536,  # placeholder, ideal seria embedding real
            limit=3,
            score_threshold=0.0,  # aceita qualquer score no MVP
        )
        if results:
            rag_context = "\n\n".join([r.get("text", "")[:500] for r in results[:3]])
    except Exception as e:
        logger.warning(f"RAG search falhou: {e}")
    
    # Memórias recentes
    memories_text = "(nenhuma memória recente)"
    try:
        mem_results = await vector_service.search(
            collection="memoria_episodica",
            query_embedding=[0.0] * 1536,
            user_id=str(user.id),
            limit=5,
            score_threshold=0.0,
        )
        if mem_results:
            memories_text = "\n".join([f"- {r.get('text', '')}" for r in mem_results])
    except Exception as e:
        logger.warning(f"Memory search falhou: {e}")
    
    # 4. Monta system prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        user_profile=profile_text,
        rag_context=rag_context,
        memories=memories_text,
    )
    
    # 5. Histórico recente (últimas 10 mensagens)
    history_res = await db.execute(
        select(models.Message)
        .where(models.Message.chat_id == chat.id)
        .order_by(models.Message.created_at.desc())
        .limit(11)
    )
    history_msgs = list(reversed(history_res.scalars().all()))
    messages_for_ai = [
        {"role": m.role, "content": m.content} for m in history_msgs[:-1]  # exclui a msg atual (acabamos de salvar)
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
    except Exception as e:
        logger.error(f"Erro chamando IA: {e}")
        raise HTTPException(status_code=503, detail=f"Erro no motor de IA: {str(e)}")
    
    # 7. Salva resposta
    ai_msg = models.Message(
        id=uuid.uuid4(),
        chat_id=chat.id,
        user_id=user.id,
        role="assistant",
        content=ai_content,
        ai_model=ai_model,
        tokens_used=tokens_used,
        metadata={"profile_used": bool(profile_text != "Não disponível")},
    )
    db.add(ai_msg)
    
    # Atualiza last_message_at do chat
    chat.last_message_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(ai_msg)
    
    # 8. Background: extrair fatos importantes pra memória_episodica
    background_tasks.add_task(
        extract_memories_background,
        user_id=str(user.id),
        user_message=payload.content,
        ai_response=ai_content,
    )
    
    return schemas.MessageResponse.model_validate(ai_msg)


async def extract_memories_background(user_id: str, user_message: str, ai_response: str):
    """Extrai fatos importantes da conversa e salva em memoria_episodica"""
    try:
        # Em prod: usar IA pra extrair fatos
        # Aqui: salva heurística simples
        if any(kw in user_message.lower() for kw in ["meu nome", "me chamo", "sou ", "trabalho", "gosto de", "odeio", "meu objetivo"]):
            # Salva na memoria_episodica (embedding placeholder)
            await vector_service.upsert(
                collection="memoria_episodica",
                text=user_message[:500],
                embedding=[0.0] * 1536,  # placeholder
                payload={
                    "user_id": user_id,
                    "type": "user_fact",
                    "extracted_at": datetime.utcnow().isoformat(),
                },
            )
    except Exception as e:
        logger.error(f"Erro extraindo memórias: {e}")
