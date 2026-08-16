# 12 — Monitor de saúde do AYRIA (PLANO, ainda não implementado)

⚠️ **Não tem rotina automática ainda.** Aqui está o PLANO.

## O que monitorar

| Item | Como | Frequência |
|---|---|---|
| **Backend `/health`** | `curl https://ayria.online/health` | A cada 5min |
| **Backend staging `/health`** | `curl https://teste.ayria.online/health` | A cada 5min |
| **PostgreSQL** | `pg_isready` ou psql connect | A cada 15min |
| **Qdrant** | `curl http://127.0.0.1:6333/` | A cada 15min |
| **Disco** | `df -h / \| awk '{print $5}' \| grep -v Use \| head -1` | A cada 1h |
| **Memória** | `free -m \| awk '/^Mem:/ {print $3}'` | A cada 1h |

## Plano: script + cron + Telegram

### Passo 1 — Script de healthcheck

```bash
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230

cat > /home/peron/bin/ayria-healthcheck.sh <<'EOF'
#!/bin/bash
# AYRIA healthcheck — alerta se cair
# Cron: */5 * * * *

ALERT_TELEGRAM="@avisos_perontec_bot"
TELEGRAM_TOKEN=$(grep "^AVISOS_TOKEN=" /home/peron/.telegram_bots.env | cut -d= -f2-)
TELEGRAM_CHAT="779495783"
FAIL_COUNT_FILE=/tmp/ayria-health-fail-count
[ -f "$FAIL_COUNT_FILE" ] || echo 0 > "$FAIL_COUNT_FILE"

send_alert() {
    local msg="$1"
    curl -sk -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT}" \
        -d "text=🚨 AYRIA ALERTA: ${msg}" \
        -d "parse_mode=HTML" > /dev/null
}

check() {
    local name="$1" url="$2"
    local code=$(curl -sk --connect-timeout 10 -o /dev/null -w "%{http_code}" "$url")
    if [ "$code" != "200" ]; then
        echo "[$(date '+%H:%M:%S')] ❌ ${name}: HTTP ${code}"
        return 1
    else
        echo "[$(date '+%H:%M:%S')] ✅ ${name}: HTTP ${code}"
        return 0
    fi
}

# Checks
FAIL=0
check "ayria.online/health" "https://ayria.online/health" || FAIL=1
check "teste.ayria.online/health" "https://teste.ayria.online/health" || FAIL=1

# PG
if ! PGPASSWORD='AyR1a_Pr0d_2026!Secure' psql -h 127.0.0.1 -U ayria -d ayria -tAc "SELECT 1" > /dev/null 2>&1; then
    echo "[$(date '+%H:%M:%S')] ❌ postgres ayria db"
    FAIL=1
fi

# Qdrant
code=$(curl -sk --connect-timeout 5 -o /dev/null -w "%{http_code}" http://127.0.0.1:6333/)
if [ "$code" != "200" ]; then
    echo "[$(date '+%H:%M:%S')] ❌ qdrant: HTTP ${code}"
    FAIL=1
fi

# Alerta só após 3 falhas seguidas (evitar ruído)
COUNT=$(cat "$FAIL_COUNT_FILE")
if [ $FAIL -eq 0 ]; then
    echo 0 > "$FAIL_COUNT_FILE"
elif [ $COUNT -ge 3 ]; then
    send_alert "Healthcheck falhou ${COUNT}x seguidas. Ver logs."
    echo $(($COUNT + 1)) > "$FAIL_COUNT_FILE"
else
    echo $(($COUNT + 1)) > "$FAIL_COUNT_FILE"
fi
EOF
chmod +x /home/peron/bin/ayria-healthcheck.sh

# Cron (root)
echo "*/5 * * * * /home/peron/bin/ayria-healthcheck.sh >> /var/log/ayria/healthcheck.log 2>&1" \
  | sudo crontab -
```

### Passo 2 — Alertas Telegram

Token Telegram do `@avisos_perontec_bot` já tá em `/home/peron/.telegram_bots.env` (var `AVISOS_TOKEN`).

Para testar:
```bash
TELEGRAM_TOKEN=$(grep "^AVISOS_TOKEN=" /home/peron/.telegram_bots.env | cut -d= -f2-)
curl -X POST "https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage" \
  -d "chat_id=779495783" \
  -d "text=🚨 AYRIA healthcheck OK — $(date)"
```

### Passo 3 — Logs centralizados

Para debug rápido quando cair:
```bash
# Logs em tempo real
journalctl -u ayria-backend -f
journalctl -u caddy -f
tail -f /var/log/caddy/ayria.log
```

## Plano alternativo: UptimeRobot (externo, mais simples)

1. Criar conta em https://uptimerobot.com (free)
2. Adicionar monitor HTTP(s):
   - URL 1: `https://ayria.online/health` (esperado: 200 + body com "ok")
   - URL 2: `https://teste.ayria.online/health`
3. Configurar alerta por email (grátis) ou webhook (pro)

Vantagem: monitor externo, não depende da VPS estar no ar.

## Pendente

- ❌ Implementar healthcheck.sh
- ❌ Criar cron
- ❌ Testar alerta Telegram
- ❌ Configurar UptimeRobot (alternativa)