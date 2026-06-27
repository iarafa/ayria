# AYRIA

> Plataforma de IA para autoconhecimento, psicologia e numerologia.
> Multi-usuário, memória de longo prazo, base de conhecimento treinável.

## Stack

- **Backend:** FastAPI (Python 3.12) + BackgroundTasks
- **Frontend:** React + Vite + Tailwind CSS + Lucide React
- **DB Estruturado:** PostgreSQL 16 (JSONB)
- **DB Vetorial:** Qdrant
- **IA:** MiniMax / OpenAI (OpenAI-compatible API)
- **Storage:** Local filesystem (em /app/uploads)
- **Deploy:** Docker + Coolify

## Quick Start (dev local)

```bash
# 1. Configure o .env (já existe em .env)
cp .env.example .env
# Edite: JWT_SECRET, POSTGRES_PASSWORD, AI_API_KEY (já configurado)

# 2. Suba tudo
docker compose up -d

# 3. Acesse:
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000/docs (Swagger)
# Qdrant:   http://localhost:6333/dashboard
```

## Login padrão (admin seed)

- **Email:** admin@ayria.local
- **Senha:** admin123

**MUDE A SENHA EM PRODUÇÃO!**

## Estrutura

```
ayria/
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── database.py              # SQLAlchemy async + Settings
│   ├── models.py                # 9 models ORM
│   ├── schemas.py               # Pydantic schemas
│   ├── routers/
│   │   ├── auth.py              # /api/auth/{register,login,me}
│   │   ├── onboarding.py        # /api/onboarding/{status,answer}
│   │   ├── chats.py             # /api/chats/* (CRUD)
│   │   ├── chat.py              # /api/chat/message (Motor AYRIA)
│   │   └── admin.py             # /api/admin/* (users, knowledge, attributes)
│   ├── services/
│   │   ├── ai_service.py        # MiniMax + OpenAI fallback
│   │   ├── vector_service.py    # Qdrant 3 collections
│   │   └── storage_service.py   # Local filesystem
│   ├── utils/
│   │   └── security.py          # JWT + bcrypt
│   └── migrations/
│       ├── init.sql             # Schema inicial (8 tabelas)
│       └── 002_alignment.sql    # Ajustes p/ checklist oficial
├── frontend/                    # React/Vite (próxima fase)
│   ├── tailwind.config.js       # ✅ Design system aplicado
│   └── src/
├── docker-compose.yml           # 4 services
├── Dockerfile.backend           # Python 3.12
├── Dockerfile.frontend          # Node 20
├── .env.example                 # Template de env vars
└── AYRIA_CHECKLIST_AUDITORIA.md # Validação oficial
```

## Design System

Paleta oficial aplicada em `frontend/tailwind.config.js`:

```
ayria.bg     #050505   (background principal)
ayria.card   #111111   (cards)
ayria.primary #6366F1  (indigo)
ayria.accent  #A855F7  (roxo)
ayria.text    #F8FAFC  (texto)
ayria.muted   #94A3B8  (secundário)
ayria.success #10B981
ayria.error   #EF4444
ayria.admin   #F59E0B
```

## Rotas implementadas (17 endpoints do checklist oficial)

| Método | Rota | Função |
|---|---|---|
| POST | `/api/auth/register` | Cadastro |
| POST | `/api/auth/login` | Login JWT |
| GET | `/api/auth/me` | Perfil atual |
| GET | `/api/onboarding/status` | Perguntas dinâmicas |
| POST | `/api/onboarding/answer` | Salvar resposta |
| GET | `/api/chats` | Listar conversas |
| POST | `/api/chats` | Criar conversa |
| GET | `/api/chats/{id}/messages` | Listar mensagens |
| DELETE | `/api/chats/{id}` | Deletar |
| POST | `/api/chat/message` | Enviar msg (Motor AYRIA) |
| GET | `/api/admin/users` | Listar users |
| PUT | `/api/admin/users/{id}/role` | Mudar role |
| GET | `/api/admin/attributes` | Listar atributos |
| POST | `/api/admin/attributes` | Criar atributo |
| GET | `/api/admin/onboarding/config` | Ver config |
| PUT | `/api/admin/onboarding/config` | Editar config |
| GET | `/api/admin/knowledge/list` | Listar docs |
| POST | `/api/admin/knowledge/upload` | Upload doc |
| DELETE | `/api/admin/knowledge/{id}` | Deletar doc |

## Próximas fases

- ⏳ **Fase 3:** Frontend React/Vite (Tailwind aplicado, falta implementar páginas)
- ⏳ **Fase 4:** Chunking de PDFs + embedding real (LangChain) pra Qdrant
- ⏳ **Fase 5:** Deploy Coolify com HTTPS

## Documentação

Ver `docs/AYRIA_DESIGN_SYSTEM.md` e `AYRIA_CHECKLIST_AUDITORIA.md`.

## Pendências pra produção

- [ ] Trocar senha do admin padrão
- [ ] Configurar HTTPS via Coolify
- [ ] Implementar chunking real de PDFs (LangChain)
- [ ] Implementar embeddings reais (text-embedding-3-small)
- [ ] Backup automático do PostgreSQL
- [ ] Monitoramento (logs + métricas)
