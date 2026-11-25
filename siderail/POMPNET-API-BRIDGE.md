# POMP NET ↔ SideRail live API and subscription compatibility layer

The current POMP NET dashboard now contains a SideRail page. It reuses the existing POMP NET admin login/session; it does not ask the operator to paste SideRail credentials into the browser.

## API path

The dashboard calls `/jinx-api/siderail/*`. The existing helper at loopback port 8090 validates the current POMP NET bearer token through the existing panel's `/api/admin` endpoint and requires `is_sudo=true`. It then authenticates to SideRail server-to-server. SideRail password and JWT never leave the helper process.

On the first authenticated SideRail request, the helper checks `/api/status`. If SideRail reports `setup=false`, it initializes the first owner exactly once using the server-side owner username/password. It never resets an already initialized SideRail database.

Configure these secrets on the POMP NET service:
- `SIDERAIL_INTERNAL_URL` — SideRail internal URL, e.g. the private Railway service URL.
- `SIDERAIL_OWNER_USERNAME` — SideRail owner username.
- `SIDERAIL_OWNER_PASSWORD` — SideRail owner password.

Do not commit credentials to Git. The helper caches the SideRail JWT in process memory and renews it after an upstream 401.

The allow-list covers SideRail status, system metrics/restart, users and per-user operations, inbounds, proxy sources/scan/test/check, routing and presets, activity, Telegram bot settings/test, settings/credentials, admin management, traffic stats, and backup export/import. All calls require the POMP NET super-admin session. Backup import is destructive to SideRail users/inbounds only and is exposed solely to this owner-authenticated route; the UI displays a confirmation warning. It never changes Marzban.

## Existing subscription URL compatibility

Nginx now routes public `GET /sub/*` requests through the helper:
1. If `SIDERAIL_INTERNAL_URL` is configured and the path is a supported SideRail token route, the helper tries SideRail's public `/sub/{token}` (or `/json`, `/clash`, `/singbox`) endpoint first.
2. A SideRail HTTP 404 means the token is not imported there; the request falls back to the exact existing Marzban/optional 3X-UI subscription backend.
3. A SideRail HTTP 410 (expired) is returned as-is. Network failure returns 503 rather than silently sending an imported user's token to the wrong database.
4. Legacy Marzban tokens that have not been migrated continue to use the old subscription backend.
5. Original token text, path, query string, User-Agent, host, content type, `Subscription-Userinfo`, `Profile-Update-Interval` and `Profile-Title` are preserved.

The SideRail backup converter preserves the old Marzban token values where SideRail can represent the user. After a successful import, those old `/sub/{token}` URLs resolve against SideRail without changing the URL printed on the user's device. Unsupported or rejected users remain on Marzban.

## Dashboard

The existing POMP NET login and primary dashboard remain. A new `SideRail` navigation page uses the existing POMP NET bearer token to:
- Read SideRail status, Xray/system state, users and inbounds.
- Create users with real SideRail inbound assignments.
- Enable/disable, reset traffic, rotate subscription token and delete users.
- Enable/disable inbounds.
- View routing, activity, bot configuration, settings and admins.
- Export/import SideRail backups.

This is a real UI-to-API integration, but it does not mean the remote SideRail service is live. The page reports connection errors until the SideRail Railway service and its variables exist.

## Required validation before production cutover

GitHub Actions now checks the dashboard JavaScript, helper syntax, migration tests, both Docker builds, SideRail runtime health, SideRail Xray config validation, SideRail VLESS/VMess/Trojan WS HTTP 101 handshakes, POMP NET runtime, and existing POMP NET Xray WS handshakes.

The connected Railway account has an expired trial and has rejected project creation. Consequently no Railway service or independent `/data` volume has been provisioned yet. The local Docker smoke test is not a public client connection test.

No actual Marzban user export has been imported. The existing Marzban database, volume, owner login and dashboard data are unchanged. Do not switch production traffic until the SideRail service and persistent volume are deployed, a protected backup is made, a real inbound map is reviewed, user migration is imported and compared, and an external v2rayNG client handshake and rollback test pass.
