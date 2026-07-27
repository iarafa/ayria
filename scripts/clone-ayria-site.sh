#!/bin/bash
# AYRIA - Clona o site público do Lovable → ~/projects/ayria/site/
# Uso: bash scripts/clone-ayria-site.sh
#
# 📝 26/07/2026 — Rafael pediu pra clonar o site público da AYRIA
# pra ficar acessível offline / hospedável em qualquer host estático.
#
# O site é SSR (Lovable), então o HTML já vem completo.
# Precisa só baixar HTML + 6 assets e reescrever paths.

set -e

PROJ=/home/peron/projects/ayria
SITE_DIR=$PROJ/site
SRC="https://ayria-life-navigator.lovable.app"

mkdir -p "$SITE_DIR/assets"
cd "$SITE_DIR"

echo "=== 1. Baixa HTML ==="
curl -sSL -A "Mozilla/5.0" "$SRC/" -o index.html
echo "  ✅ index.html: $(wc -c < index.html) bytes"

echo ""
echo "=== 2. Baixa assets referenciados ==="
ASSETS=(
  "~flock.js"
  "assets/hero-orb-DNCFbJnK.jpg"
  "assets/index-Bs9ey3CK.js"
  "assets/index-DlyoQ5Ai.js"
  "assets/styles-BUOl1R5f.css"
)
# A logo está em path versionado — pega dinamicamente
LOGO_PATH=$(grep -aoE '/__l5e/assets-v1/[^"]+/ayria-logo\.png' index.html | head -1 | tr -d '"')
[ -n "$LOGO_PATH" ] && ASSETS+=("$LOGO_PATH")

for u in "${ASSETS[@]}"; do
  fname=$(echo "$u" | sed 's|^/||;s|^.*/assets/|assets/|')
  if [ "$u" = "~flock.js" ] || [ "$(basename "$u")" = "~flock.js" ]; then
    fname="~flock.js"
  fi
  if [[ "$u" == */ayria-logo.png ]]; then
    fname="assets/ayria-logo.png"
  fi
  printf "  ⬇  /%s → %s\n" "$u" "$fname"
  curl -sSL "$SRC/$u" -o "$fname"
done

echo ""
echo "=== 3. Reescreve paths absolutos → relativos ==="
sed -i \
  -e 's|"/~flock.js"|"./~flock.js"|g' \
  -e 's|"/assets/hero-orb-DNCFbJnK\.jpg"|"./assets/hero-orb-DNCFbJnK.jpg"|g' \
  -e 's|"/assets/index-Bs9ey3CK\.js"|"./assets/index-Bs9ey3CK.js"|g' \
  -e 's|"/assets/index-DlyoQ5Ai\.js"|"./assets/index-DlyoQ5Ai.js"|g' \
  -e 's|"/assets/styles-BUOl1R5f\.css"|"./assets/styles-BUOl1R5f.css"|g' \
  -e 's|"/__l5e/assets-v1/[^/]*/ayria-logo\.png"|"./assets/ayria-logo.png"|g' \
  -e 's|data-proxy-url="/~api/analytics"||g' \
  index.html

echo ""
echo "=== 4. Remove badge 'Edit with Lovable' ==="
python3 << 'PYEOF'
import re
with open('index.html') as f:
    h = f.read()
# Remove badges/HTTP-CSS do lovable
h = re.sub(r'<meta\s+[^>]*og:image[^>]*/>', '', h)
h = re.sub(r'<meta\s+[^>]*twitter:image[^>]*/>', '', h)
h = re.sub(r'<link[^>]*lovable[^>]*>', '', h)
h = re.sub(r'<a[^>]*href="https://lovable\.dev/projects/[^"]*"[^>]*>.*?</a>', '', h)
# Remove #lovable-badge {...} CSS blocks
while True:
    m = re.search(r'#lovable-badge[a-zA-Z0-9_-]*\s*\{', h)
    if not m: break
    j = h.find('{', m.end()-1)
    depth = 1
    k = j + 1
    while k < len(h) and depth > 0:
        if h[k] == '{': depth += 1
        elif h[k] == '}': depth -= 1
        k += 1
    s = m.start()
    while s > 0 and h[s-1] in ' \t\n;':
        s -= 1
    h = h[:s] + h[k:]
with open('index.html', 'w') as f:
    f.write(h)
print("  ✅ Lovable badge removido")
PYEOF

echo ""
echo "=== 5. Inventário final ==="
echo "Total: $(du -sh . | cut -f1)"
find . -type f -printf "  %p (%s bytes)\n" | sort

echo ""
echo "=== 6. Teste rápido ==="
PORT="${PORT:-8180}"
python3 -m http.server "$PORT" > /tmp/ayria-site.log 2>&1 &
SERVER_PID=$!
sleep 2
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$PORT/")
echo "  ✅ http://localhost:$PORT/ → HTTP $STATUS"
kill $SERVER_PID 2>/dev/null
echo ""
echo "Para servir de fato:"
echo "  cd $SITE_DIR && python3 -m http.server 8180"
echo "Depois acessa: http://localhost:8180/"