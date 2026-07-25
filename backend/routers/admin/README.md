# Pasta `backend/routers/admin/` — Admin Router (quebrado por sub-domínio)

## O que mora aqui

Todos os endpoints administrativos (`/api/admin/*`), separados por sub-domínio.

## Regra

- **1 arquivo = 1 sub-domínio**. Não misturar.
- **NUNCA** criar endpoint novo em arquivo errado — coloca no certo.
- Todo endpoint aqui exige `Depends(require_admin)`.
- Endpoint que muda role/permissions precisa de check extra `admin.role == "SUPER_ADMIN"`.
- Audit log: ações destrutivas (delete, role change, password reset) DEVEM gravar em `audit_log`.

## Estrutura

```
admin/
├── README.md         # este arquivo
├── __init__.py       # junta todos os sub-routers no prefixo /api/admin
├── _base.py          # imports compartilhados (FastAPI, models, schemas, etc)
├── users.py          # CRUD user + block + password + role + details + observer (12 endpoints)
├── audit.py          # audit log + ingest de logs do frontend (2 endpoints)
├── attributes.py     # attribute definitions (2 endpoints)
├── onboarding.py     # onboarding config (2 endpoints)
├── knowledge.py      # knowledge documents (3 endpoints)
├── plans.py          # planos comerciais (2 endpoints)
├── config.py         # config IA/system + debug Qdrant (3 endpoints)
├── prompt.py         # system prompt + RAG + prompt chat (11 endpoints)
├── supervisor.py     # supervisor keywords + prompt (7 endpoints)
└── lockouts.py       # login lockouts (admin unlock) (2 endpoints)
```

**Total:** 47 endpoints (incluindo helpers como `process_document_background`)

## Histórico de mudanças

- **2026-07-25** — DE quebrou `admin.py` (2744 linhas, 43 endpoints + 4 helpers) em 10 arquivos por sub-domínio. Comportamento idêntico.

## Pegadinhas conhecidas

- `delete_user` faz cascade manual (Postgres raw SQL + Qdrant + Stripe). Ordem importa: apaga filhos ANTES do user.
- `block_user` resolve alerts de supervisor abertos automaticamente (status='resolved').
- `admin_change_password` checa se é o ÚLTIMO admin antes de resetar senha de outro admin.
- `update_user_role` (SUPER_ADMIN only) impede auto-rebaixamento + último SUPER_ADMIN.
- `prompt_chat` usa temperatura 0.3 e max_tokens 4000 — escrita estruturada.
- `prompt/system/restore-default` aceita `payload.key` pra restaurar SÓ um módulo.
- `supervisor/keywords/source` PUT cria backup automático (mantém últimos 10).
- `knowledge/upload` valida MIME + tamanho (50MB) + path traversal.
- `debug/qdrant` testa reachability com timeout 3s + DNS lookup separado.
- `login-lockouts/unlock` chama `services.lockout_service.admin_unlock` (delega).
- `process_document_background` (knowledge.py) é função helper chamada via `BackgroundTasks`.
- `prompt_chat_save` faz backup do .md antes de sobrescrever.
- `AVAILABLE_MODULES` é mutável (in-memory list) — `delete_module` reindexa do filesystem.

## Como usar

```python
# main.py
from routers.admin import router as admin_router
app.include_router(admin_router)
```

## Como adicionar endpoint novo

1. Identifica o sub-domínio → se já tem arquivo, **usa o existente**.
2. Se for sub-domínio novo, cria arquivo novo + adiciona import em `__init__.py`.
3. Atualiza este README (estrutura + pegadinhas).
