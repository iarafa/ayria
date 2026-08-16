# Procedimentos de deploy, restart e debug

## Restart de cada serviço

```bash
# Backend produção
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "systemctl restart ayria-backend && sleep 5 && systemctl status ayria-backend --no-pager | head -10"

# Backend staging
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "systemctl restart ayria-backend-staging && sleep 5 && systemctl status ayria-backend-staging --no-pager | head -10"

# Caddy (sempre que mudar Caddyfile)
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "caddy fmt --overwrite /etc/caddy/Caddyfile && caddy validate --config /etc/caddy/Caddyfile && systemctl restart caddy"

# PostgreSQL
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "pg_lsclusters && pg_ctlcluster 18 main restart"

# Qdrant (sem systemd unit — rodar manualmente)
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "pkill -f /opt/qdrant/qdrant; nohup /opt/qdrant/start.sh > /var/log/qdrant/qdrant.log 2>&1 & disown"
```

## Deploy de novo código AYRIA

```bash
# 1. Atualizar código via git
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "cd /opt/ayria && git pull origin feature/sub-alma-user"

# 2. Se requirements.txt mudou, reinstalar
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "/opt/ayria/.venv/bin/pip install -r /opt/ayria/backend/requirements.txt"

# 3. Se frontend mudou, rebuild
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "cd /opt/ayria/frontend && npm install --silent && npm run build"

# 4. Restart backend
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "systemctl restart ayria-backend && sleep 5"
```

## Verificação de saúde (checklist)

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"
echo "=== HEALTH CHECK ==="
echo "site:    $($VPS 'systemctl is-active caddy')"
echo "prod:    $($VPS 'systemctl is-active ayria-backend')"
echo "staging: $($VPS 'systemctl is-active ayria-backend-staging')"
echo "pg:      $($VPS 'pg_lsclusters | grep main | awk "{print \$3, \$4}"')"
echo "qdrant:  $($VPS 'ps -p $(pgrep -f /opt/qdrant/qdrant) -o rss= 2>/dev/null && echo MB')"
echo ""
echo "=== URLs ==="
curl -sk --connect-timeout 5 -o /dev/null -w 'https://ayria.online/ → %{http_code}\n' https://ayria.online/
curl -sk --connect-timeout 5 -o /dev/null -w 'https://teste.ayria.online/ → %{http_code}\n' https://teste.ayria.online/
curl -sk --connect-timeout 5 https://ayria.online/health
echo ""
curl -sk --connect-timeout 5 https://teste.ayria.online/health
```

## Onde estão os logs

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"

# Logs em tempo real
$VPS "journalctl -u ayria-backend -f"           # backend prod
$VPS "journalctl -u ayria-backend-staging -f"   # backend staging
$VPS "journalctl -u caddy -f"                    # Caddy
$VPS "tail -f /var/log/caddy/ayria.log"          # Caddy access log prod
$VPS "tail -f /var/log/caddy/staging.log"        # Caddy access log staging
$VPS "tail -f /opt/qdrant/qdrant.log"             # Qdrant (se rodando via start.sh)
$VPS "tail -f /var/log/postgresql/postgresql-18-main.log"  # PG

# Logs de email
$VPS "journalctl -u ayria-backend | grep -i 'email\\|turbo\\|smtp'"
```

## Aplicar migrations AYRIA no banco

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"
$VPS "PGPASSWORD='AyR1a_Pr0d_2026!Secure' psql -h 127.0.0.1 -U ayria -d ayria -f /opt/ayria/backend/migrations/00X_nome.sql"
```
