#!/usr/bin/env bash
# Runtime integration test for the built POMP NET SUPER JINX image.
# Runs locally inside the ephemeral GitHub Actions runner; it does not deploy publicly.
set -Eeuo pipefail

IMAGE="${1:-pompnet-super-jinx:ci}"
NAME="pompnet-jinx-smoke"
RESET_NAME="pompnet-jinx-reset-admin"
VOLUME="pompnet-jinx-smoke-data"
BASE="http://127.0.0.1:18080"
ADMIN="ADMIN_tanel9990"
PASSWORD="ci-only-$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
USER="jinx_ci_smoke"

AUTO_NAME="pompnet-jinx-auto-admin"
AUTO_VOLUME="pompnet-jinx-auto-admin-data"
AUTO_BASE="http://127.0.0.1:18081"

cleanup() {
  docker rm -f "$NAME" "$AUTO_NAME" "$RESET_NAME" >/dev/null 2>&1 || true
  docker volume rm "$VOLUME" "$AUTO_VOLUME" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker volume create "$VOLUME" >/dev/null

start_panel() {
  docker run -d --name "$NAME" \
    -p 127.0.0.1:18080:8080 \
    -v "$VOLUME:/var/lib/marzban" \
    -e ADMIN_USERNAME="$ADMIN" \
    -e ADMIN_PASSWORD="$PASSWORD" \
    -e XRAY_SUBSCRIPTION_URL_PREFIX="$BASE" \
    -e PANEL_DOMAIN="ci.example.net" \
    -e SUB_PROFILE_TITLE="POMP NET MOHAMMAD" \
    "$IMAGE" >/dev/null
}

wait_panel() {
  for _ in $(seq 1 120); do
    STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' "$BASE/health" 2>/dev/null || true)"
    if [[ "$STATUS" == "200" ]]; then return 0; fi
    if ! docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true; then
      docker logs "$NAME" || true
      return 1
    fi
    sleep 2
  done
  docker logs "$NAME" || true
  echo "Panel did not become healthy within 240 seconds" >&2
  return 1
}

login() {
  curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 2 \
    -X POST "$BASE/api/admin/token" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "username=$ADMIN" \
    --data-urlencode "password=$PASSWORD" \
    | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
}

# Railway terminates public TLS at its HTTPS edge (443); the container listens on HTTP 8080.
# Port 2096 is not assumed to exist on Railway. VPS/Compose and Caddy deployments keep
# their own separately configured 2096 listeners and are not used to build Railway links.
grep -q 'XRAY_SUBSCRIPTION_URL_PREFIX="https://\$PUBLIC_DOMAIN"' start.sh
if grep -q 'XRAY_SUBSCRIPTION_URL_PREFIX="https://\$PUBLIC_DOMAIN:2096"' start.sh; then
  echo "Railway subscription URL must use the TLS edge hostname without an unexposed :2096 port" >&2
  exit 1
fi
grep -q 'listen 8080' nginx.conf
echo "[smoke] Railway HTTPS edge -> internal port 8080 subscription routing: OK"
grep -q -- 'POMP NET legibility and mobile performance overrides' jinx.css
grep -q -- 'POMP NET readable subscription view' sub.html
grep -q -- 'prefers-reduced-motion:reduce' jinx.css
echo "[smoke] readable high-contrast low-motion styles: OK"

start_panel
wait_panel

# The five SideRail-compatible HTTP inbounds must exist in the generated Xray runtime config.
docker exec "$NAME" python -c 'import json; c=json.load(open("/var/lib/marzban/xray_config.json")); a={x["tag"]:x for x in c["inbounds"]}; required={"VLESS WS","VMESS WS","TROJAN WS","VLESS HTTPUPGRADE","VLESS XHTTP"}; missing=required-set(a); assert not missing, "missing SideRail-compatible inbounds: "+", ".join(sorted(missing)); assert a["VLESS XHTTP"]["streamSettings"]["xhttpSettings"]["mode"]=="auto"; assert all(not x.get("sniffing",{}).get("enabled",False) for x in a.values()), "Xray sniffing must be disabled"; assert "VLESS XHTTP SU" not in a; print("[smoke] five SideRail-compatible inbounds + XHTTP auto + sniffing disabled: OK")'

# The support page contains only the configured bank card and its copy action.
DONATE_PAGE="$(curl --fail --silent --show-error "$BASE/donate/")"
grep -q -- "حمایت پروژه" <<< "$DONATE_PAGE"
grep -q -- "کپی شماره کارت" <<< "$DONATE_PAGE"
DONATE_CONFIG="$(curl --fail --silent --show-error "$BASE/donate/config.js")"
grep -q -- 'bankCard: "6280231311605819"' <<< "$DONATE_CONFIG"
if grep -q -- "هر بخش از POMP NET" <<< "$DONATE_PAGE"; then echo "Unexpected extra support text" >&2; exit 1; fi
echo "[smoke] project support page shows bank card only: OK"

# Verify the real PasarGuard dashboard is served and receives the POMP NET skin.
DASHBOARD_HTML="$(curl --fail --silent --show-error "$BASE/dashboard/")"
grep -q -- 'href="/jinx.css"' <<< "$DASHBOARD_HTML"
grep -q -- 'src="/jinx.js"' <<< "$DASHBOARD_HTML"
JINX_SCRIPT="$(curl --fail --silent --show-error "$BASE/jinx.js")"
grep -q -- "POMP NET MOHAMMAD" <<< "$JINX_SCRIPT"
grep -q -- "pompnet-panel-credit" <<< "$JINX_SCRIPT"
grep -q -- "با همراهی SUPER JINX" <<< "$JINX_SCRIPT"
JINX_STYLE="$(curl --fail --silent --show-error "$BASE/jinx.css")"
grep -q -- "Vazirmatn" <<< "$JINX_STYLE"
echo "[smoke] native PasarGuard dashboard + POMP NET skin: OK"
# Telegram bot settings are served, but configuration stays owner-only.
BOT_PAGE="$(curl --fail --silent --show-error "$BASE/bot/")"
grep -q "ربات مدیریت POMP NET MOHAMMAD" <<< "$BOT_PAGE"
BOT_UNAUTH="$(curl --silent --output /dev/null --write-out '%{http_code}' "$BASE/jinx-api/bot-config")"
test "$BOT_UNAUTH" = "401"
OWNER_TOKEN="$(login)"
curl --fail --silent --show-error "$BASE/jinx-api/bot-config" -H "Authorization: Bearer $OWNER_TOKEN" \
  | python -c 'import json,sys; d=json.load(sys.stdin); assert d["ok"] and "token_set" in d; print("[smoke] owner-only Telegram bot settings endpoint: OK")'

# Verify the 24-scene animated layer is served from the built image (not only present in GitHub).
MOTION_CSS="$(curl --fail --silent --show-error "$BASE/pompnet-motion.css")"
MOTION_JS="$(curl --fail --silent --show-error "$BASE/pompnet-motion.js")"
grep -q -- "#pompnet-motion" <<< "$MOTION_CSS"
grep -q -- "requestAnimationFrame" <<< "$MOTION_JS"
SCENE_COUNT="$(printf '%s' "$MOTION_JS" | grep -o '\["#' | wc -l)"
test "$SCENE_COUNT" -ge 24 || { echo "Expected 24 animated scenes, found $SCENE_COUNT" >&2; exit 1; }
echo "[smoke] animated dashboard assets + 24 scenes: OK"

TOKEN="$(login)"
echo "[smoke] admin login: OK"
curl --fail --silent --show-error "$BASE/pompnet-engine/health" | python -c 'import json,sys; d=json.load(sys.stdin); assert d.get("ok") is True and d.get("engine")=="xray-independent" and d.get("pid"); print("[smoke] independent Xray process is running: OK")'
curl --fail --silent --show-error "$BASE/pompnet-engine/api/inbounds" -H "Authorization: Bearer $TOKEN" | python -c 'import json,sys; a=json.load(sys.stdin); assert {x["protocol"] for x in a}=={"vless","vmess","trojan"}; assert all(x["port"]==443 and x["transport"]=="ws" for x in a); print("[smoke] three independent Railway WebSocket inbounds: OK")'
ENGINE_CREATE="$(curl --fail --silent --show-error -X POST "$BASE/pompnet-engine/api/users" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  --data '{"username":"pompnet_engine_ci","protocols":["vless","vmess","trojan"],"expire":0,"data_limit_gb":0}')"
echo "$ENGINE_CREATE" | python -c 'import json,sys; d=json.load(sys.stdin); assert d["ok"] and len(d["links"])==3 and d["subscription_url"]; print("[smoke] independent Xray created three real protocol credentials: OK")'
ENGINE_SUB_PATH="$(printf '%s' "$ENGINE_CREATE" | python -c 'import json,sys,urllib.parse; print(urllib.parse.urlsplit(json.load(sys.stdin)["subscription_url"]).path)')"
curl --fail --silent --show-error "$BASE$ENGINE_SUB_PATH" | python -c 'import base64,sys; s=base64.b64decode(sys.stdin.buffer.read()).decode(); assert all(x in s for x in ("vless://","vmess://","trojan://")); print("[smoke] independent Xray subscription serves all three links: OK")'

USER_JSON="$(curl --fail --silent --show-error --retry 10 --retry-all-errors --retry-delay 2 \
  -X POST "$BASE/api/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"username":"jinx_ci_smoke","proxies":{"vless":{},"vmess":{},"trojan":{}},"inbounds":{"vless":["VLESS WS"],"vmess":["VMESS WS"],"trojan":["TROJAN WS"]},"expire":0,"data_limit":0,"data_limit_reset_strategy":"no_reset","status":"active"}')"
echo "$USER_JSON" | python -c 'import json,sys; u=json.load(sys.stdin); assert u["username"]=="jinx_ci_smoke"; assert u.get("subscription_url"); print("[smoke] create VLESS + VMess + Trojan user + subscription URL: OK")'

SUB_URL="$(printf '%s' "$USER_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["subscription_url"])')"
SUB_PATH="$(python -c 'import sys,urllib.parse; u=urllib.parse.urlsplit(sys.argv[1]); print(u.path if u.path else sys.argv[1])' "$SUB_URL")"
if [[ "$SUB_PATH" == http* ]]; then
  SUB_BODY="$(curl --location --fail --silent --show-error "$SUB_PATH")"
else
  SUB_BODY="$(curl --location --fail --silent --show-error "$BASE$SUB_PATH")"
fi
test -n "${SUB_BODY:-}" || { echo "Subscription endpoint returned an empty body" >&2; exit 1; }
# Decode the real Marzban subscription and verify every selected protocol is actually emitted.
printf '%s' "$SUB_BODY" | python -c 'import base64,sys; raw=sys.stdin.buffer.read().strip(); txt=raw.decode(errors="ignore"); txt=base64.b64decode(raw+b"="*((4-len(raw)%4)%4)).decode(errors="ignore") if not any(txt.lower().startswith(p) for p in ("vless://","vmess://","trojan://")) else txt; lines=[x.strip() for x in txt.splitlines() if x.strip()]; missing=[p for p in ("vless://","vmess://","trojan://") if not any(x.lower().startswith(p) for x in lines)]; assert not missing, "subscription missing protocol links: "+", ".join(missing); print("[smoke] real subscription contains VLESS + VMess + Trojan links: OK")'
# Browser subscription page must render the custom Persian POMP NET template, not only raw config text.
SUB_PAGE="$(curl --location --fail --silent --show-error -A 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124.0 Mobile Safari/537.36' -H 'Accept: text/html,application/xhtml+xml' "$BASE$SUB_PATH")"
grep -q -- "POMP NET MOHAMMAD" <<< "$SUB_PAGE"
grep -q -- "کدنویسی و توسعه توسط تیم POMP NET MOHAMMAD" <<< "$SUB_PAGE"
grep -q -- "با همراهی SUPER JINX" <<< "$SUB_PAGE"
grep -q -- "#8B35FF" <<< "$SUB_PAGE"
if grep -qi -- "SideRail" <<< "$SUB_PAGE"; then
  echo "Unexpected third-party subscription branding" >&2
  exit 1
fi
echo "[smoke] custom subscription page + POMP NET theme: OK"
echo "[smoke] subscription endpoint returned a non-empty body: OK"

# Verify the real reseller sub-panel: isolated admin account, enforced limits, and its own subscription.
RESELLER="jinx_ci_reseller"
RESELLER_PASS="Reseller-Super-123!"
curl --fail --silent --show-error -X POST "$BASE/jinx-api/resellers" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  --data "{\"username\":\"$RESELLER\",\"password\":\"$RESELLER_PASS\",\"max_users\":10,\"quota_gb\":2,\"expire\":$(($(date +%s)+2592000)),\"title\":\"POMP NET CI reseller\",\"domain\":\"\"}" \
  | python -c 'import json,sys; assert json.load(sys.stdin)["ok"] is True'
RESELLER_TOKEN="$(curl --fail --silent --show-error -X POST "$BASE/api/admin/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$RESELLER" --data-urlencode "password=$RESELLER_PASS" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
curl --fail --silent --show-error "$BASE/api/admin" -H "Authorization: Bearer $RESELLER_TOKEN" \
  | python -c 'import json,sys; a=json.load(sys.stdin); assert a["username"]=="jinx_ci_reseller" and not a["is_sudo"]'
echo "[smoke] reseller account creation + independent login: OK"

# A reseller must not be able to read the owner's user.
OWNER_USER_STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' \
  "$BASE/api/user/$USER" -H "Authorization: Bearer $RESELLER_TOKEN")"
[[ "$OWNER_USER_STATUS" == "403" || "$OWNER_USER_STATUS" == "404" ]] || { echo "Reseller accessed another admin's user (HTTP $OWNER_USER_STATUS)" >&2; exit 1; }

RESELLER_USER_JSON="$(curl --fail --silent --show-error -X POST "$BASE/api/user" \
  -H "Authorization: Bearer $RESELLER_TOKEN" -H 'Content-Type: application/json' \
  --data '{"username":"jinx_ci_reseller_user","proxies":{"vless":{}},"inbounds":{"vless":["VLESS WS"]},"expire":0,"data_limit":536870912,"data_limit_reset_strategy":"no_reset","status":"active"}')"
echo "$RESELLER_USER_JSON" | python -c 'import json,sys; u=json.load(sys.stdin); assert u["username"]=="jinx_ci_reseller_user" and u.get("subscription_url"); print("[smoke] reseller creates own Xray user + real subscription URL: OK")'
RESELLER_SUB="$(printf '%s' "$RESELLER_USER_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["subscription_url"])')"
RESELLER_PATH="$(python -c 'import sys,urllib.parse; print(urllib.parse.urlsplit(sys.argv[1]).path)' "$RESELLER_SUB")"
RESELLER_BODY="$(curl --location --fail --silent --show-error "$BASE$RESELLER_PATH")"
test -n "$RESELLER_BODY" || { echo "Reseller subscription endpoint returned an empty body" >&2; exit 1; }
echo "[smoke] reseller subscription endpoint: OK"

# Confirm real WebSocket upgrades through Nginx to each selected Xray protocol inbound.
JX_ID="$(docker exec "$NAME" cat /var/lib/marzban/jinx_path)"
python - "$BASE" "$JX_ID" <<'PY'
import http.client, sys
from urllib.parse import urlsplit
base, secret = sys.argv[1], sys.argv[2]
u = urlsplit(base)
for suffix, label in (("/v", "VLESS"), ("/m", "VMess"), ("/t", "Trojan")):
    c = http.client.HTTPConnection(u.hostname, u.port, timeout=12)
    c.request("GET", f"/cdn/{secret}{suffix}", headers={
        "Host": u.netloc, "Upgrade": "websocket", "Connection": "Upgrade",
        "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==", "Sec-WebSocket-Version": "13"
    })
    r = c.getresponse()
    assert r.status == 101, f"{label} WebSocket upgrade returned HTTP {r.status}"
    c.close()
    print(f"[smoke] Nginx -> Xray {label} WebSocket handshake: OK")
PY

# Stop and recreate the container against the SAME named volume.
docker rm -f "$NAME" >/dev/null
start_panel
wait_panel
TOKEN="$(login)"
curl --fail --silent --show-error "$BASE/api/user/$USER" \
  -H "Authorization: Bearer $TOKEN" \
  | python -c 'import json,sys; assert json.load(sys.stdin)["username"]=="jinx_ci_smoke"'
JX_ID_AFTER="$(docker exec "$NAME" cat /var/lib/marzban/jinx_path)"
test "$JX_ID" = "$JX_ID_AFTER"
echo "[smoke] database + secret subscription path survive container recreation: OK"

# Fresh-install path: the owner password is supplied explicitly as a test secret.
AUTO_PASSWORD="ci-fixed-owner-password-2026!"
docker volume create "$AUTO_VOLUME" >/dev/null
docker run -d --name "$AUTO_NAME" \
  -p 127.0.0.1:18081:8080 \
  -v "$AUTO_VOLUME:/var/lib/marzban" \
  -e ADMIN_USERNAME="$ADMIN" \
  -e ADMIN_PASSWORD="$AUTO_PASSWORD" \
  -e XRAY_SUBSCRIPTION_URL_PREFIX="$AUTO_BASE" \
  -e PANEL_DOMAIN="ci.example.net" \
  "$IMAGE" >/dev/null
AUTO_HEALTHY=0
for _ in $(seq 1 120); do
  AUTO_STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' "$AUTO_BASE/health" 2>/dev/null || true)"
  if [[ "$AUTO_STATUS" == "200" ]]; then AUTO_HEALTHY=1; break; fi
  if ! docker inspect -f '{{.State.Running}}' "$AUTO_NAME" 2>/dev/null | grep -q true; then
    echo "Fixed-admin fresh install container exited before becoming healthy" >&2
    docker logs "$AUTO_NAME" || true
    exit 1
  fi
  sleep 2
done
test "$AUTO_HEALTHY" = "1" || { docker logs "$AUTO_NAME" || true; echo "Fixed-admin fresh install did not become healthy" >&2; exit 1; }

AUTO_TOKEN="$(curl --fail --silent --show-error -X POST "$AUTO_BASE/api/admin/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=$ADMIN" \
  --data-urlencode "password=$AUTO_PASSWORD" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"
test -n "$AUTO_TOKEN"
echo "[smoke] configured POMP NET owner login on fresh install: OK"

docker rm -f "$AUTO_NAME" >/dev/null
docker run -d --name "$AUTO_NAME" \
  -p 127.0.0.1:18081:8080 \
  -v "$AUTO_VOLUME:/var/lib/marzban" \
  -e ADMIN_USERNAME="$ADMIN" \
  -e ADMIN_PASSWORD="$AUTO_PASSWORD" \
  -e XRAY_SUBSCRIPTION_URL_PREFIX="$AUTO_BASE" \
  -e PANEL_DOMAIN="ci.example.net" \
  "$IMAGE" >/dev/null
AUTO_HEALTHY=0
for _ in $(seq 1 120); do
  AUTO_STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' "$AUTO_BASE/health" 2>/dev/null || true)"
  if [[ "$AUTO_STATUS" == "200" ]]; then AUTO_HEALTHY=1; break; fi
  if ! docker inspect -f '{{.State.Running}}' "$AUTO_NAME" 2>/dev/null | grep -q true; then
    echo "Fixed-admin container exited after recreation" >&2
    docker logs "$AUTO_NAME" || true
    exit 1
  fi
  sleep 2
done
test "$AUTO_HEALTHY" = "1" || { docker logs "$AUTO_NAME" || true; echo "Fixed-admin container did not recover after recreation" >&2; exit 1; }
curl --fail --silent --show-error -X POST "$AUTO_BASE/api/admin/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$ADMIN" \
  --data-urlencode "password=$AUTO_PASSWORD" \
  | python -c 'import json,sys; assert json.load(sys.stdin).get("access_token"); print("[smoke] fixed owner login survives container recreation: OK")'

# Existing admin recovery path: an explicitly requested reset changes the existing owner password.
# Stop the previous container first; never mount the same SQLite volume twice.
docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$RESET_NAME" \
  -p 127.0.0.1:18082:8080 \
  -v "$VOLUME:/var/lib/marzban" \
  -e ADMIN_USERNAME="$ADMIN" \
  -e ADMIN_PASSWORD="$PASSWORD" \
  -e RESET_ADMIN_PASSWORD=1 \
  -e XRAY_SUBSCRIPTION_URL_PREFIX="http://127.0.0.1:18082" \
  "$IMAGE" >/dev/null
for _ in $(seq 1 120); do
  RESET_STATUS="$(curl --silent --output /dev/null --write-out '%{http_code}' "http://127.0.0.1:18082/health" 2>/dev/null || true)"
  if [[ "$RESET_STATUS" == "200" ]]; then break; fi
  if ! docker inspect -f '{{.State.Running}}' "$RESET_NAME" 2>/dev/null | grep -q true; then
    docker logs "$RESET_NAME" || true
    echo "Admin recovery container exited" >&2
    exit 1
  fi
  sleep 2
done
curl --fail --silent --show-error -X POST "http://127.0.0.1:18082/api/admin/token" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "username=$ADMIN" \
  --data-urlencode "password=$PASSWORD" \
  | python -c 'import json,sys; assert json.load(sys.stdin).get("access_token"); print("[smoke] one-time existing-admin recovery: OK")'
