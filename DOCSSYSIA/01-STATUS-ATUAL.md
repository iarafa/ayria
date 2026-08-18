# Status atual (14/08/2026 19:38 GMT-3)

## VPS
- **IP:** 179.198.127.230 (Hostinger VPS)
- **OS:** Ubuntu 26.04 LTS
- **Hostname:** srv1899928
- **Disco:** 387GB (381GB livre)
- **RAM:** 31GB (30GB livre)
- **Uptime:** ~24h

## Serviços rodando

| Serviço | Versão | Status | Porta | Unit |
|---|---|---|---|---|
| **Caddy** | 2.6.2 | ✅ ativo | 80, 443 | `caddy.service` |
| **PostgreSQL** | 18.4 (pgdg) | ✅ online | 127.0.0.1:5432 | `postgresql.service` |
| **Qdrant** | 1.12.4 | ✅ rodando | 6333 (HTTP), 6334 (gRPC) | (nohup via /opt/qdrant/start.sh) |
| **AYRIA prod** | uvicorn 0.32.0 | ✅ ativo | 127.0.0.1:8000 | `ayria-backend.service` |
| **AYRIA staging** | uvicorn 0.32.0 | ✅ ativo | 127.0.0.1:8001 | `ayria-backend-staging.service` |
| **SSH** | OpenSSH | ✅ ativo | 2222 | `ssh.service` |

## URLs (via Cloudflare proxy ON)

| URL | Aponta pra | Testado |
|---|---|---|
| https://ayria.online/ | frontend SPA | ✅ HTTP 200 (login renderiza) |
| https://ayria.online/api/* | backend prod (:8000) | ✅ JSON |
| https://ayria.online/health | backend prod | ✅ `{"status":"ok","database":"ok","environment":"production"}` |
| https://teste.ayria.online/ | frontend SPA | ✅ HTTP 200 (login renderiza) |
| https://teste.ayria.online/api/* | backend staging (:8001) | ✅ JSON |
| https://teste.ayria.online/health | backend staging | ✅ `{"environment":"staging"}` |

## Banco

- **Cluster:** `main` (PostgreSQL 18.4)
- **Database:** `ayria` (owner: ayria)
- **User:** `ayria` / senha em `/etc/ayria/.env`
- **Tamanho:** ~19MB
- **Tabelas:** 32 (restaurado de dump local)
- **Users:** 36 (incluindo `peron@perontecnologia.com.br`)

## Credenciais configuradas (em `/etc/ayria/.env`)

- ✅ TurboSMTP (envio email) — testado, signup fake recebeu email
- ✅ Stripe TEST mode — API conecta (R$ 4369,11 sandbox)
- ✅ MiniMax AI (AI_API_KEY)
- ✅ Azure Blob Storage (SAS URL)
- ❌ Cloudflare Origin Cert (SSL Strict real) — pendente
- ❌ Live Stripe keys (transações reais) — pendente

## Pendências

- ❌ Monitor de saúde (cron 5min + alerta Telegram)
- ❌ Rebuild frontend staging com VITE_API_URL=teste
- ❌ Live Stripe (transações reais)
