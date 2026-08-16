# 13 — Como adicionar/remover usuário SSH na VPS AYRIA

## Estrutura atual

- **Porta:** 2222 (NÃO 22)
- **Autenticação:** chave ed25519 apenas (PasswordAuthentication no)
- **Chave atual:** `~/.ssh/ayria-prod-DE-ed25519` (user `peron` local)
- **User atual na VPS:** root

## Adicionar novo usuário SSH

### Passo 1 — Gerar par de chaves (na máquina do novo usuário)

```bash
# Na máquina do NOVO usuário (não na VPS!)
ssh-keygen -t ed25519 -f ~/.ssh/ayria-prod-NOVO-ed25519 -C "novo@maquina"
# Vai criar ~/.ssh/ayria-prod-NOVO-ed25519 (privada) e .pub (pública)
```

### Passo 2 — Copiar chave pública pra VPS

```bash
# Método 1: ssh-copy-id
ssh-copy-id -i ~/.ssh/ayria-prod-NOVO-ed25519.pub \
  -p 2222 root@179.198.127.230

# Método 2: manual
cat ~/.ssh/ayria-prod-NOVO-ed25519.pub | \
  ssh -p 2222 root@179.198.127.230 \
  "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### Passo 3 — Testar login

```bash
ssh -i ~/.ssh/ayria-prod-NOVO-ed25519 -p 2222 root@179.198.127.230 "echo OK; hostname; date"
```

### (Opcional) Criar user dedicado ao invés de root

```bash
# Na VPS
useradd -m -s /bin/bash novoadmin
mkdir -p /home/novoadmin/.ssh
# Copiar chave pública
nano /home/novoadmin/.ssh/authorized_keys
chmod 700 /home/novoadmin/.ssh
chmod 600 /home/novoadmin/.ssh/authorized_keys
chown -R novoadmin:novoadmin /home/novoadmin/.ssh

# Sudo (se precisar de root)
apt install -y sudo
usermod -aG sudo novoadmin
```

## Remover usuário SSH

```bash
# Na VPS
# 1. Remover chave pública do authorized_keys
ssh -p 2222 root@179.198.127.230 \
  "nano ~/.ssh/authorized_keys"  # apagar linha do usuário X

# OU remover user inteiro:
userdel -r usuarioantigo
```

## Rotação de chaves (segurança)

A cada 6-12 meses, ou se comprometida:

1. Gerar novo par (Passo 1 acima)
2. Adicionar chave nova (Passo 2)
3. **Testar login com chave nova ANTES de remover a antiga**
4. Remover chave antiga do `authorized_keys`
5. Manter chave antiga por 7 dias como contingência

## Backup das chaves (importante!)

⚠️ **NÃO perder as chaves** = perder acesso à VPS.

```bash
# Backup local
cp -r ~/.ssh /home/peron/backups/ssh-keys-$(date +%Y%m%d)/

# Ou criptografado (recomendado):
tar czf - ~/.ssh | gpg -c > /home/peron/backups/ssh-keys-$(date +%Y%m%d).tar.gz.gpg
```

## Recuperação em caso de perda total das chaves

Último recurso — precisa acesso ao **console da Hostinger** (não SSH):

1. Login em https://hpanel.hostinger.com
2. VPS → seu servidor → **Acesso → Console** (abre terminal direto na VPS)
3. Adicionar nova chave:
   ```bash
   mkdir -p ~/.ssh
   echo "ssh-ed25519 AAAA... nova-chave-pública" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
4. Sair do console e testar SSH da máquina local

## Endurecimento recomendado (não aplicado ainda)

- [ ] Mudar `PermitRootLogin yes` → `PermitRootLogin prohibit-password` (ou `no`)
- [ ] Instalar `fail2ban` já feito ✅
- [ ] Configurar `AllowUsers` específico no sshd_config
- [ ] Desabilitar `X11Forwarding`
- [ ] Mudar porta SSH periodicamente (security through obscurity)