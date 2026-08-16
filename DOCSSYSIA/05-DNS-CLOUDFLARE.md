# DNS — Cloudflare (14/08/2026)

## Registros ativos

| Nome | Tipo | Conteúdo | Proxy | TTL |
|---|---|---|---|---|
| `ayria.online` | A | 179.198.127.230 | **ON** (laranja) | Auto |
| `www.ayria.online` | CNAME | ayria.online | **ON** | Auto |
| `ayria.online` | AAAA | 2a02:4780:6:e:cece1::1 | **ON** | Auto |
| `teste.ayria.online` | A | 179.198.127.230 | **ON** | Auto |
| `ayria.online` | MX | ayria.online | Somente DNS | Auto |

## ⚠️ Ainda NÃO configurado

- Cloudflare **Origin Certificate** (cert válido pra SSL Strict) — pendente
- `ayria.online` **TXT record** SPF/DKIM/DMARC (recomendado pra email) — pendente

## Como adicionar Origin Certificate (pra SSL Strict)

1. **No painel Cloudflare** → `ayria.online` → **SSL/TLS** → **Origin Server**
2. Clicar **Create Certificate**
   - Hostnames: `*.ayria.online`, `ayria.online`
   - Validity: 15 years
3. Copiar:
   - **Origin Certificate** (-----BEGIN CERTIFICATE-----...)
   - **Private Key** (-----BEGIN PRIVATE KEY-----...)
4. **Na VPS:**
   ```bash
   # Backup do cert atual
   cp /etc/ssl/ayria/cert.pem /etc/ssl/ayria/cert.pem.autoassinado.bak
   cp /etc/ssl/ayria/key.pem /etc/ssl/ayria/key.pem.autoassinado.bak
   
   # Colar novo cert (vim ou echo)
   vim /etc/ssl/ayria/cert.pem
   vim /etc/ssl/ayria/key.pem
   chmod 644 /etc/ssl/ayria/cert.pem
   chown caddy:caddy /etc/ssl/ayria/key.pem
   chmod 640 /etc/ssl/ayria/key.pem
   
   # Restart Caddy
   systemctl restart caddy
   ```
5. **No painel Cloudflare** → SSL/TLS → Overview → mudar pra **Full (Strict)**

## Cloudflare Tunnel (alternativa mais segura, sem expor IP)

Se quiser esconder o IP do VPS totalmente, dá pra usar Cloudflare Tunnel em vez de A record. Mas como já tá com proxy ON funcionando, não é urgente.
