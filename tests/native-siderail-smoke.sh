#!/usr/bin/env bash
set -Eeuo pipefail
IMAGE="${1:-pompnet-super-jinx:ci}"
NAME="pompnet-native-siderail-smoke"
VOLUME="pompnet-native-siderail-smoke-data"
BASE="http://127.0.0.1:18080"
ADMIN="pompnet_ci_owner"
PASSWORD="ci-only-$(python -c 'import secrets; print(secrets.token_urlsafe(24))')"
cleanup(){ docker rm -f "$NAME" >/dev/null 2>&1 || true; docker volume rm "$VOLUME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker volume create "$VOLUME" >/dev/null
docker run -d --name "$NAME" -p 127.0.0.1:18080:8080 -v "$VOLUME:/var/lib/marzban" \
  -e ADMIN_USERNAME="marzban-ci-unused" -e ADMIN_PASSWORD="$PASSWORD" \
  -e SIDERAIL_DATA_DIR=/var/lib/marzban/siderail -e CORE_DIR=/var/lib/marzban/siderail/core \
  -e XRAY_SUBSCRIPTION_URL_PREFIX="$BASE" -e PANEL_DOMAIN="ci.example.net" "$IMAGE" >/dev/null
for _ in $(seq 1 120); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/healthz" || true)"
  [[ "$code" == "200" ]] && break
  docker inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null | grep -q true || { docker logs "$NAME"; exit 1; }
  sleep 2
done
[[ "$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/healthz")" == "200" ]]
HTML="$(curl --fail --silent --show-error "$BASE/")"
grep -q 'id="root"' <<< "$HTML"
STATUS="$(curl --fail --silent --show-error "$BASE/api/status")"
grep -q '"setup":false' <<< "$STATUS"
TOKEN="$(curl --fail --silent --show-error -X POST "$BASE/api/setup" -H 'Content-Type: application/json' \
  --data "$(python -c 'import json,os; print(json.dumps({"username":os.environ["CI_OWNER"],"password":os.environ["CI_PASS"]}))' CI_OWNER="$ADMIN" CI_PASS="$PASSWORD")" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
curl --fail --silent --show-error "$BASE/api/me" -H "Authorization: Bearer $TOKEN" \
  | python -c 'import json,sys; d=json.load(sys.stdin); assert d["admin"]["role"]=="owner"'
INBOUNDS="$(curl --fail --silent --show-error "$BASE/api/inbounds" -H "Authorization: Bearer $TOKEN")"
INBOUND_ID="$(printf '%s' "$INBOUNDS" | python -c 'import json,sys; a=json.load(sys.stdin); assert a; print(a[0]["id"])')"
curl --fail --silent --show-error -X POST "$BASE/api/users" -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' --data "$(python -c 'import json,sys; print(json.dumps({"email":"ci-native-user","dataLimit":0,"expireDays":30,"inboundIds":[int(sys.argv[1])]}))' "$INBOUND_ID")" \
  | python -c 'import json,sys; d=json.load(sys.stdin); assert d["email"]=="ci-native-user"'
curl --fail --silent --show-error "$BASE/api/users" -H "Authorization: Bearer $TOKEN" \
  | python -c 'import json,sys; d=json.load(sys.stdin); assert any(u["email"]=="ci-native-user" for u in d["users"])'
echo "[smoke] Native SideRail SPA, setup/login, authenticated API, inbound read and real user creation: OK"
