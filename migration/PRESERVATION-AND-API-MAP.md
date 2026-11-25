# POMP NET — UI preservation and 3X-UI compatibility contract

This contract is for the staging migration only. It is intentionally additive: it does not edit the existing login page, dashboard, subscription template, Nginx routes, Dockerfile, startup script, or persistent database.

## Non-negotiable preservation boundary

The following user-facing assets must remain byte-for-byte unchanged during the engine migration unless the owner explicitly requests a separate redesign:

- `pompnet-dashboard.html` — existing POMP NET dashboard, layout, menus, buttons, and browser-side behavior.
- `sub.html` — existing subscription page and its design/controls.
- Existing login page and the public login URL/flow.
- Existing public `/sub/{token}` URLs. A compatibility lookup must resolve old tokens; a new random token must not silently replace an existing one.
- Existing branding and navigation.

The backend may be replaced only behind the existing HTTP contract. No frontend redesign is part of this migration.

## Confirmed dashboard HTTP contract

Static inspection of `pompnet-dashboard.html` found these Marzban-compatible calls:

| Existing request | Current purpose | Required 3X-UI adapter behavior |
|---|---|---|
| `POST /api/admin/token` | Dashboard login; browser expects an access token | Authenticate against 3X-UI server-side and issue a short-lived POMP NET adapter token. Never return 3X-UI credentials/cookies to JavaScript. |
| `GET /api/users` | Populate user list | Read all permitted clients from 3X-UI inbounds and normalize to the existing response fields. |
| `POST /api/user` | Create a user | Validate the existing request shape, create a client in the selected supported inbound, persist mapping and return the exact response shape expected by current JS. |
| `DELETE /api/user/{username}` | Delete a user | Resolve the username to its mapped inbound/client and remove only that client; do not delete an entire inbound. |
| `GET /api/system` | Dashboard system statistics | Return live engine health and normalized traffic/user counts; never fabricate values. |

The dashboard source also references the legacy user detail route prefix `/api/user/`; every actual suffix used by the browser must be inventoried before claiming feature parity. Other features such as reset, revoke, QR, expiry, quota, and subscription are not assumed complete merely because the five calls above exist.

## Existing subscription contract

- Nginx currently forwards `/sub/*` to the Marzban service.
- The existing subscription HTML is separately installed as the Marzban subscription template.
- The subscription page must not be replaced with the upstream JinX page as part of this task.
- A durable mapping store must map each legacy subscription token to one or more 3X-UI clients. Store only a hash of the public token where practical; preserve the original token value only if migration requirements make that unavoidable.
- Subscription output must retain the existing content type, profile headers, update interval, support URL, and app-compatible URI formats after they are measured from current production behavior.
- A missing mapping must return a clear 404, never another user's configuration.

## Authentication design requirement

3X-UI uses its own login/session mechanism, which is not interchangeable with Marzban's OAuth-style `/api/admin/token` JWT contract. The adapter therefore needs its own signed, expiring bearer token and role checks. It must:
1. Validate the administrator credentials against 3X-UI through a server-side HTTP client.
2. Keep the 3X-UI cookie and credentials server-side only.
3. Issue an adapter token with an expiry and invalidate it on credential change.
4. Protect every dashboard API route, including read-only statistics.
5. Avoid logging passwords, cookies, tokens, UUIDs, or subscription URLs.

## Data migration rules

- Never mount the Marzban volume at `/etc/x-ui`; the SQLite schemas are unrelated.
- Never initialize a fresh 3X-UI database over the only copy of the old data.
- Export users, UUIDs, expiry, data limits, enabled state, inbounds, stream settings, and subscription tokens before conversion.
- Preserve UUIDs where 3X-UI accepts them.
- Translate only settings with a verified equivalent. Emit a per-user/per-inbound exception report for unsupported settings.
- Traffic counters require an explicit baseline strategy; do not claim historical traffic was preserved if only the current total can be seeded.
- Keep the old volume and a verified backup untouched until external client tests pass and rollback is proven.

## Railway transport boundary

The upstream JinX-X4G Dockerfile uses 3X-UI v2.9.4 and a new `/etc/x-ui` data directory. Its Nginx template routes a VLESS WebSocket path to Xray. Railway's public HTTPS 443 terminates at the platform edge; the internal app listens on 8080. This is not a raw TCP Xray listener on public port 443. Any generated link must match the actual deployed WS path, TLS termination, host, and inbound configuration.

## Acceptance tests required before cutover

1. Existing login URL renders the same login page; valid owner login succeeds; invalid login fails.
2. Existing dashboard HTML/CSS/JS hashes are unchanged.
3. Existing subscription page HTML hash is unchanged.
4. Existing `/sub/{token}` token returns the same user's converted configuration; unknown token returns 404.
5. Dashboard list, create, detail, enable/disable, reset, delete, expiry, quota, and traffic operations all have verified 3X-UI-backed implementations or are explicitly marked unavailable in UI.
6. Create one VLESS client; verify its UUID and generated URI against the live inbound.
7. Fetch subscription from an external network and import it into v2rayNG.
8. Establish a real Xray handshake and transfer traffic; a successful HTTP response alone is not proof of VPN connectivity.
9. Restart and redeploy with the new volume; verify database and client persistence.
10. Demonstrate rollback to the untouched old deployment and volume.

## Current honest status

The current repository is still Marzban-based. The reference repository confirms the 3X-UI v2.9.4 base and its Railway/Nginx layout, but does not provide a drop-in Marzban API adapter. The existing login, dashboard, and subscription assets have not been modified by this contract commit. No 3X-UI adapter, data conversion, build, deployment, or external VPN handshake is claimed complete.
