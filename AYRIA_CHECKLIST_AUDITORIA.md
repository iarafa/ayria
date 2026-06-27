# AYRIA — Checklist de Auditoria

> Documento de auto-validação contínua. Cada item ✅ significa que está implementado e testado.

## Fase 1 — Estrutura ✅ (em progresso)

- [x] Estrutura de pastas backend/frontend criada
- [x] docker-compose.yml orquestra 4 serviços
- [x] Dockerfile.backend (Python 3.12 + FastAPI)
- [x] Dockerfile.frontend (Node 20 + Vite)
- [x] Schema PostgreSQL completo (8 tabelas + audit)
- [x] Seed admin padrão (admin@ayria.local / admin123)
- [x] Atributos padrão cadastrados
- [x] Onboarding padrão (10 passos)
- [x] .env.example com todas variáveis

## Fase 2 — Backend (próximo)

### Auth
- [ ] POST /auth/register — criar usuário
- [ ] POST /auth/login — JWT token
- [ ] POST /auth/refresh — refresh token
- [ ] Middleware auth_required
- [ ] Middleware admin_required
- [ ] Hash bcrypt (passlib)

### Users
- [ ] GET /users/me — perfil atual
- [ ] PUT /users/me — atualizar perfil
- [ ] GET /admin/users (admin)
- [ ] PUT /admin/users/{id}/role (admin)

### Onboarding
- [ ] GET /onboarding/questions — perguntas dinâmicas
- [ ] POST /onboarding/answer — salvar resposta
- [ ] POST /onboarding/complete — finalizar fluxo

### Chat
- [ ] GET /chats — listar conversas
- [ ] POST /chats — criar conversa
- [ ] GET /chats/{id} — detalhes + mensagens
- [ ] DELETE /chats/{id} — deletar
- [ ] POST /chats/{id}/messages — enviar mensagem
- [ ] Streaming SSE (opcional)

### Admin / Knowledge
- [ ] POST /admin/documents — upload arquivo
- [ ] GET /admin/documents — listar
- [ ] DELETE /admin/documents/{id}
- [ ] POST /admin/documents/{id}/reindex
- [ ] GET /admin/attributes — listar atributos
- [ ] POST /admin/attributes — criar atributo
- [ ] PUT /admin/attributes/{id}
- [ ] DELETE /admin/attributes/{id}
- [ ] GET /admin/audit-log

### Services
- [ ] ai_service.py — Minimax + OpenAI fallback
- [ ] vector_service.py — Qdrant 3 collections
- [ ] storage_service.py — Azure Blob + local
- [ ] chunking_service.py — split docs em chunks
- [ ] extraction_service.py — extrai fatos pra memoria_episodica

## Fase 3 — Frontend (depois)

### Design System
- [ ] Tailwind config (cores AYRIA, font Inter)
- [ ] Componentes base: Button, Card, Input, Modal
- [ ] Layout: Sidebar + Main
- [ ] Glassmorphism utility class
- [ ] Dark mode (default)

### Pages
- [ ] /login — Login
- [ ] /register — Cadastro
- [ ] /onboarding — Fluxo guiado
- [ ] /chat — Chat principal (com sidebar de histórico)
- [ ] /admin — Painel admin (rota protegida)
  - [ ] /admin/users
  - [ ] /admin/documents (upload)
  - [ ] /admin/attributes
  - [ ] /admin/audit

### State (Zustand ou Context)
- [ ] authStore — usuário atual, token
- [ ] chatStore — chats, mensagens ativas
- [ ] profileStore — perfil do usuário

### Hooks
- [ ] useAuth
- [ ] useChat (envio, SSE)
- [ ] useOnboarding
- [ ] useAdmin

## Fase 4 — Deploy

- [ ] docker-compose.coolify.yml (sem postgres/qdrant embutidos)
- [ ] README com instruções completas
- [ ] OpenAPI docs (FastAPI auto)
- [ ] Testes E2E (pytest + playwright)
- [ ] CI GitHub Actions
- [ ] Backup PostgreSQL automático
- [ ] Monitoramento (logs, métricas)

## Validação Contínua

Sempre que uma feature for adicionada, marcar ✅ aqui.
Items ❌ viram pendência da próxima sessão.

## Decisões Técnicas

| Item | Decisão | Por quê |
|---|---|---|
| Auth | JWT HS256 | Simples, sem dependência externa |
| DB | PostgreSQL 16 | JSONB nativo, robusto |
| Vetor | Qdrant 1.12 | Open source, fácil deploy |
| IA | Minimax M2.7 | Default OpenAI-compatible |
| Frontend state | Zustand | Mais simples que Redux |
| Styling | Tailwind + Inter | Spec pediu |
| Estilo | Glassmorphism | Spec pediu |
