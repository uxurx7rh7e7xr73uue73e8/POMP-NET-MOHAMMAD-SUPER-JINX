#!/usr/bin/env bash
set -Eeuo pipefail

REPO="https://github.com/uxurx7rh7e7xr73uue73e8/POMP-NET-MOHAMMAD-SUPER-JINX.git"
APP_DIR="${APP_DIR:-/opt/pompnet-super-jinx}"

fail() { echo "ERROR: $*" >&2; exit 1; }

[[ "${EUID}" -eq 0 ]] || fail "Run as root: sudo bash setup-vps.sh"
command -v docker >/dev/null 2>&1 || fail "Docker Engine is not installed."
docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is not installed."
command -v git >/dev/null 2>&1 || fail "git is not installed."
command -v openssl >/dev/null 2>&1 || fail "openssl is not installed."
command -v python3 >/dev/null 2>&1 || fail "python3 is not installed."
command -v ss >/dev/null 2>&1 || fail "ss (iproute2) is not installed."
command -v curl >/dev/null 2>&1 || fail "curl is not installed."
docker info >/dev/null 2>&1 || fail "Docker daemon is not running."

if [[ -d "$APP_DIR/.git" ]]; then
  git -C "$APP_DIR" pull --ff-only || fail "Could not update the project directory."
elif [[ -e "$APP_DIR" ]]; then
  fail "$APP_DIR exists but is not this Git repository. Move it safely or choose another APP_DIR."
else
  mkdir -p "$(dirname "$APP_DIR")"
  git clone --depth 1 "$REPO" "$APP_DIR" || fail "Git clone failed."
fi

cd "$APP_DIR"
[[ ! -e .env ]] || fail ".env already exists. Existing configuration was left untouched."
if docker volume inspect pompnet_data >/dev/null 2>&1; then
  fail "Existing data volume pompnet_data found. Refusing to create new credentials or touch existing panel data."
fi

for port in 80 443; do
  if ss -ltnH "sport = :$port" | grep -q .; then
    fail "TCP port $port is already in use. Do not stop existing services blindly; free/configure it first."
  fi
done
if ss -lunH "sport = :443" | grep -q .; then
  echo "WARNING: UDP/443 is already in use; HTTP/3 will not be available." >&2
fi

read -r -p "Domain pointing to this VPS (example: panel.example.com): " DOMAIN
python3 - "$DOMAIN" <<'PY' || fail "Invalid domain name."
import re, sys
d = sys.argv[1].strip()
if not re.fullmatch(r"(?=.{4,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", d):
    raise SystemExit(1)
PY

# The owner account name is fixed by ensure_admin.py and must match the login UI.
ADMIN="ADMIN_tanel9990"
PASSWORD="$(openssl rand -base64 36 | tr -d '\n')"

umask 077
cat > .env <<EOF
PANEL_DOMAIN=$DOMAIN
ADMIN_USERNAME=$ADMIN
ADMIN_PASSWORD=$PASSWORD
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=43200
EOF
chmod 600 .env

docker compose config --quiet || fail "Compose configuration is invalid; .env is preserved at $APP_DIR/.env."
docker compose up -d --build

echo
echo "Waiting for POMP NET panel health..."
for _ in $(seq 1 90); do
  if curl --fail --silent --show-error "https://$DOMAIN/health" >/dev/null 2>&1; then
    echo
    echo "POMP NET SUPER JINX is responding over HTTPS."
    echo "Panel: https://$DOMAIN/dashboard/"
    echo "Admin username: ADMIN_tanel9990"
    echo "Persistent admin password: $PASSWORD"
    echo "SAVE THIS PASSWORD NOW. It is also stored in the protected .env file and remains the same across restarts/redeploys that keep this project directory and Docker volume."
    echo "Project directory: $APP_DIR"
    exit 0
  fi
  sleep 2
done

echo "The containers were started, but HTTPS health did not pass yet." >&2
echo "Check DNS A/AAAA records, inbound TCP 80/443, then run:" >&2
echo "cd $APP_DIR && docker compose logs --tail=200" >&2
exit 1
