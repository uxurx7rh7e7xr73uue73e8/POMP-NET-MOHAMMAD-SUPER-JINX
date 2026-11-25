# POMP NET Railway Xray rebuild — engineering gate

## Scope

Target: keep the existing POMP NET login, dashboard, subscription page, and branding while moving the data plane to an independently managed Xray-core process hosted entirely on Railway. No VPS and no external SSH node.

This document is an implementation gate, not a claim that the migration is already deployed.

## Reference-project findings

The public SideRail repository documents a Railway-specific architecture:
- one Docker service exposed through Railway HTTP ingress on port 8080;
- TLS is terminated at Railway's edge and client profiles use the public HTTPS hostname, port 443, and TLS;
- the application proxies supported WebSocket / HTTPUpgrade / XHTTP paths to private Xray listeners;
- Xray's stats API and inbound listeners remain loopback-only;
- persistent state is stored under a Railway Volume mounted at /data;
- raw TCP, gRPC, WireGuard and Hysteria are not supported by that HTTP-edge architecture.

The SideRail repository has a proprietary, all-rights-reserved license. POMP NET must not copy its source, UI, assets, or remove its attribution. This project will independently implement equivalent general capabilities and retain its own POMP NET interface.

## Existing POMP NET facts

The current production Dockerfile is based on `gozargah/marzban:latest`. The current startup script launches Marzban and its managed Xray configuration. The optional 3X-UI bridge is a staging integration and is not the independent Railway Xray engine. Therefore changing only environment variables or enabling that bridge does not accomplish the requested migration.

Existing UI and `sub.html` must remain intact. Do not replace them with a template or mock API.

## Required target architecture

1. Railway web service: existing POMP NET HTTP entry point, login, dashboard, API and subscription routes.
2. Xray runtime: independently launched Xray-core process in the same Railway service/container, with an explicit supervisor and health checks. It must not share listener ports with Marzban's embedded Xray.
3. Control plane: authenticated internal API for users, inbounds, quotas, expiry, enable/disable, reset traffic and generated links. No public unauthenticated engine API.
4. State: SQLite and generated config under the persistent Railway Volume; atomic writes and backup before schema/config migration.
5. Edge transport: WebSocket / HTTPUpgrade / XHTTP over the Railway HTTPS edge only, using the public Railway hostname and TLS on client profiles. No claim of raw TCP/UDP support through HTTP ingress.
6. Stats: Xray StatsService/HandlerService where supported by the pinned Xray version; counters must be read from the running engine, not fabricated from database values.
7. Subscription: existing POMP NET page and route preserved; generated links must match the actual listener, path, hostname, TLS and UUID/password in the running config.

## Safety gates before switching production

- Pin a tested Xray release and verify its checksum.
- Prove the binary runs in the final Docker image.
- Validate generated JSON with `xray run -test -config ...`.
- Start the engine and verify each configured inbound is listening locally.
- Exercise authenticated create / edit / disable / delete and verify the persisted config after restart.
- Verify generated VLESS / VMess / Trojan links match the runtime config.
- Verify Railway Volume is mounted at `/data` and survives redeploy.
- Confirm Railway networking supports the chosen HTTP-based transport paths.
- Run a real external client test (v2rayNG) before calling any profile working.
- Only after all gates pass, change the dashboard API adapter from Marzban to the new engine. Until then, preserve the current production runtime and data.

## Known deployment blocker

The connected Railway integration currently has Viewer-only access. It cannot inspect or change service variables, attach a Volume, deploy, or read runtime logs. GitHub source changes can be prepared, but live Railway deployment and connectivity cannot be truthfully marked complete without deploy-level Railway access.

## Current status

- [x] Confirmed current Docker base is Marzban.
- [x] Confirmed existing 3X-UI bridge is opt-in and not the standalone Railway engine.
- [x] Confirmed reference transport model and license restriction.
- [ ] Independent Xray supervisor integrated into production startup.
- [ ] POMP NET CRUD API switched to the independent engine.
- [ ] Persistent Railway Volume configured and verified.
- [ ] CI runtime tests against the final image.
- [ ] Railway deployment and external v2rayNG test.
