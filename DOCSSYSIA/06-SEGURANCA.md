# Segurança (14/08/2026)

## UFW (firewall) — portas liberadas

```
22 (SSH) — originalmente, mas SSH tá em 2222
80 (HTTP) — redirect pra HTTPS
443 (HTTPS) — Caddy
2222 (SSH) — porta real do SSH

BLOQUEADAS: tudo o resto (incluindo 5432 Postgres, 6333/6334 Qdrant)
```

## SSH (porta 2222, chave ed25519)

- **Porta:** 2222 (NÃO 22 — segurança por obscuridade + evita brute force)
- **Chave local:** `~/.ssh/ayria-prod-DE-ed25519`
- **User:** root (não criar user dedicado por enquanto)
- **Sem password login:** `PasswordAuthentication no` no sshd_config
- **Root password:** trocado em 13/08 (não documentar valor aqui)

## Fail2ban

- Jail ativo: `sshd`
- Monitora tentativas falhas de SSH
- Bane IP após 5 falhas por 1h
- Status: `fail2ban-client status sshd`

## SSL/TLS

- **Cert atual:** auto-assinado (criado em 13/08, válido até 14/08/2027)
- **SAN:** ayria.online, www.ayria.online, teste.ayria.online
- **Cloudflare SSL mode:** Full (NÃO Strict) — aceita cert auto-assinado
- **⚠️ Pra Strict:** gerar Origin Cert (ver 05-DNS-CLOUDFLARE.md)

## Permissões de arquivos sensíveis

| Arquivo | Perm | Owner |
|---|---|---|
| `/etc/ayria/.env` | 600 | root:ayria-app |
| `/etc/ayria/.env-staging` | 600 | root:ayria-app |
| `/opt/ayria/backend/.env` | 640 | ayria-app:ayria-app |
| `/etc/ssl/ayria/cert.pem` | 644 | caddy:caddy |
| `/etc/ssl/ayria/key.pem` | 640 | caddy:caddy |
| `/opt/ayria/backend/` | 755 | root:root (ayria-app lê) |
| `/opt/ayria/.venv/` | 755 | root:root (ayria-app lê) |
| `/var/log/ayria/` | 755 | ayria-app:ayria-app |

## ⚠️ NÃO MEXER (regras absolutas do MEMORY.md)

- ❌ **NÃO mexer no Mikrotik** (rede do Rafael) — jamais criar/editar regra NAT/filtro/mangle
- ❌ **NÃO fazer commit sem push** — sempre `git push origin main`
- ❌ **NÃO downgradar PG sem autorização** — manter mesma versão do local
- ❌ **NÃO usar Docker** pra AYRIA em produção — sempre nativo
- ❌ **NÃO postar em redes sociais sem aprovação** do Rafael
