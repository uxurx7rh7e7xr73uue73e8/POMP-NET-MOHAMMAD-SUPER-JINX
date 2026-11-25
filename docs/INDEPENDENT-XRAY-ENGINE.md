# POMP NET independent Xray engine (Railway staging)

This branch adds a separate Xray process and registry without touching the current
Marzban database, its Xray config, login page, dashboard, or subscription template.

## What is implemented in this phase

- Independent Xray process using the Xray executable already present in the image.
- Separate persistent SQLite registry and generated config under
  `/var/lib/marzban/pompnet-engine/`.
- Three Railway HTTP-edge transports: VLESS WebSocket, VMess WebSocket, Trojan
  WebSocket. TLS is terminated by Railway on public port 443; Xray listens only
  on loopback ports 21001-21003.
- Config validation with `xray run -test` before replacing the last config and
  restarting the independent process.
- Owner-only API authentication by validating the existing Marzban bearer token
  against `GET /api/admin` and requiring `is_sudo=true`.
- User create/list/toggle/delete, UUID/password generation, expiry auto-disable,
  share links, and a base64 subscription endpoint.
- Nginx routes:
  - `/pompnet-engine/api/users`
  - `/pompnet-engine/api/inbounds`
  - `/pompnet-engine/health`
  - `/pompnet-sub/<subscription-token>`
  - `/pompnet/vless`, `/pompnet/vmess`, `/pompnet/trojan`

## API examples

Use the existing owner access token in the Authorization header:

```http
GET /pompnet-engine/api/inbounds
GET /pompnet-engine/api/users
POST /pompnet-engine/api/users
Content-Type: application/json

{"username":"client01","protocol":"vless","expire":0,"data_limit_gb":0}
```

Supported protocol values are `vless`, `vmess`, and `trojan`.
`expire` is a Unix timestamp; zero means no expiry. The API currently stores
`data_limit_gb` as metadata only. **Traffic accounting, quota enforcement,
connected-IP reporting, user roles/reseller limits, backup/restore, and a
dedicated graphical user-management screen are not implemented in this phase.**
Do not treat the stored quota field as an enforced quota.

## Railway requirements and limitations

- Keep the existing persistent Volume mounted at `/var/lib/marzban`; the new
  registry lives inside it. Do not move or replace the existing volume.
- Keep the public Railway domain target port at 8080.
- This design uses Railway's HTTPS ingress and WebSocket transports only.
  Raw TCP, UDP, Reality, gRPC, Hysteria2, and TUIC are not exposed by these
  routes.
- The existing Marzban-managed Xray remains active during this staged phase.
  The new engine uses separate ports and data. No existing users are migrated
  automatically; no current subscription links are rewritten.
- The POMP NET dashboard keeps its existing visual design and login flow; its user, inbound, system and diagnostics API calls now route to the independent engine. The existing Marzban subscription template and `/sub/` route remain unchanged; new engine subscriptions use `/pompnet-sub/`.

## Verification status

The code is committed to the feature branch. GitHub Actions run 308 passed Python syntax validation, JSON validation, Docker image build, and the existing Marzban runtime smoke test at the earlier engine commit. The later multi-protocol/dashboard adapter changes still require a fresh CI run and runtime validation. A passing
build is not proof of a live Railway deployment or an Android v2rayNG tunnel.
Railway remains Viewer-only in the connected account, so no Railway variables,
Volume, deployment, or public client test are claimed here.
