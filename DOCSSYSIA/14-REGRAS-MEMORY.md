# 14 — Regras críticas do MEMORY.md (sobre AYRIA)

Regras duramente aprendidas que **NUNCA** podem ser violadas. Estas vieram de broncas reais do Rafael.

## 🚨 REGRA 1: "Mesma versão que temos local" = EXATAMENTE a mesma

**Quando:** 14/08/2026
**Bronca:** "vc é idiota? eu pedi pra ser mesma versão que temos local!"

**Significa:** Se o AYRIA local roda PG 18.4, a VPS também tem que rodar PG 18.4. Não importa análise de "compatibilidade", não importa sugestão de LTS.

**Aplicação AYRIA:**
- PG local = PG 18.4 → VPS **tem que ser** PG 18.4
- Python local = 3.12 (Docker) → venv VPS = 3.12
- Node local = 22.x → Node VPS = mesma versão

## 🚨 REGRA 2: Systemd AYRIA precisa de EnvironmentFile

**Quando:** 14/08/2026
**Causa:** `email_turbo.py` usa `os.getenv()` (variáveis de PROCESSO), mas systemd sem `EnvironmentFile=` não passava as credenciais TurboSMTP pro uvicorn.

**Aplicação:**
```ini
[Service]
...
EnvironmentFile=/etc/ayria/.env   # ← OBRIGATÓRIO
ExecStart=/opt/ayria/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

Variáveis que dependem disso (porque usam `os.getenv`):
- TURBOSMTP_CONSUMER_KEY / SECRET
- MAIL_FROM / MAIL_FROM_NAME
- PUBLIC_BASE_URL (se override)

Variáveis que NÃO dependem (pydantic-settings pega do .env direto):
- DATABASE_URL
- AI_API_KEY
- AZURE_STORAGE_SAS_URL
- STRIPE_*
- JWT_SECRET

## 🚨 REGRA 3: NÃO downgradar PostgreSQL sem autorização

**Causa:** Tentei downgrade PG 18 → 16 por "compatibilidade" sem perguntar.

**Aplicação:** Se o AYRIA roda em PG X, mantém PG X. Mesmo que eu ache que versão Y é "melhor", **não mudo sem autorização EXPLÍCITA**.

## 🚨 REGRA 4: Sempre COMMIT + PUSH (nunca local sem push)

**Quando:** 22/07/2026
**Bronca:** "o comite tem que acontecer a cada sessão num pode de forma algum perder isso!"

**Aplicação:**
- Antes de QUALQUER resposta pro Rafael sobre código → `git add + commit + push`
- Se push falhar → PARAR e avisar, não continuar trabalhando
- Script: `bash /home/peron/bin/ayria-commit-save "msg"`

## 🚨 REGRA 5: NÃO mexer no Mikrotik (rede)

**Quando:** 22/07/2026
**Bronca:** "vc nunca deve mexer nas regras de ferram minha navegação ok 445 80 8080"

**Aplicação:** NUNCA:
- ❌ Criar/editar regra NAT (dstnat, srcnat)
- ❌ Criar/editar filtro (forward, input)
- ❌ Criar/editar mangle/route
- ❌ Nem mesmo READ-ONLY sem pedir

**Se algo exige Mikrotik:** confirmar com Rafael primeiro.

## 🚨 REGRA 6: AYRIA em produção = NATIVO, NUNCA Docker

**Quando:** 13/08/2026
**Aplicação:** VPS roda uvicorn + Postgres + Qdrant nativos. Não usar Docker pra AYRIA em produção. Docker adiciona camadas de bug.

## 🚨 REGRA 7: Diferença local vs produção = APENAS SSL

**Quando:** 13/08/2026
**Aplicação:** Se local funciona e prod quebra, o problema é CONFIG (variáveis, SSL), nunca código.

## 🚨 REGRA 8: Sempre VALIDAR no navegador antes de entregar

**Quando:** 12/08/2026
**Bronca:** "tudo que vc fizer de app que roda na web, antes de me entregar vc deve testar se ele ta online, abrindo o navegador e entrando no app"

**Aplicação:**
- ❌ NÃO basta `curl 200` — curl não é "app carregando"
- ✅ ABRIR Playwright headless → screenshot → `image` tool → VER
- ✅ SÓ ENTÃO anexar print + URL e entregar
- ✅ Testar com usuário real (peron@perontecnologia.com.br)

## 🚨 REGRA 9: NÃO misturar contextos

**Quando:** 10/08/2026 + 13/08/2026
**Bronca:** "eu não quero que vc misture coisas!"

**Aplicação:**
- Quando o Rafael falar de **UM TEMA específico** (ex: AYRIA), ficar SÓ naquele tema
- ❌ NUNCA inferir de outro contexto (ex: JUJU) pra explicar AYRIA
- ❌ NUNCA misturar JUJU, ZE, marketing, aapanel com AYRIA

## 🚨 REGRA 10: Cache-bust no frontend AYRIA

**Quando:** 15/07/2026
**Aplicação:** Toda mudança de frontend exige:
1. Cache-bust no `index.html` (`?v=timestamp`)
2. Validar bundle novo no container (`docker exec grep`)
3. Validar texto antigo sumiu

## 🚨 REGRA 11: Resposta curta quando user tá bravo

**Quando:** 29/06/2026
**Aplicação:** Se Rafael tá puto e pergunta simples, resposta em 1 linha. Sem título, sem seção, sem "aqui está".

## 🚨 REGRA 12: NÃO inventar sem fonte

**Quando:** 06/07/2026
**Aplicação:** Toda afirmação operacional citar fonte (arquivo + heading). Sem fonte, dizer "não sei".

## 🚨 REGRA 13: NÃO PARAR no meio e perguntar

**Quando:** 13/08/2026 (reforçado 14/08/2026)
**Bronca:** "eu tô parando no MEIO das coisas e voltando a perguntar. Isso é pior do que errar"

**Aplicação:**
- Quando Rafael der OK pra começar → IR ATÉ O FINAL
- Não perguntar "ok?" no meio do trabalho
- Terminar a tarefa SÓ ENTÃO perguntar o próximo passo

## 🚨 REGRA 14: NÃO convencer, dar opções neutras

**Quando:** 08/08/2026
**Aplicação:** Dar opções PURAS, sem "recomendo X" misturado. Se tiver opinião, marcar EXPLÍCITAMENTE separado como "minha preferência".

## 🚨 REGRA 15: Bug silencioso — sempre verificar resultado real

**Quando:** 15/07/2026 (TurboSMTP retornava 201 mesmo sem enviar)
**Aplicação:** Não confiar em "status 200/201" — verificar log/backend/DB pra confirmar que a ação REALMENTE aconteceu.