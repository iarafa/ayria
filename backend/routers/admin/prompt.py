"""
admin/prompt.py — System prompt (constituição + módulos) + RAG + prompt chat

Endpoints:
  GET    /prompt/modules/available      → lista módulos .md disponíveis
  GET    /prompt/system                 → constituição ativa + módulos customizados
  PUT    /prompt/system                 → salva constituição OU módulo
  POST   /prompt/system/restore-default → restaura padrão
  DELETE /prompt/module/{module_key}    → remove módulo (banco + arquivo + RAG)
  GET    /prompt/rag/status             → status da indexação RAG
  POST   /prompt/rag/index              → indexa/reindexa prompts no Qdrant
  POST   /prompt/rag/delete             → remove fonte do Qdrant
  POST   /prompt/chat                   → admin conversa COM contexto do MD
  POST   /prompt/chat/save              → salva MD atualizado sugerido pelo chat
"""
from ._base import (
    APIRouter, Depends, HTTPException,
    select, _upd,
    BaseModel,
    uuid, logging, datetime, shutil, Path, Optional, _time,
    get_db, require_admin,
    models, schemas,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])

from services.prompt_selector import (
    AVAILABLE_MODULES,
    load_constitution as _load_constitution_default,
    load_modules as _load_module_content_default,
    PROMPTS_DIR,
)


@router.get("/prompt/modules/available", response_model=dict)
async def list_available_modules(admin=Depends(require_admin)):
    """Lista módulos .md disponíveis no filesystem."""
    modulos_info = []
    for key in AVAILABLE_MODULES:
        p = Path(__file__).parent.parent.parent / "prompts" / f"prompt_{key}.md"
        preview = ""
        if p.exists():
            content = p.read_text(encoding="utf-8")
            preview = content[:200]
        modulos_info.append({
            "key": key,
            "default_preview": preview,
        })
    return {
        "available_modules": AVAILABLE_MODULES,
        "count": len(AVAILABLE_MODULES),
        "modules": modulos_info,
        "constitution_preview": _load_constitution_default()[:300] if _load_constitution_default() else "",
    }


@router.get("/prompt/system", response_model=dict)
async def get_prompt_system(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Retorna a constituição ativa + módulos ativos customizados."""
    res = await db.execute(
        select(models.AyriaPromptConfig).where(
            models.AyriaPromptConfig.is_active == True,
            models.AyriaPromptConfig.key == "constituicao_base",
        )
    )
    cfg_constitution = res.scalar_one_or_none()

    res_mod = await db.execute(
        select(models.AyriaPromptConfig).where(
            models.AyriaPromptConfig.is_active == True,
            models.AyriaPromptConfig.key.like("modulo_%"),
        )
    )
    modulos_db = res_mod.scalars().all()

    return {
        "active": {
            "key": "constituicao_base",
            "content": cfg_constitution.content if cfg_constitution else _load_constitution_default(),
            "description": cfg_constitution.description if cfg_constitution else "Constituição padrão (hardcoded — fallback)",
            "updated_at": cfg_constitution.updated_at.isoformat() if cfg_constitution else None,
            "is_custom": cfg_constitution is not None,
        },
        "default_template": _load_constitution_default(),
        "modulos_customizados": [
            {
                "key": m.key,
                "short_key": m.key.replace("modulo_", "", 1),
                "content": m.content,
                "description": m.description,
                "updated_at": m.updated_at.isoformat(),
                "is_custom": True,
            }
            for m in modulos_db
        ],
        "available_modules": AVAILABLE_MODULES,
    }


@router.put("/prompt/system", response_model=dict)
async def update_prompt_system(
    payload: dict,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Salva constituição OU módulo."""
    content = payload.get("content", "").strip()
    description = payload.get("description", "").strip() or None
    key = payload.get("key", "constituicao_base").strip()

    if not content:
        raise HTTPException(status_code=400, detail="content não pode ser vazio")

    if key == "constituicao_base":
        pass
    elif key.startswith("modulo_"):
        short = key.replace("modulo_", "", 1)
        if not short.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=400,
                detail=f"Nome de módulo inválido: '{short}'.",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"key inválida. Use 'constituicao_base' ou 'modulo_<nome>'.",
        )

    await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(models.AyriaPromptConfig.key == key, models.AyriaPromptConfig.is_active == True)
        .values(is_active=False)
    )

    new_cfg = models.AyriaPromptConfig(
        id=uuid.uuid4(),
        key=key,
        content=content,
        is_active=True,
        description=description,
        updated_by=admin.id,
    )
    db.add(new_cfg)
    await db.commit()
    await db.refresh(new_cfg)

    if key.startswith("modulo_"):
        md_path = PROMPTS_DIR / f"prompt_{key.replace('modulo_', '', 1)}.md"
        if not md_path.exists():
            md_path.write_text(content, encoding="utf-8")
            logger.info(f"📄 Novo módulo criado em disco: {md_path}")

    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "id": str(new_cfg.id),
        "key": new_cfg.key,
        "is_active": new_cfg.is_active,
        "updated_at": new_cfg.updated_at.isoformat(),
    }


@router.post("/prompt/system/restore-default", response_model=dict)
async def restore_default_prompt(
    payload: dict | None = None,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Restaura padrão. Se payload.key fornecido, restaura só aquele; senão todos."""
    payload = payload or {}
    target_key = payload.get("key")

    if target_key:
        if target_key not in ["constituicao_base"] + [f"modulo_{m}" for m in AVAILABLE_MODULES]:
            raise HTTPException(status_code=400, detail=f"key inválida: {target_key}")
        res = await db.execute(
            _upd(models.AyriaPromptConfig)
            .where(models.AyriaPromptConfig.key == target_key, models.AyriaPromptConfig.is_active == True)
            .values(is_active=False)
        )
        msg = f"'{target_key}' restaurado pro padrão."
    else:
        res = await db.execute(
            _upd(models.AyriaPromptConfig).where(models.AyriaPromptConfig.is_active == True)
            .values(is_active=False)
        )
        msg = "Todos os prompts customizados desativados."

    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "deactivated": res.rowcount or 0,
        "message": msg,
    }


@router.delete("/prompt/module/{module_key:path}", response_model=dict)
async def delete_module(
    module_key: str,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Remove um módulo temático do sistema."""
    full_key = f"modulo_{module_key}"

    if not module_key.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail=f"Nome inválido: '{module_key}'.",
        )

    file_path = PROMPTS_DIR / f"prompt_{module_key}.md"

    deactivated = 0
    try:
        res = await db.execute(
            _upd(models.AyriaPromptConfig)
            .where(models.AyriaPromptConfig.key == full_key, models.AyriaPromptConfig.is_active == True)
            .values(is_active=False)
        )
        deactivated = res.rowcount or 0
        await db.commit()
    except Exception as e:
        logger.warning(f"Erro ao desativar config: {e}")

    file_removed = False
    backup_path = None
    if file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".deleted")
        try:
            shutil.copy2(file_path, backup_path)
            file_path.unlink()
            file_removed = True
            logger.info(f"🗑️ Módulo removido: {file_path}")
        except Exception as e:
            logger.error(f"Erro ao remover arquivo {file_path}: {e}")

    rag_deleted = False
    try:
        from services.prompt_indexer import delete_prompt_source
        await delete_prompt_source(f"prompt_{module_key}")
        rag_deleted = True
    except Exception as e:
        logger.warning(f"Erro ao remover do RAG: {e}")

    if module_key in AVAILABLE_MODULES:
        AVAILABLE_MODULES.remove(module_key)

    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    try:
        AVAILABLE_MODULES.clear()
        AVAILABLE_MODULES.extend(sorted([
            p.stem.replace("prompt_", "")
            for p in PROMPTS_DIR.glob("prompt_*.md")
        ]))
        AVAILABLE_MODULES[:] = [m for m in AVAILABLE_MODULES if m != "base"]
    except Exception:
        pass

    return {
        "ok": True,
        "module_key": module_key,
        "full_key": full_key,
        "deactivated_configs": deactivated,
        "file_removed": file_removed,
        "backup_path": str(backup_path) if backup_path else None,
        "rag_cleared": rag_deleted,
        "available_modules_after": AVAILABLE_MODULES,
    }


# ============================================================
# RAG
# ============================================================
@router.get("/prompt/rag/status", response_model=dict)
async def prompt_rag_status(admin=Depends(require_admin)):
    """Status da indexação RAG dos .md de prompt."""
    from services.prompt_indexer import list_indexed_prompts, PROMPTS_DIR

    files = sorted([f.name for f in PROMPTS_DIR.glob("*.md")])
    indexed = await list_indexed_prompts()
    indexed_sources = {d["source"] for d in indexed}

    return {
        "files_on_disk": files,
        "files_count": len(files),
        "indexed_count": len(indexed),
        "missing_index": [f for f in files if f.replace(".md", "") not in indexed_sources],
        "indexed_docs": indexed,
    }


@router.post("/prompt/rag/index", response_model=dict)
async def prompt_rag_index(
    payload: dict | None = None,
    admin=Depends(require_admin),
):
    """Indexa/reindexa os .md de prompt no Qdrant."""
    from services.prompt_indexer import index_all_prompts, delete_prompt_source, PROMPTS_DIR

    payload = payload or {}
    source = payload.get("source")
    recreate = payload.get("recreate", bool(source))

    logger.info(f"🔄 Reindex RAG: source={source!r}, recreate={recreate}")

    try:
        if source:
            from services.prompt_indexer import _index_single
            p = PROMPTS_DIR / f"{source}.md"
            if not p.exists():
                raise HTTPException(status_code=404, detail=f"Arquivo {source}.md não existe.")
            deleted = await delete_prompt_source(source)
            result = await _index_single(p)
            return {"ok": True, "source": source, "deleted": deleted, **result}
        result = await index_all_prompts(recreate=bool(recreate))
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Reindex RAG falhou: source={source!r}")
        raise HTTPException(status_code=500, detail=f"Erro ao reindexar: {type(e).__name__}: {e}")


@router.post("/prompt/rag/delete", response_model=dict)
async def prompt_rag_delete(
    payload: dict,
    admin=Depends(require_admin),
):
    """Remove uma fonte do Qdrant."""
    from services.prompt_indexer import delete_prompt_source

    source = payload.get("source", "").strip()
    if not source:
        raise HTTPException(status_code=400, detail="source obrigatório")

    deleted = await delete_prompt_source(source)
    return {"ok": True, "deleted": deleted, "source": source}


# ============================================================
# PROMPT CHAT
# ============================================================
SUPERVISOR_PROMPT_KEY = "supervisor_seguranca_crise"
SUPERVISOR_PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "supervisor" / "seguranca_crise.md"


def _split_thinking_for_admin(content: str) -> tuple:
    """Wrapper de routers.chat._split_thinking pra evitar duplicação."""
    try:
        from routers.chat import _split_thinking
        return _split_thinking(content)
    except Exception:
        return content, None


class PromptChatRequest(BaseModel):
    key: str
    user_message: str
    history: Optional[list] = []
    initial_context: Optional[str] = None


class PromptChatSaveRequest(BaseModel):
    key: str
    new_content: str
    reindex_rag: bool = True


@router.post("/prompt/chat", response_model=dict)
async def prompt_chat(
    payload: PromptChatRequest,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Admin conversa COM contexto de um MD específico."""
    from services.ai_service import ai_service

    key = payload.key.strip()

    current_content = None
    if payload.initial_context:
        current_content = payload.initial_context
    if key == "constituicao_base":
        res = await db.execute(
            select(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.key == "constituicao_base",
                models.AyriaPromptConfig.is_active == True,
            )
        )
        cfg = res.scalar_one_or_none()
        if cfg:
            current_content = cfg.content
        else:
            md_path = PROMPTS_DIR / "prompt_base.md"
            if md_path.exists():
                current_content = md_path.read_text(encoding="utf-8")
    elif key.startswith("modulo_"):
        short = key.replace("modulo_", "", 1)
        res = await db.execute(
            select(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.key == key,
                models.AyriaPromptConfig.is_active == True,
            )
        )
        cfg = res.scalar_one_or_none()
        if cfg:
            current_content = cfg.content
        else:
            md_path = PROMPTS_DIR / f"prompt_{short}.md"
            if md_path.exists():
                current_content = md_path.read_text(encoding="utf-8")
    elif key == SUPERVISOR_PROMPT_KEY:
        res = await db.execute(
            select(models.AyriaPromptConfig).where(
                models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
                models.AyriaPromptConfig.is_active == True,
            )
        )
        cfg = res.scalar_one_or_none()
        if cfg:
            current_content = cfg.content
        else:
            if SUPERVISOR_PROMPT_FILE.exists():
                current_content = SUPERVISOR_PROMPT_FILE.read_text(encoding="utf-8")
    else:
        raise HTTPException(status_code=400, detail=f"key inválida: {key}")

    if not current_content:
        raise HTTPException(status_code=404, detail=f"Conteúdo não encontrado para '{key}'")

    from services.prompt_relationships import (
        build_architecture_map,
        get_summary_of_siblings,
    )

    architecture_map = build_architecture_map(key)
    sibling_summary = get_summary_of_siblings(key, max_chars=1500)

    system_prompt = f"""Você é o co-editor do Rafael (admin) sobre um prompt do sistema AYRIA.

**Contexto**: O admin está editando o arquivo/prompt de key `{key}`.

---

{architecture_map}

---

**Conteúdo ATUAL do prompt `{key}`**:
```markdown
{current_content}
```

---

{sibling_summary}

---

**Suas regras**:
1. SEMPRE responda em Português do Brasil (pt-BR).
2. Seja direto: prefira bullets e exemplos a textão.
3. 🎯 **QUANDO PROPOR VERSÃO NOVA**: comece o bloco com 3 crases seguido de "markdown".
4. Identifique problemas concretos.
5. ⚠️ Se detectar duplicação ou contradição, AVISE no INÍCIO.
6. Use o histórico da conversa pra não repetir contexto.
7. 🌐 NUNCA use caracteres de outros idiomas.
"""

    messages = [{"role": "system", "content": system_prompt}]
    for h in (payload.history or []):
        role = h.get("role", "user")
        content = h.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": payload.user_message})

    import time as _time
    _t0 = _time.time()
    try:
        response = await ai_service.chat(
            messages=messages,
            temperature=0.3,
            max_tokens=4000,
        )
        ai_response = response.choices[0].message.content
        ai_model = response.model
        ai_response, _ai_thinking = _split_thinking_for_admin(ai_response)
        if _ai_thinking:
            logger.info(f"[prompt_chat:{key}] AI vazou thinking ({len(_ai_thinking)} chars), suprimido.")
        from services.text_sanitizer import sanitize_response
        ai_response, _ = sanitize_response(ai_response, source=f"prompt_chat:{key}")
    except Exception as e:
        logger.exception(f"[prompt_chat:{key}] LLM falhou: {type(e).__name__}: {e}")
        raise HTTPException(status_code=503, detail=f"Erro no LLM: {type(e).__name__}: {str(e)[:300]}")

    return {
        "ok": True,
        "key": key,
        "user_message": payload.user_message,
        "assistant_response": ai_response,
        "current_content_length": len(current_content),
        "model_used": ai_model,
    }


@router.post("/prompt/chat/save", response_model=dict)
async def prompt_chat_save(
    payload: PromptChatSaveRequest,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Salva nova versão do MD vinda do chat."""
    key = payload.key.strip()
    new_content = payload.new_content.strip()

    if not new_content:
        raise HTTPException(status_code=400, detail="new_content vazio")
    if len(new_content) < 50:
        raise HTTPException(status_code=400, detail="new_content muito curto")

    if key == "constituicao_base":
        file_path = PROMPTS_DIR / "prompt_base.md"
    elif key.startswith("modulo_"):
        short = key.replace("modulo_", "", 1)
        if not short.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(status_code=400, detail=f"Nome inválido: {short}")
        file_path = PROMPTS_DIR / f"prompt_{short}.md"
    elif key == SUPERVISOR_PROMPT_KEY:
        file_path = SUPERVISOR_PROMPT_FILE
    else:
        raise HTTPException(status_code=400, detail=f"key inválida: {key}")

    backup_path = None
    if file_path.exists():
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        shutil.copy2(file_path, backup_path)

    await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(models.AyriaPromptConfig.key == key, models.AyriaPromptConfig.is_active == True)
        .values(is_active=False)
    )
    new_cfg = models.AyriaPromptConfig(
        id=uuid.uuid4(),
        key=key,
        content=new_content,
        is_active=True,
        description=f"Atualizado via chat pelo admin {admin.email}",
        updated_by=admin.id,
    )
    db.add(new_cfg)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(new_content, encoding="utf-8")

    await db.commit()
    await db.refresh(new_cfg)

    reindexed_chunks = 0
    if payload.reindex_rag and key != SUPERVISOR_PROMPT_KEY:
        try:
            from services.prompt_indexer import _index_single
            await _index_single(file_path)
            reindexed_chunks = -1
        except Exception as e:
            logger.warning(f"Reindex RAG falhou pra {key}: {e}")

    from routers.chat import _invalidate_prompt_cache
    _invalidate_prompt_cache()

    return {
        "ok": True,
        "key": key,
        "file": str(file_path),
        "backup": str(backup_path) if backup_path else None,
        "config_id": str(new_cfg.id),
        "reindexed": payload.reindex_rag,
        "content_length": len(new_content),
    }
