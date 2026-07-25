"""
AYRIA - Admin Router (montagem)

Todos os endpoints administrativos ficam aqui, organizados por sub-domínio.

REGRA: cada arquivo = 1 responsabilidade.
- users.py       → CRUD user + block + password + role + details + observer (chats/messages de outro user)
- audit.py       → audit log + ingest de logs do frontend
- attributes.py  → attribute definitions
- onboarding.py  → onboarding config
- knowledge.py   → knowledge documents (upload/list/delete) + background processing
- plans.py       → CRUD planos comerciais
- config.py      → config IA/system + debug qdrant
- prompt.py      → system prompt (constituição + módulos) + RAG + prompt chat
- supervisor.py  → supervisor keywords + supervisor prompt
- lockouts.py    → login lockouts (admin unlock)
"""
from fastapi import APIRouter

# Importa cada sub-router e junta no prefix `/api/admin`
from .users import router as users_router
from .audit import router as audit_router
from .attributes import router as attributes_router
from .onboarding import router as onboarding_router
from .knowledge import router as knowledge_router
from .plans import router as plans_router
from .config import router as config_router
from .prompt import router as prompt_router
from .supervisor import router as supervisor_router
from .lockouts import router as lockouts_router

router = APIRouter(prefix="/api/admin", tags=["admin"])

router.include_router(users_router)
router.include_router(audit_router)
router.include_router(attributes_router)
router.include_router(onboarding_router)
router.include_router(knowledge_router)
router.include_router(plans_router)
router.include_router(config_router)
router.include_router(prompt_router)
router.include_router(supervisor_router)
router.include_router(lockouts_router)
