#!/bin/bash
# AYRIA FULL backup — banco + código + configs + credenciais
# Roda 2x ao dia (03:00 e 15:00). Mantém últimos 7 dias.
# 🆕 18/08/2026 — Notifica Telegram em sucesso, falha e erro de espaço em disco.
set -uo pipefail

BACKUP_ROOT=/var/backups/ayria
DB_DIR="$BACKUP_ROOT/db"
FULL_DIR="$BACKUP_ROOT/full"
LOG="$BACKUP_ROOT/logs/backup.log"
KEEP_DAYS=7

# Carrega env vars (TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID) — fallback pra /etc/ayria/.env
if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    if [ -f /etc/ayria/.env ]; then
        source <(grep -E "^TELEGRAM_(BOT_TOKEN|CHAT_ID)=" /etc/ayria/.env)
    fi
fi

TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-779495783}"
HOSTNAME_SHORT=$(hostname -s)
TS_HUMAN=$(date '+%Y-%m-%d %H:%M:%S')

# ===== Função pra enviar Telegram =====
send_telegram() {
    local msg="$1"
    local emoji="$2"
    local tag="${3:-BACKUP}"
    if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] TELEGRAM_BOT_TOKEN não configurado — pulando envio de $tag" >> "$LOG"
        return 0
    fi
    local full_msg="${emoji} <b>${tag} AYRIA</b> [${HOSTNAME_SHORT}]
${msg}
🕐 ${TS_HUMAN}"
    # Resposta vem em JSON, silenciosa, timeout 10s
    curl -s --max-time 10 -X POST \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d "chat_id=${TELEGRAM_CHAT_ID}" \
        -d "parse_mode=HTML" \
        -d "disable_web_page_preview=true" \
        --data-urlencode "text=${full_msg}" \
        >> "$LOG" 2>&1 || echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] Falha ao enviar Telegram (não derruba backup)" >> "$LOG"
}

# ===== Handler de erro — qualquer falha notifica =====
on_error() {
    local exit_code=$?
    local line=$1
    send_telegram "❌ <b>FALHA</b> no backup AYRIA
Linha: ${line}
Exit code: ${exit_code}
Verifique: <code>tail -50 ${LOG}</code>" "🚨" "BACKUP-FAIL"
    exit "$exit_code"
}
trap 'on_error ${LINENO}' ERR

mkdir -p "$DB_DIR" "$FULL_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M)

# ===== 1. DUMP DO BANCO =====
DB_FILE="$DB_DIR/ayria-$TIMESTAMP.dump"
PGPASSWORD='AyR1a_Pr0d_2026!Secure' pg_dump \
  -h 127.0.0.1 -U ayria -d ayria -F c -b \
  -f "$DB_FILE" 2>>"$LOG"
DB_SIZE=$(du -h "$DB_FILE" | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') DB OK: $DB_FILE ($DB_SIZE)" >> "$LOG"

# ===== 2. BACKUP FULL =====
FULL_FILE="$FULL_DIR/ayria-full-$TIMESTAMP.tar.gz"
tar czf "$FULL_FILE" \
  --exclude='/opt/ayria/.venv' \
  --exclude='/opt/ayria/frontend/node_modules' \
  --exclude='/opt/ayria/.git' \
  --exclude='/opt/ayria/frontend/dist/assets' \
  --exclude='/var/log/caddy/*.log.*' \
  /opt/ayria \
  /etc/ayria \
  /etc/caddy/Caddyfile \
  /etc/systemd/system/ayria-backend.service \
  /etc/systemd/system/ayria-backend-staging.service \
  /etc/ssl/ayria \
  /home/peron/bin/ayria-full-backup.sh \
  2>>"$LOG"
FULL_SIZE=$(du -h "$FULL_FILE" | cut -f1)
echo "$(date '+%Y-%m-%d %H:%M:%S') FULL OK: $FULL_FILE ($FULL_SIZE)" >> "$LOG"

# ===== 3. Limpeza =====
find "$DB_DIR" -name "ayria-*.dump" -mtime +$KEEP_DAYS -delete
find "$FULL_DIR" -name "ayria-full-*.tar.gz" -mtime +$KEEP_DAYS -delete

DB_REMAIN=$(ls "$DB_DIR" 2>/dev/null | wc -l)
FULL_REMAIN=$(ls "$FULL_DIR" 2>/dev/null | wc -l)
DB_COUNT_USED=$(df -h / | tail -1 | awk '{print $5}')
echo "$(date '+%Y-%m-%d %H:%M:%S') Mantidos: $DB_REMAIN db + $FULL_REMAIN full (disco: ${DB_COUNT_USED})" >> "$LOG"

# ===== 4. Notificação de sucesso =====
# Calcula idade do backup mais antigo (em horas)
OLDEST_DB=$(ls -t "$DB_DIR"/*.dump 2>/dev/null | tail -1 | xargs -I {} stat -c %Y {} 2>/dev/null || echo 0)
if [ -n "$OLDEST_DB" ] && [ "$OLDEST_DB" != "0" ]; then
    NOW=$(date +%s)
    OLDEST_HOURS=$(( (NOW - OLDEST_DB) / 3600 ))
else
    OLDEST_HOURS="?"
fi

send_telegram "✅ Backup AYRIA concluído
• DB: <code>${DB_SIZE}</code> (mantidos: ${DB_REMAIN})
• Full: <code>${FULL_SIZE}</code> (mantidos: ${FULL_REMAIN})
• Mais antigo: ${OLDEST_HOURS}h
• Disco: ${DB_COUNT_USED} usado" "💾" "BACKUP-OK"
