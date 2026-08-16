# Comandos úteis (cheatsheet)

## Acesso à VPS

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"

# Interativo
$VPS

# Comando único
$VPS "comando aqui"

# Copiar arquivo
scp -P 2222 arquivo_local root@179.198.127.230:/tmp/
scp -P 2222 root@179.198.127.230:/tmp/arquivo ./
```

## Health check completo

```bash
#!/bin/bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"

echo "=== SERVIÇOS ==="
echo "caddy:    $($VPS 'systemctl is-active caddy')"
echo "ayria:    $($VPS 'systemctl is-active ayria-backend')"
echo "staging:  $($VPS 'systemctl is-active ayria-backend-staging')"
echo "postgres: $($VPS 'pg_lsclusters | grep main | awk "{print \$3, \$4}"')"
echo "qdrant:   $($VPS 'pgrep -f /opt/qdrant/qdrant && echo \"OK\"')"

echo ""
echo "=== URLs ==="
curl -sk --connect-timeout 5 -w 'ayria:    %{http_code}\n' -o /dev/null https://ayria.online/
curl -sk --connect-timeout 5 -w 'teste:    %{http_code}\n' -o /dev/null https://teste.ayria.online/
curl -sk --connect-timeout 5 https://ayria.online/health
echo ""
curl -sk --connect-timeout 5 https://teste.ayria.online/health
echo ""

echo ""
echo "=== RECURSOS ==="
$VPS "free -h | head -2"
$VPS "df -h / | tail -1"
$VPS "uptime -p"
```

## Banco de dados

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"
PG="PGPASSWORD='AyR1a_Pr0d_2026!Secure' psql -h 127.0.0.1 -U ayria -d ayria"

# Contagem de tabelas
$VPS "$PG -tAc 'SELECT count(*) FROM information_schema.tables WHERE table_schema='\''public'\'';"

# Tamanho do banco
$VPS "$PG -tAc \"SELECT pg_size_pretty(pg_database_size('ayria'));\""

# Listar usuários
$VPS "$PG -c 'SELECT email, is_verified, role, created_at FROM users ORDER BY created_at DESC LIMIT 10;'"

# Listar assinaturas Stripe
$VPS "$PG -c 'SELECT ayria_user_id, subscription_status, stripe_subscription_id, current_period_end FROM stripe_subscriptions;'"

# Aplicar migration
$VPS "$PG -f /opt/ayria/backend/migrations/00X_algumacoisa.sql"
```

## Stripe (TEST mode)

```bash
SEC=$(grep "^STRIPE_SECRET_KEY=" /home/peron/.openclaw/workspace/DOCSSYSIA/04-CREDENCIAIS-LOCALIZACAO.md > /dev/null; \
      ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
        "grep '^STRIPE_SECRET_KEY=' /etc/ayria/.env" | cut -d= -f2-)

# Saldo
curl -sk -u "${SEC}:" https://api.stripe.com/v1/balance | python3 -m json.tool

# Listar webhooks
curl -sk -u "${SEC}:" https://api.stripe.com/v1/webhook_endpoints

# Listar preços
curl -sk -u "${SEC}:" https://api.stripe.com/v1/prices | python3 -m json.tool
```

## Logs em tempo real

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"

$VPS "journalctl -u ayria-backend -f"
$VPS "journalctl -u ayria-backend-staging -f"
$VPS "journalctl -u caddy -f"
$VPS "tail -f /var/log/caddy/ayria.log"
$VPS "tail -f /opt/qdrant/qdrant.log"
```

## Backup rápido (manual — enquanto não tem cron)

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"
$VPS "PGPASSWORD='AyR1a_Pr0d_2026!Secure' pg_dump -h 127.0.0.1 -U ayria -d ayria -F c -f /tmp/ayria-backup-\$(date +%Y%m%d-%H%M).dump"
$VPS "ls -lh /tmp/ayria-backup-*.dump"
# Pra baixar:
scp -P 2222 root@179.198.127.230:/tmp/ayria-backup-*.dump ./
```

## Atualizar MEMORY.md + DOCSSYSIA + commit

```bash
# 1. Editar MEMORY.md
vim /home/peron/.openclaw/workspace/MEMORY.md

# 2. Atualizar docs em DOCSSYSIA
vim /home/peron/.openclaw/workspace/DOCSSYSIA/

# 3. Commit + push (NUNCA sem push!)
bash /home/peron/bin/ayria-commit-save "msg descritiva"
```

## Teste de email real

```bash
# Criar signup teste
curl -sk -X POST https://ayria.online/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke-'$$'@ayria.local","password":"Senha123!","name":"Smoke"}'

# Verificar log
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230 \
  "journalctl -u ayria-backend --no-pager -n 30 | grep -i 'email\|turbo'"
```

## Reiniciar tudo do zero (emergência)

```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"

$VPS "systemctl restart caddy ayria-backend ayria-backend-staging postgresql"

# Se ainda assim não funcionar:
$VPS "pkill -f /opt/qdrant/qdrant; nohup /opt/qdrant/start.sh > /var/log/qdrant/qdrant.log 2>&1 &"
```

