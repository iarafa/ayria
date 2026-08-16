# 10 — Setup completo do zero (AYRIA em VPS Hostinger)

Documenta COMO instalar tudo do zero, caso precise reinstalar ou criar nova VPS.

## 1. VPS base (Ubuntu 26.04 LTS)

```bash
# Após criar VPS no painel Hostinger, primeiro acesso via console
passwd                                    # 1. trocar senha root

# 2. Configurar SSH (porta 2222, chave ed25519, sem password login)
apt update && apt install -y openssh-server
sed -i 's/^#Port 22/Port 2222/' /etc/ssh/sshd_config
sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh

# 3. Liberar UFW
apt install -y ufw fail2ban
ufw allow 2222/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP Caddy'
ufw allow 443/tcp comment 'HTTPS Caddy'
ufw --force enable
systemctl enable fail2ban
```

## 2. PostgreSQL 18 (mesma versão do AYRIA local)

```bash
# Adicionar repo oficial pgdg
apt install -y postgresql-common
/usr/share/postgresql-common/pgdg/apt.postgresql.org.sh
wget --quiet -O- https://www.postgresql.org/media/keys/ACCC4CF8.asc \
  | gpg --dearmor -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list
apt update
apt install -y postgresql-18 postgresql-contrib-18

pg_createcluster 18 main
pg_ctlcluster 18 main start

# Criar user + db AYRIA
sudo -u postgres psql <<SQL
CREATE USER ayria WITH PASSWORD 'AyR1a_Pr0d_2026!Secure';
CREATE DATABASE ayria OWNER ayria;
GRANT ALL PRIVILEGES ON DATABASE ayria TO ayria;
SQL
```

## 3. Qdrant (vector DB)

```bash
mkdir -p /opt/qdrant
cd /opt/qdrant
QDRANT_VERSION="v1.12.4"
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && QDRANT_ARCH="x86_64-unknown-linux-musl" || QDRANT_ARCH="aarch64-unknown-linux-musl"
curl -sL -o qdrant.tar.gz "https://github.com/qdrant/qdrant/releases/download/${QDRANT_VERSION}/qdrant-${QDRANT_ARCH}.tar.gz"
tar -xzf qdrant.tar.gz
chmod +x qdrant
mkdir -p /var/lib/qdrant /var/log/qdrant

cat > /etc/qdrant-config.yaml <<EOF
storage:
  storage_path: /var/lib/qdrant
service:
  host: 127.0.0.1
  http_port: 6333
  grpc_port: 6334
  enable_cors: true
log:
  level: INFO
EOF

cat > /opt/qdrant/start.sh <<EOF
#!/bin/bash
cd /opt/qdrant
exec ./qdrant --config-path /etc/qdrant-config.yaml
EOF
chmod +x /opt/qdrant/start.sh

nohup /opt/qdrant/start.sh > /var/log/qdrant/qdrant.log 2>&1 & disown
sleep 5
curl -s http://127.0.0.1:6333/  # deve retornar JSON
```

## 4. Caddy + cert auto-assinado

```bash
# Repo oficial Caddy
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian/debian-archive-keyring.gpg' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-debian-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/caddy-stable-archive-keyring.gpg] https://dl.cloudsmith.io/public/caddy/stable/debian any-version main" \
  > /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy

# Cert auto-assinado (SAN: ayria.online + www + teste)
mkdir -p /etc/ssl/ayria
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout /etc/ssl/ayria/key.pem \
  -out /etc/ssl/ayria/cert.pem \
  -days 365 \
  -subj "/C=BR/ST=SP/L=Itatiba/O=Peron Tecnologia/OU=AYRIA/CN=ayria.online" \
  -addext "subjectAltName=DNS:ayria.online,DNS:www.ayria.online,DNS:teste.ayria.online"
chown -R caddy:caddy /etc/ssl/ayria
chmod 644 /etc/ssl/ayria/cert.pem
chmod 640 /etc/ssl/ayria/key.pem
```

## 5. Python 3.12 + clone AYRIA

```bash
# Python 3.12 (Ubuntu 26.04 só tem 3.14, sem wheels p/ AYRIA)
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.12 python3.12-venv python3.12-dev python3-dev build-essential libpq-dev

# Clone
cd /opt
git clone -b feature/sub-alma-user https://github.com/iarafa/ayria.git

# venv
python3.12 -m venv /opt/ayria/.venv
/opt/ayria/.venv/bin/pip install --upgrade pip
/opt/ayria/.venv/bin/pip install -r /opt/ayria/backend/requirements.txt
# Adicionar stripe (NÃO tá no requirements.txt)
/opt/ayria/.venv/bin/pip install stripe
```

## 6. Frontend build

```bash
apt install -y nodejs npm
cd /opt/ayria/frontend
npm install --silent
npm run build  # gera /opt/ayria/frontend/dist
```

## 7. User ayria-app + systemd

```bash
useradd --system --no-create-home --shell /usr/sbin/nologin ayria-app
mkdir -p /var/log/ayria /var/log/ayria-staging
chown ayria-app:ayria-app /var/log/ayria /var/log/ayria-staging

cat > /etc/systemd/system/ayria-backend.service <<EOF
[Unit]
Description=AYRIA Backend (FastAPI)
After=network.target
[Service]
Type=simple
User=ayria-app
Group=ayria-app
WorkingDirectory=/opt/ayria/backend
Environment="PATH=/opt/ayria/.venv/bin:/usr/local/bin:/usr/bin"
Environment="AYRIA_LOG_DIR=/var/log/ayria"
EnvironmentFile=/etc/ayria/.env
ExecStart=/opt/ayria/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now ayria-backend
```

## 8. .env + restaurar banco

```bash
mkdir -p /etc/ayria
# Gerar .env via Python (dotenv parser) — ver 04-CREDENCIAIS-LOCALIZACAO.md
# Copiar dump e restaurar:
PGPASSWORD='AyR1a_Pr0d_2026!Secure' psql -h 127.0.0.1 -U ayria -d ayria -f /tmp/ayria-dump.sql
```

## 9. Caddyfile

Ver `02-ARQUITETURA.md` para o Caddyfile completo. Depois:

```bash
caddy validate --config /etc/caddy/Caddyfile
systemctl restart caddy
```

## Tempo total esperado

~30min se tudo correr bem. Pontos de falha comuns:
- APT update falha (mirror lento) → trocar mirror
- pip install falha por wheel ausente → verificar Python 3.12 (3.14 não tem wheels p/ AYRIA)
- Caddyfile syntax → rodar `caddy fmt` antes de `validate`