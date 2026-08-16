# Troubleshooting — problemas comuns e soluções

## "502 Bad Gateway" no https://ayria.online/

**Causa:** backend uvicorn caiu ou não tá escutando
**Solução:**
```bash
VPS="ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230"
$VPS "systemctl status ayria-backend"
$VPS "ss -tlnp | grep ':8000'"   # confirma se uvicorn tá escutando
$VPS "journalctl -u ayria-backend --no-pager -n 30"  # ver erro
$VPS "systemctl restart ayria-backend"
```

## "Connection refused" no Postgres

**Causa:** PG caiu
**Solução:**
```bash
$VPS "pg_lsclusters"
$VPS "pg_ctlcluster 18 main start"
```

## Caddy não sobe após editar Caddyfile

**Solução:**
```bash
$VPS "caddy fmt --overwrite /etc/caddy/Caddyfile && caddy validate --config /etc/caddy/Caddyfile"
# Se erro, ler a mensagem e corrigir Caddyfile
$VPS "systemctl restart caddy"
```

## Email não chega após signup

**Checklist:**
1. `TURBOSMTP_*` no `/etc/ayria/.env` E no `/proc/<uvicorn_pid>/environ`?
2. systemd tem `EnvironmentFile=/etc/ayria/.env`? (REGRAS MEMORY.md 14/08)
3. Backend log mostra "✅ Email enviado"? (não só resposta 201)
4. Sandbox do TurboSMTP bloqueando domínio `ayria.online`?
5. DNS MX de `tecia.app` configurado?

## Stripe webhook retorna 400 "Assinatura HMAC inválida"

**Causa:** signing secret errado ou não bate com o do Stripe Dashboard
**Solução:**
1. Verificar `STRIPE_WEBHOOK_SECRET` no `.env` da VPS
2. Comparar com signing secret do webhook criado no Dashboard Stripe
3. Se diferente, atualizar `.env` + restart

## Frontend retornando HTML em /api/* (deveria ser JSON)

**Causa:** reverse_proxy do Caddy não tá aplicando matcher
**Solução:**
```bash
# Verificar que o Caddyfile usa @backend + handle @backend ANTES do handle SPA
# Estrutura obrigatória:
#   handle @backend { reverse_proxy 127.0.0.1:8000 }
#   handle { root * /opt/ayria/frontend/dist; file_server }
```

## Login renderiza mas email não valida

**Causa:** TurboSMTP fora do ar OU credenciais erradas
**Solução:**
1. `curl -sk -u "KEY:SECRET" https://api.turbo-smtp.com/api/v2/info` — testa API
2. Se 401, credenciais erradas
3. Se 200, problema no envio

## Banco tá com schema desatualizado (migrations pendentes)

**Solução:**
```bash
$VPS "PGPASSWORD='AyR1a_Pr0d_2026!Secure' psql -h 127.0.0.1 -U ayria -d ayria -c '\\dt'"
# Comparar com migrations em /opt/ayria/backend/migrations/
# Aplicar pendentes:
$VPS "PGPASSWORD='AyR1a_Pr0d_2026!Secure' psql -h 127.0.0.1 -U ayria -d ayria -f /opt/ayria/backend/migrations/00X.sql"
```

## Disco cheio

**Solução:**
```bash
$VPS "df -h /"
# Logs antigos:
$VPS "journalctl --vacuum-size=200M"
$VPS "rm -f /var/log/caddy/*.log.*"
$VPS "rm -rf /opt/ayria/.venv/lib/python3.12/site-packages/*.dist-info"  # cache pip
```

## Senha SSH perdida / chave privada corrompida

**Último recurso:** acessar via console do Hostinger (VPS) e:
```bash
# Resetar authorized_keys (precisa console)
# Ou adicionar nova chave pública
echo "ssh-ed25519 AAAA... usuario@maquina" >> /root/.ssh/authorized_keys
systemctl restart ssh
```
