#!/bin/sh
set -e

# Carrega secrets auxiliares (secrets em .env são passados via docker run -e)
# Esse arquivo .turbo-secrets.env fica em /app/ (copiado via volume no docker run)
if [ -f /app/.turbo-secrets.env ]; then
    echo "[start.sh] Carregando /app/.turbo-secrets.env"
    set -a
    . /app/.turbo-secrets.env
    set +a
fi

# Sobe uvicorn em background e nginx em foreground (pid 1)
mkdir -p /app/logs
cd /app
echo "[start.sh] Subindo uvicorn na 127.0.0.1:8000..."
uvicorn main:app --host 127.0.0.1 --port 8000 >> /app/logs/ayria.log 2>&1 &

UVI_PID=$!
echo "[start.sh] uvicorn pid=$UVI_PID"

# Esperar uvicorn ficar disponível (max 60s)
for i in $(seq 1 60); do
    if curl -fs http://127.0.0.1:8000/health > /dev/null 2>&1; then
        echo "[start.sh] uvicorn OK após ${i}s"
        break
    fi
    if ! kill -0 $UVI_PID 2>/dev/null; then
        echo "[start.sh] uvicorn MORREU. Logs:"
        tail -50 /app/logs/ayria.log
        exit 1
    fi
    sleep 1
done

echo "[start.sh] Subindo nginx em foreground..."
nginx -g "daemon off;"