"""
AYRIA - Chats Router
GET  /api/chats
POST /api/chats
GET  /api/chats/{chat_id}/messages
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
import uuid

from database import get_db
from utils.security import get_current_user
import models
import schemas

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("", response_model=list[schemas.ChatResponse])
async def list_chats(
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista conversas do usuário"""
    res = await db.execute(
        select(models.Chat)
        .where(models.Chat.user_id == user.id, models.Chat.is_archived == False)
        .order_by(desc(models.Chat.last_message_at))
    )
    chats = res.scalars().all()
    
    # Conta mensagens por chat
    result = []
    for chat in chats:
        count_res = await db.execute(
            select(func.count(models.Message.id)).where(models.Message.chat_id == chat.id)
        )
        count = count_res.scalar() or 0
        result.append(schemas.ChatResponse(
            id=chat.id,
            user_id=chat.user_id,
            title=chat.title,
            summary=chat.summary,
            created_at=chat.created_at,
            last_message_at=chat.last_message_at,
            message_count=count,
        ))
    return result


@router.post("", response_model=schemas.ChatResponse, status_code=201)
async def create_chat(
    payload: schemas.ChatCreate,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria nova conversa"""
    # Pega snapshot do perfil
    profile_res = await db.execute(
        select(models.UserProfile).where(models.UserProfile.user_id == user.id)
    )
    profile = profile_res.scalar_one_or_none()
    
    chat = models.Chat(
        id=uuid.uuid4(),
        user_id=user.id,
        title=payload.title or "Nova conversa",
        context_snapshot={
            "profile_attributes": profile.attributes if profile else {},
            "numerology": user.numerology_data,
        },
        is_archived=False,
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)
    
    return schemas.ChatResponse(
        id=chat.id, user_id=chat.user_id, title=chat.title,
        summary=chat.summary, created_at=chat.created_at,
        last_message_at=chat.last_message_at, message_count=0,
    )


@router.get("/{chat_id}/messages", response_model=list[schemas.MessageResponse])
async def list_messages(
    chat_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista mensagens de um chat"""
    # Verifica ownership
    chat_res = await db.execute(
        select(models.Chat).where(
            models.Chat.id == chat_id,
            models.Chat.user_id == user.id,
        )
    )
    chat = chat_res.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    res = await db.execute(
        select(models.Message)
        .where(models.Message.chat_id == chat_id)
        .order_by(models.Message.created_at)
    )
    messages = res.scalars().all()
    return [schemas.MessageResponse.model_validate(m) for m in messages]


@router.delete("/{chat_id}", status_code=204)
async def delete_chat(
    chat_id: uuid.UUID,
    user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deleta conversa"""
    res = await db.execute(
        select(models.Chat).where(
            models.Chat.id == chat_id,
            models.Chat.user_id == user.id,
        )
    )
    chat = res.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Conversa não encontrada")
    
    await db.delete(chat)
    await db.commit()
    return None
