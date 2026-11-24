#!/bin/bash
set -e

# Owner identity is stable; credentials come from a Railway Secret or a one-time
# random password stored on the persistent Volume. Never reset an existing owner on boot.
export ADMIN_USERNAME="${ADMIN_USERNAME:-ADMIN_tanel9990}"
export ALLOW_INSECURE_ADMIN_PASSWORD="${ALLOW_INSECURE_ADMIN_PASSWORD:-0}"
export RESET_ADMIN_PASSWORD="${RESET_ADMIN_PASSWORD:-0}"

echo "=== ⚡ POMP NET MOHAMMAD | SUPER JINX ==="
# ⚡ more open connections for nginx + Xray (many users / many tabs at once), never fatal
ulimit -n 65535 2>/dev/null || ulimit -n "$(ulimit -Hn)" 2>/dev/null || true

# Owner credentials are stored as a bcrypt hash in the persistent Marzban database.
# The owner username is fixed as ADMIN_tanel9990; ensure_admin.py generates a one-time password if no Secret is supplied.
unset SUDO_USERNAME SUDO_PASSWORD
# internal wiring is forced too, so a wrong Railway variable can never break the panel
export UVICORN_HOST=127.0.0.1
export UVICORN_PORT=8000
export XRAY_JSON=/var/lib/marzban/xray_config.json
export SQLALCHEMY_DATABASE_URL=sqlite:////var/lib/marzban/db.sqlite3
export JWT_ACCESS_TOKEN_EXPIRE_MINUTES="${JWT_ACCESS_TOKEN_EXPIRE_MINUTES:-43200}"
# ⚡ our own subscription page (sub.html)
export CUSTOM_TEMPLATES_DIRECTORY=/opt/jinx/templates/
export SUBSCRIPTION_PAGE_TEMPLATE=subscription/index.html
# what apps see when they fetch the subscription: title, support link, auto-update every 6h
export SUB_PROFILE_TITLE="POMP NET MOHAMMAD — SUPER JINX"
export SUB_SUPPORT_URL="https://t.me/PompNett"
export SUB_UPDATE_INTERVAL="${SUB_UPDATE_INTERVAL:-6}"
# 🔗 every app gets plain share links (the same way the SuperJinX panels that ping well do it):
#    the app builds its own config, so no panel JSON template can ever break the connection.
#    Set USE_CUSTOM_JSON_FOR_V2RAYNG=True (etc.) in Railway Variables to switch back to full JSON.
export USE_CUSTOM_JSON_FOR_V2RAYNG="${USE_CUSTOM_JSON_FOR_V2RAYNG:-False}"
export USE_CUSTOM_JSON_FOR_V2RAYN="${USE_CUSTOM_JSON_FOR_V2RAYN:-False}"
export USE_CUSTOM_JSON_FOR_STREISAND="${USE_CUSTOM_JSON_FOR_STREISAND:-False}"
export USE_CUSTOM_JSON_FOR_HAPP="${USE_CUSTOM_JSON_FOR_HAPP:-False}"

mkdir -p /var/lib/marzban /run/jinx
# Never ship a fixed/default owner password. Prefer the Railway ADMIN_PASSWORD Secret.
# Generate and print a one-time password ONLY for a genuinely fresh database.
# If an existing database has already had its owner initialized, never invent or
# print a replacement password: ensure_admin.py will preserve the current hash.
if [ -z "${ADMIN_PASSWORD:-}" ]; then
  ADMIN_PASSWORD_FILE=/var/lib/marzban/.pompnet-admin-password
  ADMIN_MARKER=/var/lib/marzban/.pompnet-default-admin-applied
  if [ -s "$ADMIN_PASSWORD_FILE" ]; then
    ADMIN_PASSWORD="$(cat "$ADMIN_PASSWORD_FILE")"
    export ADMIN_PASSWORD
  elif [ ! -e "$ADMIN_MARKER" ] && [ "${RESET_ADMIN_PASSWORD}" != "1" ]; then
    ADMIN_PASSWORD="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
    ( umask 077; printf '%s' "$ADMIN_PASSWORD" > "$ADMIN_PASSWORD_FILE" )
    chmod 600 "$ADMIN_PASSWORD_FILE"
    export ADMIN_PASSWORD
    echo "[admin] ONE-TIME LOGIN for owner ${ADMIN_USERNAME}: $ADMIN_PASSWORD"
  else
    echo "[admin] existing owner detected; preserving its password (no new password was generated)"
  fi
fi
# 🔐 secret config path /cdn/<random id> (SuperJinX style): made once, kept in the Volume = configs never change.
#    JINX_PATH_SECRET in Railway Variables sets your own id (8-64 letters / digits / -).
JX_FILE=/var/lib/marzban/jinx_path
JX_ID="$(printf '%s' "${JINX_PATH_SECRET:-}" | tr -cd 'A-Za-z0-9-')"
if [ ${#JX_ID} -lt 8 ] || [ ${#JX_ID} -gt 64 ]; then
  [ -n "${JINX_PATH_SECRET:-}" ] && echo "[start] WARNING: JINX_PATH_SECRET must be 8-64 letters/digits/- -> ignored"
  JX_ID="$( (tr -cd 'A-Za-z0-9-' < "$JX_FILE") 2>/dev/null || true)"
fi
if [ ${#JX_ID} -lt 8 ] || [ ${#JX_ID} -gt 64 ]; then
  JX_ID="$(cat /proc/sys/kernel/random/uuid 2>/dev/null || python -c 'import uuid; print(uuid.uuid4())')"
fi
printf '%s' "$JX_ID" > "$JX_FILE.tmp" 2>/dev/null && mv -f "$JX_FILE.tmp" "$JX_FILE" || echo "[start] WARNING: could not save the config path"
export JINX_WS_BASE="/cdn/$JX_ID"
echo "[start] secret config path ready"
if ! python /opt/lock.py; then
  # Safe fallback: preserve the last valid config, but ALWAYS synchronize its WS paths
  # with the current Nginx secret path. A stale path here makes every generated link fail.
  echo "[lock] WARNING: config builder failed -> synchronizing last-good Xray config paths"
  python - <<'PY'
import json, os, tempfile
dst = "/var/lib/marzban/xray_config.json"
base = "/opt/xray_config.json"
locked_file = "/opt/locked_inbound.json"
B = os.environ.get("JINX_WS_BASE", "/cdn/jinx")
try:
    with open(dst, encoding="utf-8") as f:
        cfg = json.load(f)
    if not isinstance(cfg.get("inbounds"), list):
        raise ValueError("last-good config has no inbound list")
except Exception:
    with open(base, encoding="utf-8") as f:
        cfg = json.load(f)
with open(locked_file, encoding="utf-8") as f:
    locked = json.load(f)
locked_tag = locked["tag"]
locked["streamSettings"]["wsSettings"]["path"] = B
found = False
for ib in cfg["inbounds"]:
    tag = ib.get("tag")
    ws = (ib.get("streamSettings") or {}).get("wsSettings")
    if tag == locked_tag:
        ib["streamSettings"]["wsSettings"]["path"] = B
        found = True
    elif isinstance(ws, dict) and tag in ("VLESS WS", "VMESS WS", "TROJAN WS"):
        ws["path"] = B + {"VLESS WS": "/v", "VMESS WS": "/m", "TROJAN WS": "/t"}[tag]
if not found:
    cfg["inbounds"].insert(0, locked)
tmp = dst + ".fallback.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cfg, f, ensure_ascii=False, indent=2)
os.replace(tmp, dst)
print("[lock] fallback config paths synchronized with Nginx", flush=True)
PY
fi

# Never use documentation placeholders such as panel.example.com in generated subscriptions.
# Resolve the public hostname automatically. Explicit PANEL_DOMAIN wins; then
# platform-provided hostnames are checked. Never invent a hostname or use an example domain.
PUBLIC_DOMAIN_CANDIDATE="${PANEL_DOMAIN:-${PUBLIC_DOMAIN:-${APP_DOMAIN:-}}}"
if [ -z "$PUBLIC_DOMAIN_CANDIDATE" ]; then
  PUBLIC_DOMAIN_CANDIDATE="${RAILWAY_PUBLIC_DOMAIN:-${RAILWAY_STATIC_URL:-${RENDER_EXTERNAL_HOSTNAME:-${KOYEB_PUBLIC_DOMAIN:-}}}}"
fi
if [ -z "$PUBLIC_DOMAIN_CANDIDATE" ] && [ -n "${FLY_APP_NAME:-}" ]; then
  PUBLIC_DOMAIN_CANDIDATE="${FLY_APP_NAME}.fly.dev"
fi
if [ -z "$PUBLIC_DOMAIN_CANDIDATE" ] && [ -n "${HEROKU_APP_NAME:-}" ]; then
  PUBLIC_DOMAIN_CANDIDATE="${HEROKU_APP_NAME}.herokuapp.com"
fi
# Accept either a hostname or an https URL from platform variables; reduce it to a hostname.
PUBLIC_DOMAIN="$(python - "$PUBLIC_DOMAIN_CANDIDATE" <<'PY'
import sys, re
from urllib.parse import urlsplit
v = (sys.argv[1] or "").strip()
if not v or v.lower() in ("example.com",) or v.lower().endswith(".example.com"):
    print(""); raise SystemExit
u = urlsplit(v if "://" in v else "//" + v)
h = (u.hostname or "").lower().rstrip(".")
if not h or not re.fullmatch(r"[a-z0-9.-]+", h) or "." not in h or h == "example.com" or h.endswith(".example.com"):
    h = ""
print(h)
PY
)"
if [ -z "$PUBLIC_DOMAIN" ] && [ -n "${CF_TUNNEL_TOKEN:-}" ]; then
  PUBLIC_DOMAIN="$CF_TUNNEL_HOSTNAME"
fi
if [ -n "$PUBLIC_DOMAIN" ]; then
  # Railway terminates public TLS on its generated HTTPS domain and forwards HTTP to PORT=8080.
  # Subscription URLs must use the public hostname without an internal or TCP-proxy port.
  export XRAY_SUBSCRIPTION_URL_PREFIX="https://$PUBLIC_DOMAIN"
fi
echo "[start] domain: ${PUBLIC_DOMAIN:-NOT SET} | subscription endpoint: ${XRAY_SUBSCRIPTION_URL_PREFIX:-NOT SET} (Railway HTTPS)"
[ -d /var/lib/marzban ] && touch /var/lib/marzban/.write-test && rm -f /var/lib/marzban/.write-test \
  || echo "[start] WARNING: /var/lib/marzban not writable"
mountpoint -q /var/lib/marzban 2>/dev/null || echo "[start] WARNING: no Volume on /var/lib/marzban, data will reset on redeploy"
# all 4 Railway regions work; EU West (Amsterdam) gives the lowest ping from Iran
case "${RAILWAY_REPLICA_REGION:-}" in
  *europe*|"") echo "[start] region: ${RAILWAY_REPLICA_REGION:-unknown} (Amsterdam = best for Iran)";;
  *) echo "[start] NOTE: region is ${RAILWAY_REPLICA_REGION} -> works, but for the lowest ping from Iran pick EU West (Amsterdam) in Settings > Regions";;
esac

# panel always on 8080; if Railway injected another PORT, listen there too (healthcheck never misses)
# nginx config rendered from the template with the secret path (every start, so it always matches Xray)
sed "s#__JXB__#${JINX_WS_BASE}#g" /opt/jinx/nginx.conf.tpl > /etc/nginx/conf.d/marzban.conf
if [ "${JINX_OLD_PATHS:-1}" = "0" ]; then
  : > /etc/nginx/jinx-old.inc
  echo "[start] old config paths closed (JINX_OLD_PATHS=0)"
else
  cat > /etc/nginx/jinx-old.inc <<NGX
location = /panel-ws { rewrite ^ ${JINX_WS_BASE} break;   proxy_pass http://127.0.0.1:2004; include /etc/nginx/ws.inc; }
location = /vless    { rewrite ^ ${JINX_WS_BASE}/v break; proxy_pass http://127.0.0.1:2001; include /etc/nginx/ws.inc; }
location = /vmess    { rewrite ^ ${JINX_WS_BASE}/m break; proxy_pass http://127.0.0.1:2002; include /etc/nginx/ws.inc; }
location = /trojan   { rewrite ^ ${JINX_WS_BASE}/t break; proxy_pass http://127.0.0.1:2003; include /etc/nginx/ws.inc; }
location = /vhu      { rewrite ^ ${JINX_WS_BASE}/u break; proxy_pass http://127.0.0.1:2005; include /etc/nginx/ws.inc; }
NGX
fi
if [ -n "$PORT" ] && [ "$PORT" != "8080" ]; then
  echo "listen ${PORT} reuseport;" > /etc/nginx/jinx-port.inc
  echo "[start] Railway PORT=$PORT -> nginx listens on 8080 and $PORT"
else
  : > /etc/nginx/jinx-port.inc
fi
# Fail closed: never report a healthy panel while silently dropping every VPN route.
# If the routing config is invalid, stop the deployment so the actual error is visible in Railway logs.
if ! nginx -t; then
  echo "[start] FATAL: nginx config is invalid; refusing to start a panel with non-working VPN links."
  exit 1
fi
nginx

# Cloudflare Tunnel (optional): CF_TUNNEL_TOKEN + CF_TUNNEL_HOSTNAME
if [ -n "$CF_TUNNEL_TOKEN" ] && ! command -v cloudflared >/dev/null 2>&1; then
  echo "[tunnel] WARNING: cloudflared is not in this image (download failed at build) -> direct Railway mode"
elif [ -n "$CF_TUNNEL_TOKEN" ]; then
  echo "[tunnel] starting Cloudflare tunnel -> ${CF_TUNNEL_HOSTNAME:-?}"
  ( while true; do
      cloudflared tunnel --no-autoupdate --protocol auto --edge-ip-version 4 --retries 10 \
        run --token "$CF_TUNNEL_TOKEN" 2>&1 | sed -u 's/^/[tunnel] /' || true
      echo "[tunnel] disconnected, reconnecting in 5s"; sleep 5
    done ) &
else
  echo "[tunnel] CF_TUNNEL_TOKEN not set, direct Railway mode"
fi

cd /code
FRESH=0; [ -s /var/lib/marzban/db.sqlite3 ] || FRESH=1
alembic upgrade head
if ! python /opt/ensure_admin.py; then
  echo "[admin] FATAL: admin initialization failed. Check the preceding [admin] error in deploy logs."
  exit 1
fi

# 📶 sing-box / Clash apps (SFA, SFI, Karing, Clash): auto "best latency" tested over plain http = one round trip
#    less per test, so the ping number they show is lower AND still real. Built from this image's own templates.
python - <<'PY' || echo "[start] latency-test templates skipped (apps keep their default test)"
import json, os
T = "http://cp.cloudflare.com/"
src, dst = "/code/app/templates/singbox/default.json", "/opt/jinx/templates/singbox/default.json"
if os.path.exists(src) and (os.environ.get("SINGBOX_SUBSCRIPTION_TEMPLATE") or "singbox/default.json") == "singbox/default.json":
    c = json.load(open(src, encoding="utf-8"))
    n = 0
    for o in c.get("outbounds") or []:
        if isinstance(o, dict) and o.get("type") == "urltest":
            o["url"] = T; o.setdefault("interval", "3m"); o.setdefault("tolerance", 50); n += 1
    if n:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        json.dump(c, open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[start] sing-box apps: best-latency test -> {T}", flush=True)
for name in ("clash/default.yml", "clash/settings.yml"):
    s_, d_ = "/code/app/templates/" + name, "/opt/jinx/templates/" + name
    if os.path.exists(s_):
        t = open(s_, encoding="utf-8").read()
        t2 = t.replace("https://www.gstatic.com/generate_204", T).replace("http://www.gstatic.com/generate_204", T)
        if t2 != t:
            os.makedirs(os.path.dirname(d_), exist_ok=True); open(d_, "w", encoding="utf-8").write(t2)
            print(f"[start] clash apps: latency test -> {T}", flush=True)
PY

python main.py &
MAIN=$!
echo "$MAIN" > /run/jinx/marzban.pid
trap 'kill -TERM $MAIN 2>/dev/null; wait $MAIN; exit 0' TERM INT

# helpers restart themselves if they ever stop; the panel keeps running no matter what
#   (set +e inside: a crash must restart the helper, not end its loop)
( set +e; while true; do python /opt/jinx_api.py; echo "[account] restarting in 2s"; sleep 2; done ) &
( set +e; while true; do python /opt/enforce_hosts.py; echo "[guard] restarting in 5s"; sleep 5; done ) &
( set +e; while true; do python /opt/doctor.py; echo "[doctor] restarting in 5s"; sleep 5; done ) &
( set +e; while true; do python /opt/pompnet_telegram_bot.py; echo "[bot] worker restarting in 5s"; sleep 5; done ) &

set +e
wait "$MAIN"
CODE=$?
echo "[start] panel exited with code $CODE -> container restart"
exit 1
