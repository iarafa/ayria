# AYRIA — Checklist de Auditoria Final
> Execute este arquivo ao final de todo o processo de criação.
> Para cada item, marque ✅ (OK), ❌ (Faltando) ou ⚠️ (Parcial).
> Não avance para produção enquanto houver ❌.

---

## 🗂️ BLOCO 1 — Estrutura de Arquivos e Projeto

- [ ] Repositório criado e estruturado corretamente
- [ ] Arquivo `.env.example` presente com todas as variáveis necessárias
- [ ] Arquivo `.env` configurado com valores reais (nunca commitado)
- [ ] `.gitignore` incluindo `.env`, `__pycache__`, `node_modules`, `dist`
- [ ] `README.md` com instruções de instalação e execução
- [ ] `Dockerfile` presente e funcional
- [ ] `docker-compose.yml` presente (backend + qdrant)
- [ ] Build de produção do frontend gerado (`npm run build`)
- [ ] Frontend sendo servido pelo backend FastAPI (pasta `dist/` ou `static/`)

---

## ⚙️ BLOCO 2 — Backend (FastAPI)

- [ ] FastAPI inicializa sem erros (`uvicorn main:app`)
- [ ] Rota `/health` retorna `{ "status": "ok" }`
- [ ] CORS configurado corretamente para o domínio do frontend
- [ ] Todas as rotas da API estão prefixadas com `/api`
- [ ] Middleware de autenticação JWT funcionando em todas as rotas protegidas
- [ ] Tratamento de erros global implementado (handler 404, 422, 500)
- [ ] Logs estruturados funcionando (sem `print()` solto no código)
- [ ] Variáveis de ambiente carregadas via `python-dotenv` ou `pydantic BaseSettings`
- [ ] Nenhuma chave de API hardcoded no código

### Rotas obrigatórias:
- [ ] `POST /api/auth/register`
- [ ] `POST /api/auth/login`
- [ ] `GET  /api/auth/me`
- [ ] `POST /api/onboarding/answer`
- [ ] `GET  /api/onboarding/status`
- [ ] `GET  /api/chats`
- [ ] `POST /api/chats`
- [ ] `GET  /api/chats/{chat_id}/messages`
- [ ] `POST /api/chat/message`
- [ ] `GET  /api/admin/users`
- [ ] `POST /api/admin/knowledge/upload`
- [ ] `GET  /api/admin/knowledge/list`
- [ ] `DELETE /api/admin/knowledge/{id}`
- [ ] `GET  /api/admin/onboarding/config`
- [ ] `PUT  /api/admin/onboarding/config`
- [ ] `GET  /api/admin/attributes`
- [ ] `POST /api/admin/attributes`

---

## 🗄️ BLOCO 3 — Banco de Dados (PostgreSQL)

- [ ] Conexão com PostgreSQL externa funcionando
- [ ] Migrations rodadas com sucesso (todas as tabelas criadas)
- [ ] Tabela `users` criada com todos os campos definidos
- [ ] Tabela `messages` criada com `chat_id`, `role`, `content`, `created_at`
- [ ] Tabela `chats` criada com `user_id`, `title`, `created_at`
- [ ] Tabela `onboarding_config` criada (perguntas dinâmicas)
- [ ] Tabela `user_attributes` criada (atributos dinâmicos por usuário)
- [ ] Tabela `attribute_definitions` criada (definições do admin)
- [ ] Campo `numerology_data` (JSONB) presente na tabela `users`
- [ ] Campo `onboarding_status` presente na tabela `users`
- [ ] Índices criados em `user_id`, `chat_id`, `created_at`
- [ ] Usuário admin padrão criado no seed (ou via script)

---

## 🧠 BLOCO 4 — Qdrant (Vector Database)

- [ ] Container Qdrant rodando e acessível internamente
- [ ] Conexão do backend com Qdrant funcionando
- [ ] Collection `conhecimento_geral` criada
- [ ] Collection `memoria_episodica` criada
- [ ] Collection `numerologia` criada (se aplicável)
- [ ] Função de busca semântica (`similarity_search`) funcionando
- [ ] Função de inserção de chunks funcionando
- [ ] Embeddings sendo gerados corretamente antes de inserir no Qdrant
- [ ] Metadados salvos junto com os vetores (source, tipo, user_id se aplicável)

---

## 🤖 BLOCO 5 — Integração com IA (Minimax)

- [ ] Chave de API Minimax configurada no `.env`
- [ ] Função de envio de mensagem para Minimax funcionando
- [ ] System prompt da AYRIA implementado e injetado corretamente
- [ ] Histórico de conversa sendo enviado no contexto (últimas N mensagens)
- [ ] RAG funcionando: chunks relevantes do Qdrant injetados no prompt
- [ ] Perfil do usuário (numerologia, atributos) injetado no system prompt
- [ ] Resposta da IA sendo salva no banco após cada mensagem
- [ ] Tratamento de erro caso a API da Minimax falhe (fallback ou mensagem amigável)
- [ ] Abstraction layer implementada (fácil trocar Minimax por OpenAI/Gemini)

---

## 🔐 BLOCO 6 — Autenticação e Segurança

- [ ] Registro de usuário funcionando (email + senha)
- [ ] Login retornando JWT válido
- [ ] JWT sendo validado em todas as rotas protegidas
- [ ] Senha armazenada com hash (bcrypt ou argon2) — NUNCA em texto puro
- [ ] Rota de admin protegida por role `SUPER_ADMIN`
- [ ] Usuário comum não consegue acessar rotas de admin (teste manual)
- [ ] Rate limiting implementado nas rotas de auth
- [ ] HTTPS configurado no Coolify (certificado SSL ativo)

---

## 🎨 BLOCO 7 — Frontend (React + Vite + Tailwind)

- [ ] Aplicação inicia sem erros no console
- [ ] Fonte **Inter** carregada via Google Fonts
- [ ] Tailwind configurado com as cores customizadas da AYRIA (`ayria.*`)
- [ ] Background principal `#050505` aplicado globalmente
- [ ] Sidebar com largura `260px` e fundo `#111111`
- [ ] Logo AYRIA exibido na sidebar
- [ ] Efeito Glassmorphism aplicado no header/sidebar
- [ ] Balões de chat com estilos corretos (usuário: gradiente indigo/roxo | AYRIA: card escuro)
- [ ] Input de mensagem com `rounded-2xl` e borda sutil
- [ ] Botão "Nova Conversa" funcionando
- [ ] Lista de conversas anteriores carregando na sidebar
- [ ] Loading indicator (typing dots) exibido enquanto AYRIA responde
- [ ] Interface responsiva (mobile: sidebar oculta com menu hambúrguer)
- [ ] Scroll automático para a última mensagem

### Fluxo de Onboarding:
- [ ] Usuário novo é redirecionado para onboarding ao fazer login
- [ ] Perguntas de onboarding carregadas dinamicamente do backend
- [ ] Respostas salvas corretamente no banco
- [ ] Cálculo de numerologia disparado após coleta dos dados necessários
- [ ] Usuário redirecionado para o chat após completar onboarding
- [ ] Usuário com onboarding completo vai direto para o chat

### Área Admin:
- [ ] Rota `/admin` acessível apenas para `SUPER_ADMIN`
- [ ] Aba **Usuários** — lista de usuários com dados e status
- [ ] Aba **Conhecimento** — upload de arquivos, lista de documentos, botão deletar
- [ ] Aba **Onboarding** — editor de perguntas e fluxo
- [ ] Aba **Atributos** — definição de atributos dinâmicos do usuário
- [ ] Upload de arquivo funcionando (PDF, TXT) → Azure Blob → Qdrant
- [ ] Feedback visual de sucesso/erro no upload

---

## ☁️ BLOCO 8 — Azure Blob Storage

- [ ] Connection string do Azure configurada no `.env`
- [ ] Container criado no Azure Blob
- [ ] Upload de arquivo para o Blob funcionando
- [ ] URL do arquivo salva no banco após upload
- [ ] Processamento do arquivo (chunking + embedding + Qdrant) disparado após upload
- [ ] Arquivos deletados do Qdrant quando removidos pelo admin

---

## 🚀 BLOCO 9 — Deploy (Coolify)

- [ ] Dockerfile faz build sem erros
- [ ] Variáveis de ambiente configuradas no painel do Coolify
- [ ] Serviço do backend rodando e saudável
- [ ] Container Qdrant rodando na mesma rede interna
- [ ] Domínio customizado configurado (se aplicável)
- [ ] SSL/HTTPS ativo via Let's Encrypt no Coolify
- [ ] Rota `/health` retornando 200 em produção
- [ ] Logs do container acessíveis no Coolify

---

## 🧪 BLOCO 10 — Testes Funcionais (Fluxo Completo)

Execute estes cenários manualmente antes de considerar o projeto pronto:

### Cenário 1 — Novo Usuário
- [ ] Registrar novo usuário com email e senha
- [ ] Fazer login e receber JWT
- [ ] Ser redirecionado para onboarding
- [ ] Responder todas as perguntas do onboarding
- [ ] Ver numerologia calculada e salva
- [ ] Ser redirecionado para o chat principal
- [ ] Enviar primeira mensagem e receber resposta da AYRIA

### Cenário 2 — Usuário Retornando
- [ ] Fazer login com usuário que já completou onboarding
- [ ] Ir direto para o chat (sem onboarding)
- [ ] Ver histórico de conversas anteriores na sidebar
- [ ] Continuar uma conversa anterior
- [ ] Criar nova conversa

### Cenário 3 — Admin
- [ ] Fazer login com conta SUPER_ADMIN
- [ ] Acessar área admin `/admin`
- [ ] Ver lista de usuários
- [ ] Fazer upload de um PDF de conhecimento
- [ ] Verificar que o documento aparece na lista
- [ ] Enviar mensagem no chat de treinamento e ver resposta
- [ ] Deletar um documento e verificar remoção do Qdrant

### Cenário 4 — Segurança
- [ ] Tentar acessar `/api/admin/*` com token de usuário comum → deve retornar 403
- [ ] Tentar acessar `/api/chat/message` sem token → deve retornar 401
- [ ] Tentar acessar dados de outro usuário → deve retornar 403

---

## 📋 RESULTADO FINAL

```
Total de itens:     ___
✅ OK:              ___
⚠️  Parcial:        ___
❌ Faltando:        ___

Status: [ ] APROVADO PARA PRODUÇÃO  [ ] REPROVADO — corrigir itens ❌
```

---

> **Instrução para o Replit Agent:**
> Ao finalizar a implementação, percorra este checklist item por item.
> Para cada ❌ encontrado, implemente o que está faltando antes de declarar o projeto concluído.
> Só declare "projeto finalizado" quando todos os itens estiverem ✅.
