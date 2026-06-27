#!/usr/bin/env bash
# AYRIA - Start script completo
# Sobe backend (docker) + frontend (vite no host)

set -e
cd "$(dirname "$0")"

echo "🌙 AYRIA - Start"
echo ""

# 1. Docker containers
echo "▶ Subindo containers Docker (postgres + qdrant + backend)..."
docker compose up -d

# 2. Aguardar backend ficar healthy
echo "▶ Aguardando backend ficar healthy..."
for i in {1..30}; do
  if curl -s http://localhost:8000/health | grep -q '"status":"ok"'; then
    echo "✅ Backend OK"
    break
  fi
  sleep 2
done

# 3. Iniciar Vite
echo "▶ Iniciando Vite (frontend)..."
cd frontend
if [ ! -d node_modules ]; then
  echo "  Instalando dependências..."
  npm install --no-audit --no-fund
fi

# Matar Vite anterior se existir
pkill -f "vite --host" 2>/dev/null || true
sleep 1

nohup npm run dev > /tmp/ayria-frontend.log 2>&1 < /dev/null &
disown

# 4. Aguardar frontend
echo "▶ Aguardando frontend..."
for i in {1..20}; do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/ 2>/dev/null | grep -q "200"; then
    echo "✅ Frontend OK"
    break
  fi
  sleep 2
done

echo ""
echo "🌙 AYRIA RODANDO!"
echo ""
echo "  Frontend:    http://localhost:5173"
echo "  Frontend IP: http://192.168.3.37:5173"
echo "  Backend:     http://localhost:8000/docs"
echo "  Qdrant:      http://localhost:6333/dashboard"
echo ""
echo "  Login:       admin@ayria.local / admin123"
echo ""
echo "Logs frontend: tail -f /tmp/ayria-frontend.log"
echo "Logs backend:  docker logs -f ayria-backend"
echo ""
echo "Para parar tudo: ./stop.sh"