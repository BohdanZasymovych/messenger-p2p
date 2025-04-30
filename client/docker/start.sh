#!/usr/bin/env bash
set -e

# 1) Ensure certs folder exists
mkdir -p /app/certs

# 2) Generate a self‑signed cert if none exist
if [[ ! -f /app/certs/cert.pem || ! -f /app/certs/key.pem ]]; then
  echo "🔐 Generating self‑signed TLS cert for localhost…"
  openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout /app/certs/key.pem \
    -out    /app/certs/cert.pem \
    -subj   "/CN=localhost"
fi

# 3) Start your FastAPI app in background
echo "🚀 Starting FastAPI (HTTPS) via messenger.py…"
python /app/backend/messenger.py &
API_PID=$!

# 4) Wait for it to come up
echo "⏳ Waiting for server to start…"
sleep 5

# 5) Show access info
cat <<EOF

===============================================
  Secure Chat is running at:
    https://localhost:8000
  (use HTTPS / WSS for all API and WebSocket calls)
===============================================
EOF

# 6) Optional: open browser if DISPLAY is set
if [ -n "$DISPLAY" ] && command -v xdg-open >/dev/null; then
  xdg-open https://localhost:8000 >/dev/null 2>&1 || true
fi

# 7) Keep container alive until messenger.py exits
wait $API_PID