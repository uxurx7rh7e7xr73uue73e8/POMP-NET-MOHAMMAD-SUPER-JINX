#!/bin/sh
set -eu

DATA_DIR=/var/lib/pasarguard
CERT_DIR="$DATA_DIR/certs"
CERT="$CERT_DIR/railway-cert.pem"
KEY="$CERT_DIR/railway-key.pem"
APP_PORT=8000
PUBLIC_PORT="${PORT:-8000}"

mkdir -p "$CERT_DIR"
chmod 700 "$CERT_DIR"

if [ ! -s "$CERT" ] || [ ! -s "$KEY" ]; then
  echo "[POMP NET] Creating internal self-signed certificate for Railway-to-app traffic."
  openssl req -x509 -newkey rsa:2048 -nodes -days 825 \
    -keyout "$KEY" -out "$CERT" \
    -subj "/CN=pasarguard-internal" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" >/dev/null 2>&1
  chmod 600 "$KEY"
  chmod 644 "$CERT"
fi

if ! awk -v p="$DATA_DIR" '$2 == p { found=1 } END { exit !found }' /proc/mounts; then
  echo "[POMP NET] FATAL: no mounted Railway Volume found at $DATA_DIR."
  echo "[POMP NET] Attach a persistent Volume at exactly $DATA_DIR, then redeploy."
  exit 1
fi
if [ ! -w "$DATA_DIR" ]; then
  echo "[POMP NET] FATAL: $DATA_DIR is mounted but not writable."
  exit 1
fi

cat >/etc/nginx/conf.d/default.conf <<NGINX
server {
    listen 0.0.0.0:$PUBLIC_PORT;
    server_name _;
    client_max_body_size 32m;

    location / {
        proxy_pass https://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_ssl_verify off;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
NGINX

nginx -t

export UVICORN_HOST=0.0.0.0
export UVICORN_PORT="$APP_PORT"
export UVICORN_SSL_CERTFILE="$CERT"
export UVICORN_SSL_KEYFILE="$KEY"
export UVICORN_SSL_CA_TYPE=private
export UVICORN_PROXY_HEADERS=true
export UVICORN_FORWARDED_ALLOW_IPS=127.0.0.1
export SQLALCHEMY_DATABASE_URL="${SQLALCHEMY_DATABASE_URL:-sqlite+aiosqlite:////var/lib/pasarguard/db.sqlite3}"
export DEBUG=false
export DOCS=false

echo "[POMP NET] Running official PasarGuard migrations and application."
/code/start.sh >/tmp/pasarguard-app.log 2>&1 &
APP_PID=$!

ready=0
i=0
while [ "$i" -lt 90 ]; do
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "[POMP NET] PasarGuard exited during startup:"
    cat /tmp/pasarguard-app.log
    exit 1
  fi
  code="$(curl -k -sS -o /dev/null -w '%{http_code}' "https://127.0.0.1:$APP_PORT/" || true)"
  case "$code" in
    2*|3*|4*) ready=1; break ;;
  esac
  i=$((i + 1))
  sleep 2
done

if [ "$ready" -ne 1 ]; then
  echo "[POMP NET] PasarGuard did not become ready; last application logs:"
  cat /tmp/pasarguard-app.log
  kill "$APP_PID" 2>/dev/null || true
  exit 1
fi

echo "[POMP NET] PasarGuard is ready. Starting Railway HTTP ingress on port $PUBLIC_PORT."
nginx -g 'daemon off;' &
NGINX_PID=$!
while kill -0 "$APP_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 5
done
echo "[POMP NET] Application or ingress process stopped; shutting down container."
kill "$APP_PID" "$NGINX_PID" 2>/dev/null || true
cat /tmp/pasarguard-app.log
exit 1
