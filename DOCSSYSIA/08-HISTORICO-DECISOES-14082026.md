# Histórico de decisões — 14/08/2026 (sessão de deploy AYRIA)

## Sequência do que foi feito

1. ✅ Validação VPS básica (SSH 2222 + segurança)
2. ✅ Instalação Postgres 18.4 (apt)
3. ✅ Instalação Qdrant 1.12.4 (binário standalone)
4. ✅ Configuração Caddy 2.6.2 (apt)
5. ✅ Setup DNS ayria.online + teste.ayria.online via Cloudflare
6. ✅ Clone do código AYRIA (`feature/sub-alma-user` branch) → /opt/ayria
7. ❌ **ERRO**: tentei downgrade PG 18 → 16 por "compatibilidade" — Rafael xingou
8. ✅ **CORREÇÃO**: reverti pra PG 18.4 (mesma versão do local)
9. ✅ Migração do banco AYRIA local (porta 5434) → VPS (porta 5432) via pg_dump + restore
10. ✅ Mudança de `staging.ayria.online` → `teste.ayria.online` (Rafael pediu)
11. ✅ Instalação Python 3.12 via deadsnakes PPA (3.14 não tinha wheels)
12. ✅ pip install requirements.txt (FastAPI, asyncpg, stripe, etc)
13. ✅ npm install + npm run build do frontend
14. ✅ systemd unit ayria-backend.service (User=ayria-app, EnvironmentFile=/etc/ayria/.env)
15. ❌ **ERRO**: faltou `stripe` no requirements.txt — instalei manual
16. ❌ **ERRO**: `email_turbo.py` usa `os.getenv()` mas systemd não tinha EnvironmentFile — adicionamos
17. ✅ Bug do Caddy: matcher `@backend path /api/*` não aplicava — fix com `handle @backend` antes do handle SPA
18. ✅ Test signup real: criou user + enviou email via TurboSMTP (HTTP 200 OK)
19. ✅ Setup staging: .env-staging + systemd unit ayria-backend-staging.service + vhost Caddy
20. ⚠️ **CAVEAT**: frontend em teste.ayria.online tem VITE_API_URL=https://ayria.online, então chamadas API vão pro prod (não pro staging)
21. ✅ Stripe verificado: API key funciona (test mode, R$ 4369,11 sandbox)
22. ✅ Consulta documentação oficial do Stripe (3 docs)
23. ⚠️ **PENDENTE**: Cloudflare Origin Cert (SSL Strict)
24. ⚠️ **PENDENTE**: backup automático (pg_dump diário)
25. ⚠️ **PENDENTE**: monitor de saúde (cron 5min)
26. ⚠️ **PENDENTE**: trocar Stripe pra LIVE (transações reais)

## Decisões importantes

| Decisão | Por quê | Quem decidiu |
|---|---|---|
| **PG 18.4 (NÃO 16)** | AYRIA local já roda em 18.4, é compatível. "Mesma versão que temos local" | Rafael (após bronca) |
| **Staging em `teste.ayria.online`** (não `staging`) | Rafael pediu pra renomear | Rafael |
| **Python 3.12** (não 3.14) | Pacotes do AYRIA não tinham wheels pra 3.14 | RAFA (técnico) |
| **Caddy (não Nginx)** | Mais simples, HTTPS automático | RAFA (técnico) |
| **Cert auto-assinado** (não Origin Cert ainda) | Pra subir rápido; Origin Cert é melhor mas pendente | RAFA (técnico) |
| **Stripe TEST mode primeiro** | Validar fluxo antes de live (cliente real) | RAFA + Rafael |
| **Prod primeiro, staging depois** | Rafael mudou ideia no meio: "primeiro produção, depois teste" | Rafael |
| **Sem backup/monitor** | Escopo inicial era só "subir funcional" | Rafael (aceitou) |
| **Mesmo banco prod + staging** | Escopo era só separar por porta, não por dados | RAFA (técnico) |

## Regras MEMORY.md adicionadas hoje

1. **PG 18.4 = mesma versão do local** — NUNCA fazer downgrade sem autorização
2. **systemd AYRIA precisa de EnvironmentFile=/etc/ayria/.env** — porque email_turbo.py usa os.getenv()
3. **Caddy handle @backend ANTES do handle SPA** — senão rewrite rouba
4. **Cartão 4242 4242 4242 4242** — pra testar Stripe em test mode
