# 15 — Cloudflare Origin Certificate (SSL Strict real)

⚠️ **NÃO está aplicado ainda.** O cert atual é auto-assinado (funciona com Cloudflare SSL = Full). Origin Cert permite usar SSL = Full Strict, que valida o cert no handshake.

## Por que trocar

| Modo | Como funciona | Risco |
|---|---|---|
| **Full** (atual) | Cloudflare aceita QUALQUER cert (inclusive auto-assinado) | Alguém com o IP do VPS poderia falar direto com Caddy sem Cloudflare no meio |
| **Full (Strict)** | Cloudflare exige cert válido assinado por CA confiável | IP do VPS fica escondido E handshake é validado |

## Procedimento passo-a-passo

### 1. Gerar Origin Certificate no painel Cloudflare

1. Login em https://dash.cloudflare.com
2. Selecionar domínio `ayria.online`
3. Menu **SSL/TLS** → aba **Origin Server**
4. Botão **Create Certificate**
5. Configurar:
   - **Hostnames:** `*.ayria.online`, `ayria.online` (cobre todos os subdomínios)
   - **Validity:** 15 years (recomendado)
6. Clicar **Create**
7. Vai aparecer uma tela com 2 blocos:
   - **Origin Certificate** (-----BEGIN CERTIFICATE-----...)
   - **Private Key** (-----BEGIN PRIVATE KEY-----...)
8. **Copiar AMBOS** (não fechar a tela sem copiar — chave privada some)

### 2. Colar no VPS

```bash
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230

# Backup do cert atual
cp /etc/ssl/ayria/cert.pem /etc/ssl/ayria/cert.pem.autoassinado.bak
cp /etc/ssl/ayria/key.pem /etc/ssl/ayria/key.pem.autoassinado.bak

# Colar novo cert (substituir conteúdo)
nano /etc/ssl/ayria/cert.pem
# Cola o "Origin Certificate" aqui. Salvar.

nano /etc/ssl/ayria/key.pem
# Cola o "Private Key" aqui. Salvar.

# Perms
chmod 644 /etc/ssl/ayria/cert.pem
chown caddy:caddy /etc/ssl/ayria/key.pem
chmod 640 /etc/ssl/ayria/key.pem
```

### 3. Restart Caddy

```bash
systemctl restart caddy
sleep 2
systemctl status caddy
ss -tlnp | grep -E ':(80|443)'
```

### 4. Mudar Cloudflare SSL/TLS pra Strict

1. Voltar pro painel Cloudflare
2. **SSL/TLS** → **Overview**
3. Selecionar **Full (Strict)** (NÃO Full — esse é o atual)
4. Aguardar 30s

### 5. Validar

```bash
# Testar conexão TLS via Cloudflare
curl -sv https://ayria.online/health 2>&1 | grep -iE "(server|issuer|verify)"
# Esperado: ver Cloudflare no caminho, cert apresentado pelo Caddy válido

# Testar via OpenSSL direto
echo | openssl s_client -connect ayria.online:443 -servername ayria.online 2>/dev/null | openssl x509 -noout -subject -issuer -dates
# subject deve ser CN=*.ayria.online (ou similar)
# issuer deve ser "Cloudflare Origin SSL CA" (NÃO auto-assinado)
```

### 6. Limpar backups antigos (opcional, depois de confirmar que tá tudo OK)

```bash
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230
rm /etc/ssl/ayria/cert.pem.autoassinado.bak
rm /etc/ssl/ayria/key.pem.autoassinado.bak
```

## Renovação

Origin Certs do Cloudflare valem 15 anos. Quando faltar 30 dias pra expirar:
1. Gerar novo cert (Passo 1)
2. Colar no VPS (Passo 2)
3. Restart Caddy (Passo 3)

Não precisa mudar nada no Cloudflare SSL/TLS — o cert novo vai ser aceito automaticamente.

## Rollback (se der ruim)

```bash
# Voltar cert auto-assinado
ssh -i ~/.ssh/ayria-prod-DE-ed25519 -p 2222 root@179.198.127.230

cp /etc/ssl/ayria/cert.pem.autoassinado.bak /etc/ssl/ayria/cert.pem
cp /etc/ssl/ayria/key.pem.autoassinado.bak /etc/ssl/ayria/key.pem
chown caddy:caddy /etc/ssl/ayria/key.pem
systemctl restart caddy

# Voltar Cloudflare SSL/TLS pra Full
# (no painel: SSL/TLS → Overview → Full)
```

## Pendente

- ❌ Gerar Origin Cert (precisa ação do Rafael no painel Cloudflare)
- ❌ Colar no VPS
- ❌ Mudar SSL/TLS pra Strict
- ❌ Validar handshake