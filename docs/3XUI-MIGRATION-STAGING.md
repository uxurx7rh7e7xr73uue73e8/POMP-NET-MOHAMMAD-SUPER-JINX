# POMP NET — 3X-UI migration staging

## Safety status

This branch is a staging branch only. It intentionally does not replace the production Dockerfile, startup script, Nginx routes, Marzban database, or Railway volume. Do not deploy it to the existing production service yet.

## Required end state

- Keep the existing POMP NET dashboard HTML/CSS/JS and its visible navigation.
- Replace the Marzban control plane with the pinned 3X-UI/Xray engine.
- Keep public subscription URLs stable (including the existing `/sub/{token}` route) through an explicit compatibility mapping.
- Preserve user UUIDs, expiry, data limits, enable/disable state, and subscription metadata where a deterministic mapping is possible.
- Keep the existing Marzban volume untouched as a rollback/source archive until migration is verified.

## Confirmed architecture mismatch

The current production branch is Marzban-based:
- Docker image: `gozargah/marzban:latest`
- SQLite database: `/var/lib/marzban/db.sqlite3`
- Xray configuration: `/var/lib/marzban/xray_config.json`
- Startup exports Marzban's `SQLALCHEMY_DATABASE_URL`, `XRAY_JSON`, and starts the Marzban service.

The reference JinX-X4G project is 3X-UI-based:
- Image: `ghcr.io/mhsanaei/3x-ui:v2.9.4`
- 3X-UI database directory: `/etc/x-ui`
- 3X-UI SQLite database: `/etc/x-ui/x-ui.db`
- Nginx fronts the web panel and Xray WebSocket traffic on the Railway service port.

These databases and APIs are not interchangeable. Mounting the existing Marzban volume at `/etc/x-ui` does not migrate users or inbounds.

## Compatibility work that must be implemented before cutover

1. Inventory the exact existing dashboard API calls and Nginx routes, especially `/api/*`, `/sub/*`, `/jinx-api/*`, `/doctor/*`, login, user CRUD, usage, reset, expiry, and QR generation.
2. Implement a backend adapter for each dashboard operation using authenticated 3X-UI API calls. Never expose the 3X-UI admin credentials to browser JavaScript.
3. Create a persistent mapping table from each legacy Marzban subscription token to a 3X-UI client/subscription identifier. Keep the public URL path unchanged.
4. Export and validate the Marzban users/inbounds first. Convert supported protocols/settings to 3X-UI/Xray inbounds; report unsupported fields instead of silently dropping them.
5. Verify that each migrated client retains its UUID, expiry, quota, enabled state, and transport/security settings. Usage counters may need a documented baseline because the schemas differ.
6. Run the new engine on a separate Railway service and a NEW volume mounted at `/etc/x-ui`. Do not reuse `/var/lib/marzban`.
7. Verify health, admin login, create/disable/delete client, generated VLESS link, subscription fetch, QR payload, and a real Xray handshake from an external client.
8. Only after successful checks, switch the existing public domain/routes. Keep the original volume and deployment available for rollback.

## Railway constraints

Railway's public HTTPS domain terminates TLS at the edge; the app's internal Nginx target is normally port 8080. This does not mean raw Xray TCP port 443 is exposed. For a single public Railway domain, Xray traffic must use a supported WebSocket path through Nginx.

Required new service configuration for staging:
- Dockerfile: the 3X-UI derivative Dockerfile, after integration work is complete.
- Volume: new volume, mount path `/etc/x-ui`.
- Target port: 8080 (Nginx listener).
- Secrets: a user-supplied strong 3X-UI admin username/password; never commit them.
- No production domain cutover until end-to-end tests pass.

## License and attribution

The reference JinX-X4G repository declares GPL-3.0. Any derivative distribution must retain the applicable license and upstream copyright notices. POMP NET branding must not imply an official partnership or endorsement.

## Current completion state

- [x] Isolated staging branch created from current `main`.
- [x] Current and reference architectures inspected.
- [x] Migration hazards and acceptance checks documented.
- [ ] 3X-UI engine integrated into a separate staging build.
- [ ] Dashboard API compatibility adapter implemented.
- [ ] Legacy subscription-token compatibility mapping implemented.
- [ ] Data export/conversion and validation implemented.
- [ ] Docker build and runtime smoke tests passed.
- [ ] Railway staging service and separate volume deployed.
- [ ] External v2rayNG connection verified.
- [ ] Production cutover approved and completed.

This file is a migration plan, not a claim that the migration or live connection is already complete.
