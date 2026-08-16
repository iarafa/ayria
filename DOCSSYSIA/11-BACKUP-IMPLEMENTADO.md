# 11 — Backup AYRIA (IMPLEMENTADO)

✅ **Implementado e rodando.**

## O que é backupeado

| Item | Conteúdo | Tamanho típico |
|---|---|---|
| **Banco PostgreSQL `ayria`** | `pg_dump -Fc` (formato compactado) | ~1.4MB |
| **Código AYRIA** (`/opt/ayria/`) | tudo exceto `.venv`, `node_modules`, `.git`, `frontend/dist/assets` | ~8MB |
| **Credenciais** (`/etc/ayria/.env*`) | produção + staging | ~4KB |
| **Config Caddy** (`/etc/caddy/Caddyfile`) | vhosts ayria.online + teste | ~2KB |
| **Units systemd** (`/etc/systemd/system/ayria-backend*.service`) | prod + staging | ~2KB |
| **Cert TLS** (`/etc/ssl/ayria/`) | cert.pem + key.pem | ~3KB |
| **DOCSSYSIA** (esta pasta) | 17 docs | ~50KB |

## Frequência

**2x ao dia: 03:00 e 15:00** (cron `0 3,15 * * *`).

## Retenção

Últimos **7 dias** (full + db dump). Limpeza automática via `find ... -mtime +7 -delete`.

## Onde fica

```
/var/backups/ayria/
├── db/                        ← pg_dumps individuais
│   └── ayria-AAAAMMDD-HHMM.dump
├── full/                      ← tar.gz com TUDO
│   └── ayria-full-AAAAMMDD-HHMM.tar.gz
└── logs/backup.log            ← log de execução
```

## Script

`/home/peron/bin/ayria-full-backup.sh` (na VPS).

```bash
#!/bin/bash
set -euo pipefail
BACKUP_ROOT=/var/backups/ayria
DB_DIR="$BACKUP_ROOT/db"
FULL_DIR="$BACKUP_ROOT/full"
LOG="$BACKUP_ROOT/logs/backup.log"
KEEP_DAYS=7

mkdir -p "$DB_DIR" "$FULL_DIR"
TIMESTAMP=$(date +%Y%m%d-%H%M)

# Dump banco
DB_FILE="$DB_DIR/ayria-$TIMESTAMP.dump"
PGPASSWORD='AyR1a_Pr0d_2026!Secure' pg_dump \
  -h 127.0.0.1 -U ayria -d ayria -F c -b \
  -f "$DB_FILE" 2>>"$LOG"
echo "$(date '+%Y-%m-%d %H:%M:%S') DB OK: $DB_FILE" >> "$LOG"

# Full (código + configs + credenciais)
FULL_FILE="$FULL_DIR/ayria-full-$TIMESTAMP.tar.gz"
tar czf "$FULL_FILE" \
  --exclude='/opt/ayria/.venv' \
  --exclude='/opt/ayria/frontend/node_modules' \
  --exclude='/opt/ayria/.git' \
  /opt/ayria \
  /etc/ayria \
  /etc/caddy/Caddyfile \
  /etc/systemd/system/ayria-backend.service \
  /etc/systemd/system/ayria-backend-staging.service \
  /etc/ssl/ayria \
  /home/peron/bin/ayria-full-backup.sh \
  2>>"$LOG"
echo "$(date '+%Y-%m-%d %H:%M:%S') FULL OK: $FULL_FILE" >> "$LOG"

# Limpar > 7 dias
find "$DB_DIR" -name "ayria-*.dump" -mtime +$KEEP_DAYS -delete
find "$FULL_DIR" -name "ayria-full-*.tar.gz" -mtime +$KEEP_DAYS -delete
```

## Cron job

```bash
0 3,15 * * * /home/peron/bin/ayria-full-backup.sh >> /var/backups/ayria/logs/backup.log 2>&1
```

Configurado via `crontab -e` do root na VPS.

## Status atual (verificado em 14/08/2026 19:50)

- ✅ Script criado e executável
- ✅ Backup manual testado (`ayria-full-20260814-1950.tar.gz` = 8.6M, 402 arquivos)
- ✅ Restore end-to-end testado (32 tabelas, 37 users, 20MB em banco temporário)
- ✅ Cron ativo (próximas execuções: hoje 15:00, amanhã 03:00, etc)
- ✅ Log rodando em `/var/backups/ayria/logs/backup.log`

## Como restaurar (emergência)

### Restore do banco APENAS (rápido)

```bash
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230

# 1. Parar backend
systemctl stop ayria-backend

# 2. Escolher backup (mais recente ou específico)
ls -lh /var/backups/ayria/db/
# Ex: ayria-20260814-1500.dump

# 3. Dropar e recriar DB
sudo -u postgres psql <<SQL
DROP DATABASE ayria;
CREATE DATABASE ayria OWNER ayria;
GRANT ALL PRIVILEGES ON DATABASE ayria TO ayria;
SQL

# 4. Restaurar
PGPASSWORD='AyR1a_Pr0d_2026!Secure' pg_restore \
  -h 127.0.0.1 -U ayria -d ayria \
  --no-owner --no-acl \
  /var/backups/ayria/db/ayria-20260814-1500.dump

# 5. Subir backend
systemctl start ayria-backend

# 6. Validar
curl -s http://127.0.0.1:8000/health
# Esperado: {"status":"ok","database":"ok","environment":"production"}
```

### Restore FULL (banco + código + configs)

```bash
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230

# 1. Restaurar banco (passos acima)

# 2. Extrair FULL no /opt
cd /
tar xzf /var/backups/ayria/full/ayria-full-20260814-1500.tar.gz

# 3. Reinstalar deps Python (se mudou requirements)
/opt/ayria/.venv/bin/pip install -r /opt/ayria/backend/requirements.txt
/opt/ayria/.venv/bin/pip install stripe  # FALTA no requirements.txt

# 4. Rebuild frontend (se mudou)
/opt/ayria/frontend && npm install --silent && npm run build

# 5. Reload systemd (se mudou units)
systemctl daemon-reload

# 6. Restart backend
systemctl restart ayria-backend

# 7. Validar
curl -s http://127.0.0.1:8000/health
```

## Backup off-site (pendente)

⚠️ **Backups ficam só na VPS local.** Se o disco da VPS falhar, perde tudo.

Opções futuras:
- **rclone** → Google Drive / S3 / Backblaze
- **rsync** → outra VPS / NAS do Rafael
- **scp** → `/home/peron/backups/ayria/` local (já testado em parte)

Implementar quando Rafael priorizar.

## Pendente

- ❌ Backup off-site
- ✅ Implementação local (DONE)
- ❌ Alerta Telegram se backup falhar