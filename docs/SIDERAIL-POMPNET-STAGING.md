# POMP NET × SideRail — integrated staging

## SideRail runtime included

The separate `siderail` Docker image builds the complete official SideRail server and React web app from upstream commit `6d794ce2303a01ecc412941a4f38fd00a3bda65b`. It is not a mock or a rewritten clone.

Upstream capabilities included:
- Owner setup/login, JWT/cookie auth, admin accounts, per-page permissions, expiry and quotas.
- System metrics, CPU/RAM/storage, uptime, server/inbound traffic and usage history.
- User create/edit/delete, enable/disable, UUID/password, expiry, quota, traffic reset, IP limit, inbound assignment, comments, Telegram ID, connected-IP history and subscription token rotation.
- Xray inbounds, proxy source scan/test/geolocation, address/Host/SNI settings and inbound toggles.
- Routing/block rules and presets.
- Subscription pages, QR/config links and supported client formats.
- Activity log, Telegram notifications, daily backups, backup export/import, Xray restart and auto-restart.
- Fragment/ECH options where supported by upstream.

The POMP NET palette overlay and Persian RTL option are applied during the build. Primary dashboard, users, inbounds, routing, settings, bot, activity and subscription flows have Persian translations; some low-frequency labels still fall back to English. SideRail author attribution, license, watermark, headers and signature remain.

## Railway service and persistent storage

`siderail/railway.json` configures a separate Railway service. Select it as the config file for that service and attach a dedicated Railway Volume mounted at `/data`. Never attach or reuse the Marzban volume.

Required SideRail variables:
- `PORT=8080`
- `SIDERAIL_DATA_DIR=/data`
- `CORE_DIR=/data/core`
- `CORE_VERSION=v26.9.9`
- `CORE_API_PORT=10085`
- `CORE_INBOUND_BASE_PORT=20000`
- `NODE_ENV=production`
- `JWT_SECRET` — unique long secret (at least 48 random bytes encoded as hex).

The POMP NET service must have these server-side secrets:
- `SIDERAIL_INTERNAL_URL` — private URL of the SideRail service (preferred).
- `SIDERAIL_PUBLIC_URL` — HTTPS public URL of the full SideRail web app; the owner-only POMP NET page displays a launch button for it.
- `SIDERAIL_OWNER_USERNAME`
- `SIDERAIL_OWNER_PASSWORD`

The authenticated POMP NET bridge checks SideRail `/api/status` and initializes the SideRail owner exactly once if the persistent database is empty. It never resets an existing SideRail database. Do not place these credentials in browser code or GitHub source.

The connected Railway account has an expired trial and has rejected project creation with a plan-selection requirement. Therefore no Railway project/service/Volume has been created yet. The CI named Docker volume is only an automated local persistence test, not a Railway Volume.

## POMP NET API and dashboard integration

The existing POMP NET dashboard now includes a SideRail management page. It reuses the current POMP NET super-admin login and calls `/jinx-api/siderail/*`.

The helper:
- Validates the current POMP NET administrator token and requires `is_sudo=true`.
- Authenticates to SideRail server-to-server with secrets stored only in service variables.
- Caches and refreshes the SideRail JWT.
- Exposes an allow-list for status/system, users and per-user actions, inbounds, proxy tools, routing, activity, bot, settings, admins, traffic stats and backup export/import.
- Does not expose SideRail credentials or JWT to the browser.

The dashboard can read system/users/inbounds, create SideRail users, enable/disable/reset/rotate/delete users, toggle inbounds, view routing/activity/bot/settings/admins, and export/import SideRail backups. Backup import is owner-only and replaces SideRail users/inbounds; it does not touch Marzban.

## Existing subscription URL compatibility

When `SIDERAIL_INTERNAL_URL` (or `SIDERAIL_URL`) is configured, Nginx routes public `GET /sub/*` requests through the SideRail-first gateway:
1. Try SideRail for supported `/sub/{token}`, `/json`, `/clash`, and `/singbox` paths.
2. If SideRail returns 404, fall back to the original Marzban or optional 3X-UI subscription backend.
3. Return SideRail 410 expiry as-is; if SideRail is unreachable, return 503 rather than silently sending an imported token to the wrong database.
4. Preserve the old public token path and relevant subscription response headers.

When SideRail is not configured, startup rewrites only the dedicated subscription upstream back to the original Marzban/3X-UI backend. Existing subscriptions therefore retain their previous behavior until the SideRail URL is explicitly configured.

The Marzban converter preserves supported old subscription token values, allowing migrated users to keep their old `/sub/{token}` URL. Unsupported users are rejected and remain on the legacy backend.

## Safe Marzban migration

`migration/export_marzban_users.py` is a read-only export. `migration/marzban_to_siderail_backup.py` converts the protected export into SideRail v2 backup format and refuses unsupported protocols/transports, ambiguous per-protocol credentials, missing inbound maps and duplicate IDs/tokens. It preserves supported user IDs, UUID/password, subscription token, expiry, data quota, used traffic total, IP limit, enabled state, notes and inbound assignments.

SideRail supports VLESS/VMess/Trojan over WS/XHTTP/HTTPUpgrade in this pinned model. Reality, gRPC, raw TCP, Shadowsocks, Hysteria/TUIC and other unsupported inbounds are not silently migrated. Upload the generated backup only to a fresh isolated SideRail database after reviewing the inbound map and backup. No actual user export has been imported in this session.

## Automated validation

GitHub Actions now runs:
- Python syntax and migration converter unit tests.
- POMP NET Docker build, existing dashboard/API routes, old subscription fallback, and Xray WebSocket handshakes.
- SideRail Docker build, runtime health, first-owner setup, API user creation, Xray config validation, SideRail VLESS/VMess/Trojan WS handshakes, and persistent `/data` database check across container restart.
- An end-to-end POMP NET + SideRail container-network test: authenticate with the existing POMP NET owner, bootstrap SideRail, create a SideRail user through the bridge, fetch its subscription through the old public `/sub/{token}` route, and verify an unmigrated Marzban token still falls back to Marzban.
- A VLESS client-core test is included to send traffic through the SideRail Xray server to a local HTTP echo service; this is stronger than merely checking that the Xray process exists.

A local Docker test is not the same as a public Railway/v2rayNG client test. Do not claim a live deployment or public client connection until Railway provisioning and external testing succeed.

## Production safety

The existing POMP NET production Dockerfile, Marzban database/volume, owner login, dashboard and legacy subscription backend remain preserved. Do not cut over or remove Marzban until:
1. Railway SideRail service and independent `/data` Volume exist.
2. Protected Marzban export and real inbound mapping are reviewed.
3. Imported user/token counts and per-user settings are compared.
4. Old subscription URLs are fetched successfully for migrated and unmigrated users.
5. A public v2rayNG client connection and rollback test succeed.

## License and attribution

The upstream SideRail LICENSE, README, author attribution, headers, signature and watermark remain in the build. This project does not claim authorship of upstream SideRail code.
