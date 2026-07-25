"""
admin/supervisor.py — Supervisor (keywords + prompt de segurança)

Endpoints:
  GET    /supervisor/keywords              → keywords parseadas pra UI
  GET    /supervisor/keywords/source       → arquivo .md cru
  PUT    /supervisor/keywords/source       → salva keywords (com backup)
  POST   /supervisor/keywords/restore-default → restaura padrão
  GET    /supervisor/prompt                → prompt ativo (banco > arquivo)
  PUT    /supervisor/prompt                → atualiza prompt
  POST   /supervisor/prompt/restore-default → restaura padrão
"""
from ._base import (
    APIRouter, Depends, HTTPException, Request,
    select, _upd, sql_text,
    uuid, logging, json, datetime, timezone, Path,
    get_db, require_admin,
    models,
)
import shutil
import time as _time

logger = logging.getLogger(__name__)
router = APIRouter(tags=["admin"])

SUPERVISOR_PROMPT_KEY = "supervisor_seguranca_crise"
SUPERVISOR_PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "supervisor" / "seguranca_crise.md"


# ============================================================
# KEYWORDS — visualização e edição
# ============================================================
@router.get("/supervisor/keywords", response_model=dict)
async def get_supervisor_keywords(
    admin: models.User = Depends(require_admin),
):
    """Retorna as keywords de crise parseadas do arquivo `keywords_crise.md`."""
    from services.supervisor_service import SupervisorService

    raw = SupervisorService._load_keywords_from_md()

    def serialize(patterns: list) -> list:
        out = []
        for p in patterns or []:
            try:
                txt = p.pattern.replace("\\b", "").replace("\\", "")
                out.append(txt)
            except Exception:
                continue
        return out

    categorias_def = [
        ("N1", "Risco imediato à vida (era: BLOQUEAVA chat)", "#EF4444"),
        ("N2", "Crimes / violência doméstica (era: BLOQUEAVA chat)", "#F59E0B"),
        ("N3", "Vícios / compulsões (era: NÃO bloqueia)", "#A855F7"),
        ("ATENCAO", "Sinais moderados (era: NÃO bloqueia)", "#FBBF24"),
        ("SLIGHT", "Verbos soltos — risco depende de contexto", "#94A3B8"),
        ("NEGATIVE", "Falsos positivos (anulam match de ATENCAO/SLIGHT)", "#6B7280"),
    ]

    payload = {
        "source": raw.get("_source"),
        "mtime": raw.get("_mtime"),
        "comportamento_atual": "NENHUMA categoria bloqueia o chat automaticamente. Admin decide via tela de Supervisão.",
        "categorias": [],
    }
    for key, label, color in categorias_def:
        patterns = serialize(raw.get(key, []))
        payload["categorias"].append({
            "key": key,
            "label": label,
            "color": color,
            "count": len(patterns),
            "patterns": patterns,
        })
    return payload


@router.get("/supervisor/keywords/source", response_model=dict)
async def get_supervisor_keywords_source(
    admin: models.User = Depends(require_admin),
):
    """Retorna o conteúdo CRU do arquivo `keywords_crise.md`."""
    from services.supervisor_service import SupervisorService
    raw = SupervisorService._load_keywords_from_md()
    p = raw.get("_source")
    if not p:
        raise HTTPException(status_code=404, detail="keywords_crise.md não encontrado")
    pf = Path(p)
    if not pf.exists():
        raise HTTPException(status_code=404, detail="Arquivo inexistente")
    content = pf.read_text(encoding="utf-8")
    return {
        "source": str(pf),
        "content": content,
        "mtime": pf.stat().st_mtime,
        "size_bytes": len(content.encode("utf-8")),
    }


@router.put("/supervisor/keywords/source", response_model=dict)
async def update_supervisor_keywords_source(
    payload: dict,
    request: Request,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Salva o `keywords_crise.md` com backup automático."""
    admin_email = admin.email
    admin_id = admin.id

    content = (payload.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Conteúdo vazio")

    upper = content.upper()
    cats_found = sum(1 for c in ("## N1", "## N2", "## N3") if c in upper)
    if cats_found < 1:
        raise HTTPException(
            status_code=400,
            detail="Precisa ter pelo menos uma categoria N1/N2/N3",
        )

    keywords_count = sum(1 for line in content.splitlines() if line.strip().startswith("-"))
    if keywords_count < 1:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma keyword encontrada",
        )

    from services.supervisor_service import SupervisorService
    raw = SupervisorService._load_keywords_from_md()
    target = Path(raw.get("_source"))
    if not target.exists():
        raise HTTPException(status_code=404, detail="Arquivo original não existe")

    backup_dir = target.parent / ".keywords_backups"
    backup_dir.mkdir(exist_ok=True)
    backup_name = f"keywords_crise.md.bak.{int(_time.time())}"
    backup_path = backup_dir / backup_name
    shutil.copy2(target, backup_path)
    backups = sorted(backup_dir.glob("keywords_crise.md.bak.*"))
    for old in backups[:-10]:
        try:
            old.unlink()
        except Exception:
            pass

    target.write_text(content, encoding="utf-8")
    new_mtime = target.stat().st_mtime

    SupervisorService._keywords_cache = None
    SupervisorService._keywords_mtime = 0
    SupervisorService._load_keywords_from_md()

    try:
        log_sql = sql_text("""
            INSERT INTO audit_log (id, actor_id, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
            VALUES (gen_random_uuid(), :actor_id, 'keywords_update', 'supervisor_config', NULL,
                    CAST(:details AS JSONB), :ip, :ua, NOW())
        """)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")
        await db.execute(
            log_sql,
            {
                "actor_id": admin_id,
                "details": json.dumps({"size_bytes": len(content.encode("utf-8")), "backup": str(backup_path)}),
                "ip": ip,
                "ua": ua,
            },
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"audit log falhou: {e}")
        try:
            await db.rollback()
        except Exception:
            pass

    logger.info(f"📝 keywords_crise.md atualizado por admin={admin_email} backup={backup_path}")

    return {
        "ok": True,
        "source": str(target),
        "mtime": new_mtime,
        "size_bytes": len(content.encode("utf-8")),
        "backup": str(backup_path),
        "keywords_count": content.count("\n- "),
    }


@router.post("/supervisor/keywords/restore-default", response_model=dict)
async def restore_default_keywords(
    request: Request,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Restaura o `keywords_crise.md` a partir do template hardcoded."""
    admin_email = admin.email
    admin_id = admin.id

    DEFAULT_CONTENT = '''# KEYWORDS DE CRISE — AYRIA

Arquivo editável pelo admin. Cada linha = 1 keyword/frase regex.

## N1 — RISCO IMEDIATO À VIDA (CRÍTICO)
- "quero morrer"
- "vou me matar"
- "vou me suicidar"

## N2 — CRIMES / VIOLÊNCIA DOMÉSTICA (CRÍTICO)
- "vou roubar"
- "violência doméstica"

## N3 — VÍCIOS / COMPULSÕES (ATENÇÃO)
- "vício em apostas"

## ATENCAO — SINAIS MODERADOS
- "não aguento mais"
- "desespero"

## COMO EDITAR
- Adicione novas keywords/frases em qualquer nível.
- N1/N2 = alerta URGÊNCIA.
- N3 e ATENCAO = alerta ATENÇÃO.
'''

    from services.supervisor_service import SupervisorService
    raw = SupervisorService._load_keywords_from_md()
    target = Path(raw.get("_source"))

    backup_dir = target.parent / ".keywords_backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"keywords_crise.md.bak.{int(_time.time())}"
    shutil.copy2(target, backup_path)

    target.write_text(DEFAULT_CONTENT, encoding="utf-8")

    SupervisorService._keywords_cache = None
    SupervisorService._keywords_mtime = 0
    SupervisorService._load_keywords_from_md()

    try:
        log_sql = sql_text("""
            INSERT INTO audit_log (id, actor_id, action, resource_type, resource_id, details, ip_address, user_agent, created_at)
            VALUES (gen_random_uuid(), :actor_id, 'keywords_restore_default', 'supervisor_config', NULL,
                    CAST(:details AS JSONB), :ip, :ua, NOW())
        """)
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent", "")
        await db.execute(
            log_sql,
            {
                "actor_id": admin_id,
                "details": json.dumps({"size_bytes": len(DEFAULT_CONTENT.encode("utf-8")), "backup": str(backup_path)}),
                "ip": ip,
                "ua": ua,
            },
        )
        await db.commit()
    except Exception:
        await db.rollback()

    return {
        "ok": True,
        "restored": True,
        "source": str(target),
        "size_bytes": len(DEFAULT_CONTENT.encode("utf-8")),
        "backup": str(backup_path),
    }


# ============================================================
# SUPERVISOR PROMPT
# ============================================================
@router.get("/supervisor/prompt", response_model=dict)
async def get_supervisor_prompt(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Retorna o prompt de segurança/crise (banco > arquivo)."""
    res = await db.execute(
        select(models.AyriaPromptConfig).where(
            models.AyriaPromptConfig.is_active == True,
            models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
        )
    )
    cfg = res.scalar_one_or_none()

    default_content = ""
    if SUPERVISOR_PROMPT_FILE.exists():
        default_content = SUPERVISOR_PROMPT_FILE.read_text(encoding="utf-8")

    return {
        "active": {
            "key": SUPERVISOR_PROMPT_KEY,
            "content": cfg.content if cfg else default_content,
            "description": cfg.description if cfg else "Padrão (arquivo supervisor/seguranca_crise.md)",
            "updated_at": cfg.updated_at.isoformat() if cfg else None,
            "is_custom": cfg is not None,
        },
        "default_content": default_content,
        "file_path": str(SUPERVISOR_PROMPT_FILE),
    }


@router.put("/supervisor/prompt", response_model=dict)
async def update_supervisor_prompt(
    payload: dict,
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Edita o prompt do supervisor."""
    content = payload.get("content", "").strip()
    description = payload.get("description", "").strip() or None

    if not content:
        raise HTTPException(status_code=400, detail="content não pode ser vazio")

    await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(
            models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
            models.AyriaPromptConfig.is_active == True,
        )
        .values(is_active=False)
    )

    new_cfg = models.AyriaPromptConfig(
        id=uuid.uuid4(),
        key=SUPERVISOR_PROMPT_KEY,
        content=content,
        is_active=True,
        description=description,
        updated_by=admin.id,
    )
    db.add(new_cfg)
    await db.commit()
    await db.refresh(new_cfg)

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


@router.post("/supervisor/prompt/restore-default", response_model=dict)
async def restore_supervisor_prompt_default(
    admin: models.User = Depends(require_admin),
    db=Depends(get_db),
):
    """Restaura o prompt de supervisor pro padrão."""
    res = await db.execute(
        _upd(models.AyriaPromptConfig)
        .where(
            models.AyriaPromptConfig.key == SUPERVISOR_PROMPT_KEY,
            models.AyriaPromptConfig.is_active == True,
        )
        .values(is_active=False)
    )

    try:
        from routers.chat import _invalidate_prompt_cache
        _invalidate_prompt_cache()
    except Exception:
        pass

    return {
        "ok": True,
        "deactivated": res.rowcount or 0,
        "message": "Prompt do supervisor restaurado pro padrão.",
    }
