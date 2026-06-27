#!/usr/bin/env bash
# AYRIA - Stop script

set -e
cd "$(dirname "$0")"

echo "🛑 AYRIA - Stop"
echo ""

echo "▶ Parando Vite..."
pkill -f "vite --host" 2>/dev/null && echo "  ✅ Vite parado" || echo "  (Vite não estava rodando)"

echo "▶ Parando containers Docker..."
docker compose stop

echo ""
echo "✅ Tudo parado."
echo ""
echo "Para subir de novo: ./start.sh"