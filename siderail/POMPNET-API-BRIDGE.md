# POMP NET → SideRail API bridge

The existing POMP NET helper is exposed by the existing Nginx `/jinx-api/` location and runs on loopback port 8090. This change adds a narrowly allow-listed SideRail API bridge at:

- `GET /jinx-api/siderail/status`
- `GET /jinx-api/siderail/health`
- `GET /jinx-api/siderail/system`
- `GET|POST /jinx-api/siderail/users`
- `GET|PUT|DELETE /jinx-api/siderail/users/{id}`
- `GET /jinx-api/siderail/users/{id}/ips`
- `POST /jinx-api/siderail/users/{id}/toggle`
- `POST /jinx-api/siderail/users/{id}/reset-traffic`
- `POST /jinx-api/siderail/users/{id}/rotate-token`
- `GET|PATCH /jinx-api/siderail/inbounds[/{id}]`
- `GET /jinx-api/siderail/activity`
- `GET|POST|PUT|DELETE /jinx-api/siderail/routing[/{id}]`
- `GET|PUT /jinx-api/siderail/settings`
- `GET /jinx-api/siderail/stats/traffic`
- `GET|POST /jinx-api/siderail/admins`, plus owner-only item updates
- `GET /jinx-api/siderail/backup/export`

## Authentication

Every bridged request first validates the existing POMP NET administrator bearer token using the current helper's `caller(True)` check. Only a POMP NET super-admin can use this bridge. The helper then authenticates to SideRail with a server-side SideRail owner account and calls SideRail with its JWT bearer token. Neither the SideRail password nor its JWT is sent to browser JavaScript or returned in the response.

Configure these variables as server-side secrets on the POMP NET service:

- `SIDERAIL_INTERNAL_URL` — private/internal URL of the SideRail service (preferred).
- `SIDERAIL_OWNER_USERNAME` — SideRail owner username.
- `SIDERAIL_OWNER_PASSWORD` — SideRail owner password.

`SIDERAIL_URL` is accepted as a fallback for the base URL. Never commit the credentials or paste them into GitHub source. The helper caches the SideRail JWT in process memory for at most six days and re-authenticates once after an upstream 401.

The bridge is an allow-listed proxy, not an open proxy. The destructive `POST /api/backup/import` endpoint is deliberately not exposed. SideRail setup/login credentials cannot be changed through the bridge.

## Important integration boundary

This implements a server-side API bridge, but it does not yet rewrite the legacy Marzban dashboard's browser API contract. The existing dashboard still sends its current requests to the existing Marzban-compatible routes. A frontend integration step must call the new `/jinx-api/siderail/*` endpoints and present SideRail data/actions, or the legacy API routes must be migrated one by one with compatibility tests. No production dashboard traffic is switched by this change.

The bridge also does not provide public SideRail subscription proxying. Existing `/sub/{token}` URLs remain on the existing subscription path until a verified token mapping and subscription compatibility layer is deployed.

## Validation status

Static Python compilation and migration converter unit tests are added to GitHub Actions. Live bridge authentication, SideRail CRUD, public subscription fetches, Railway deployment and Xray client handshake still require the SideRail service to be running. The connected Railway account currently rejects project creation because its trial has expired; therefore these live checks cannot be completed from this account at present.
