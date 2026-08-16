# 16 — Mapa completo de uso de MiniMax e Telegram no AYRIA (somente VPS)

> **Escopo:** APENAS arquivos em `/opt/ayria/` (VPS Hostinger 179.198.127.230)
> **Atualizado em:** 16/08/2026 (migração do bot Telegram consolidada em 1 só)
> **Pedido do:** Rafael Peron

---

## 📱 PARTE 2 — Telegram (no VPS) — ATUALIZADO 16/08/2026

### Migração consolidada (16/08/2026)

**Antes:**
- Caminho A (supervisor) usava `TELEGRAM_BOT_TOKEN` env var
- Caminho B (Stripe payment_failed) lia de `/home/peron/.telegram_bots.env` (var `AVISOS_TOKEN`)
- Chat_id admin: `779495783` (hardcoded em 2 lugares)
- Token default antigo em `telegram_notifier.py` (linha 22)

**Depois:**
- ✅ **1 único bot**: `@ayria_tec_vps_bot` (id 8335265132)
- ✅ **1 único token**: lido de env var `TELEGRAM_BOT_TOKEN` (em `/etc/ayria/.env`, `/etc/ayria/.env-staging`, `/opt/ayria/backend/.env`)
- ✅ **1 único chat_id**: `779495783` (Rafael Peron, @Perontrader)
- ✅ Token default removido de `telegram_notifier.py:22`
- ✅ `stripe_billing.py` refatorado pra importar `BOT_TOKEN` e `ADMIN_CHAT_ID` de `telegram_notifier.py` (não lê mais de arquivo externo)
- ✅ `/home/peron/.telegram_bots.env` (caminho legado) **não é mais usado pelo AYRIA**

### Configuração (env vars)

Lidas em `/opt/ayria/backend/services/telegram_notifier.py` (linhas 22-23):

| Var | Padrão | Onde mora | Função |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `""` | `/etc/ayria/.env`, `/etc/ayria/.env-staging`, `/opt/ayria/backend/.env` | Token do bot `@ayria_tec_vps_bot` |
| `TELEGRAM_CHAT_ID` | `779495783` | mesmas 3 locations | Chat do admin (Rafael) |

**REGRA:** se `TELEGRAM_BOT_TOKEN` não configurado, todas as funções viram **no-op silenciosas** (nada quebra, só log).

### Código que usa Telegram (no VPS)

| # | Arquivo (no VPS) | Linha(s) | Função |
|---|---|---|---|
| 1 | `/opt/ayria/backend/services/telegram_notifier.py` (113 linhas) | 22-23, 69-112 | **Cliente Telegram principal**. Função `send_supervisor_alert(user_email, level, signals, content_excerpt, ia_confirmed, alert_id)`. POST em `https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage`, **sem parse_mode** (texto puro). **Best-effort** — erro NÃO derruba o chat. |
| 2 | `/opt/ayria/backend/routers/chat.py` | 701-714 | Importa `send_supervisor_alert`. Agenda em background task quando supervisor detecta risco. |
| 3 | `/opt/ayria/backend/routers/stripe_billing.py` | 740-820 | **Falha pagamento Stripe**. Importa `BOT_TOKEN` e `ADMIN_CHAT_ID` do `telegram_notifier` (não lê mais de arquivo externo). Usa `subprocess` + `curl`. |
| 4 | `/opt/ayria/backend/scripts/ayria_supervisor_batch.py` | 16 | Script batch offline. Processa backlog, notifica via Telegram. |

### Roteiro de rotação de token (se precisar)

Quando rotacionar `TELEGRAM_BOT_TOKEN`, atualizar **3 arquivos** (Regra 2 do MEMORY.md — systemd precisa de `EnvironmentFile`):

1. `/etc/ayria/.env` → `TELEGRAM_BOT_TOKEN=novo_token`
2. `/etc/ayria/.env-staging` → mesma coisa
3. `/opt/ayria/backend/.env` → mesma coisa (cópia, pydantic-settings lê daqui)
4. Restart backend: `systemctl restart ayria-backend ayria-backend-staging`
5. Validar: `cat /proc/$(pgrep -f uvicorn)/environ | tr '\0' '\n' | grep TELEGRAM`

### Teste rápido (validar envio)

```bash
TOKEN=$(grep "^TELEGRAM_BOT_TOKEN=" /etc/ayria/.env | cut -d= -f2-)
curl -s "https://api.telegram.org/bot${TOKEN}/getMe"
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" -d "chat_id=779495783" -d "text=🟢 teste"
```

### Documentação no VPS que menciona Telegram

| Arquivo (no VPS) | Linha | Contexto |
|---|---|---|
| `/opt/ayria/DOCSSYSIA/01-STATUS-ATUAL.md` | 54 | Pendência monitor Telegram |
| `/opt/ayria/DOCSSYSIA/12-MONITOR-PLANO.md` | 16, 29, 36, 90-97, 126 | Plano completo (NÃO implementado). Quando implementar, usar mesmo `TELEGRAM_BOT_TOKEN`. |
| `/opt/ayria/DOCSSYSIA/04-CREDENCIAIS-LOCALIZACAO.md` | 55-58 | Lista `/home/peron/.telegram_bots.env` como localização local — **ATUALIZAR 16/08**: arquivo local não é mais usado pelo AYRIA. Token agora mora em `/etc/ayria/.env`. |
| `/opt/ayria/backend/prompts/prompt_saude_mental_br.md` | 132 | "Telegram: alguns grupos de apoio" — referência pra AYRIA citar em conversa (NÃO código). |

---

## 🔧 PARTE 4 — CHECKLIST DE ALTERAÇÃO (atualizado)

- [x] ✅ 16/08/2026 — Token consolidado em 1 só lugar (`/etc/ayria/.env`)
- [x] ✅ 16/08/2026 — `stripe_billing.py` não lê mais de arquivo externo
- [x] ✅ 16/08/2026 — Chat_id `779495783` é o único destino
- [ ] Pendente — implementar monitor de saúde (cron 5min + alerta Telegram — ver `12-MONITOR-PLANO.md`)

---

## 📌 NOTAS ATUALIZADAS

- 🔒 Token agora **só** em `/etc/ayria/.env` (e cópia em staging/backend). **Removido** `/home/peron/.telegram_bots.env` da lista de fontes.
- 🤖 Bot atual: `@ayria_tec_vps_bot` (id 8335265132)
- 👤 Chat destino: `779495783` (Rafael Peron, @Perontrader)
- ⚡ Telegram continua best-effort — se API cair, chat não quebra. Erro vira log.
- 🔀 Agora existe **1 caminho** Telegram só (consolidado).

---

**Próxima atualização:** quando monitor de saúde for implementado ou novos usos do Telegram aparecerem.
