# POMP NET Native Xray Core — migration gate

This module is an independent Xray control plane. It does not import Marzban code or reuse Marzban's database. It owns a separate SQLite database and an Xray JSON config, validates the exact config with `xray run -test -config`, and can start/stop its own Xray process.

## Current implementation

- SQLite persistence for VLESS/WS inbounds and clients.
- Unique inbound ports and tags enforced by SQLite.
- Actual Xray config generation from persisted records.
- Fail-closed Xray config validation before process restart.
- Process lifecycle owned by this manager (no second Xray process is started by Marzban).
- Authenticated local HTTP API for health, inbound listing/creation, user listing/creation/deletion.
- Generated VLESS URI uses the configured public hostname, TLS mode, WS path, port and POMP NET branding.
- Expiry is enforced when building the active Xray client list.

## Deliberate activation gate

The existing production entrypoint still starts Marzban. This module is **not wired into startup** by this commit. Do not set `POMPNET_NATIVE_CORE_AUTOSTART=1` in the current combined image: doing so while Marzban still owns its Xray process would create competing listeners and can break existing subscriptions.

Before cutover, implement and test:
1. Export the existing Marzban users, UUIDs, expiry, quotas, inbounds and subscription tokens from the mounted volume.
2. Import them transactionally into this manager, with an auditable mapping and rollback.
3. Complete the existing dashboard API contract (login/JWT, user detail, enable/disable, reset, quotas, traffic, QR, subscription output and role isolation).
4. Route the existing login/dashboard/subscription URLs to the new API without changing the HTML assets.
5. Run Docker build and runtime tests, then test a real external v2rayNG connection and traffic.
6. Only then switch the entrypoint and retain the old volume as rollback.

The manager intentionally supports VLESS/WS only in this first implementation. It does not claim SideRail feature parity, VMess/Trojan, traffic accounting, connected-IP telemetry, or a production cutover.
