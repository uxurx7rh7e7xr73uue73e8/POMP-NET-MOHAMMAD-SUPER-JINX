#!/bin/sh
set -eu

# Railway injects PORT at runtime. PasarGuard's official start.sh runs DB
# migrations and starts the all-in-one panel process.
export UVICORN_HOST=0.0.0.0
export UVICORN_PORT="${PORT:-8000}"
export SQLALCHEMY_DATABASE_URL="${SQLALCHEMY_DATABASE_URL:-sqlite+aiosqlite:////var/lib/pasarguard/db.sqlite3}"
export DEBUG=false

mkdir -p /var/lib/pasarguard
if [ ! -w /var/lib/pasarguard ]; then
  echo "[POMP NET] FATAL: /var/lib/pasarguard is not writable. Attach a Railway Volume there."
  exit 1
fi

echo "[POMP NET] Starting official PasarGuard panel on 0.0.0.0:${UVICORN_PORT}"
echo "[POMP NET] Railway TLS is terminated at the Railway edge; internal panel HTTP is intentional."
exec /code/start.sh
