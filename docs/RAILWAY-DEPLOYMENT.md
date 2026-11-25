# POMP NET MOHAMMAD — Railway deployment checklist

This document describes the **current code in this branch**. It does not claim that a Railway deployment or a v2rayNG connection has already been tested.

## Current core and storage path

The Docker image in this repository is currently based on `gozargah/marzban:latest`, not PasarGuard. Its SQLite database and Xray configuration are configured at:

- `/var/lib/marzban/db.sqlite3`
- `/var/lib/marzban/xray_config.json`

Therefore the Railway Volume for **this branch** must be mounted at **`/var/lib/marzban`**. Mounting it at `/var/lib/pasarguard` would not persist this branch's database or Xray config. Do not change the mount path on an existing live service without a verified backup and migration. A true PasarGuard conversion is a separate migration and is not completed by this deployment checklist.

## Railway service settings

1. Connect this GitHub repository and select branch `pompnet-pasarguard-core-migration`.
2. Keep the Dockerfile builder. `railway.json` configures Dockerfile build, `/health` healthcheck, a 300-second timeout and ON_FAILURE restart.
3. In the service's **Volumes** settings, create/attach one persistent volume with mount path **`/var/lib/marzban`**. If an existing volume contains data, back it up first; do not wipe or replace it.
4. In **Networking → Public Networking**, generate/use an HTTPS domain and set the target port to **8080**. Nginx listens on 8080 in the container; Uvicorn's internal upstream listens on 8000. The domain target port is not 8000.
5. Railway terminates public HTTPS on port **443**. The subscription URL on Railway should use the HTTPS hostname without appending `:2096`. Port 2096 is not exposed by this single-service Railway setup.

## Required service variables

Set these in Railway's Variables UI as secrets/variables; never commit plaintext credentials:

- `ADMIN_USERNAME=ADMIN_tanel9990`
- `ADMIN_PASSWORD` = a strong owner-selected password (at least 14 characters)
- `PORT=8080`

For a **brand-new empty volume**, set `ADMIN_PASSWORD` before the first deploy. Startup intentionally fails closed if there is no initialized owner and no password secret.

For an **existing initialized database**, the current owner password hash is preserved. Merely setting `ADMIN_PASSWORD` does not reset it. To deliberately reset it, set `RESET_ADMIN_PASSWORD=1` for exactly one deployment while `ADMIN_PASSWORD` is set, then remove `RESET_ADMIN_PASSWORD` immediately after the successful deploy. Never use this reset flag casually.

Do not set `RESET_ADMIN_PASSWORD` on an existing production volume unless the owner explicitly intends a password reset.

## Domain and subscriptions

- Set `PANEL_DOMAIN` to the actual public hostname only if it is assigned to the service; otherwise allow Railway-provided public hostname detection.
- Railway public HTTPS is 443 → container target 8080.
- The panel subscription route is `/sub/<token>` on that HTTPS hostname.
- Do not advertise a `:2096` subscription endpoint on Railway unless a separate supported ingress is explicitly configured and verified.

## Verification required after deployment

A successful image build is not proof that Xray is reachable from the public internet. Before declaring the service production-ready, verify:

1. Railway deployment reaches **SUCCESS** and `GET /health` returns HTTP 200.
2. Logs confirm the volume is mounted/writable at `/var/lib/marzban`; startup must not report that no volume is attached.
3. Owner login works using the configured secret, without exposing the password in logs.
4. Create a disposable test user with VLESS, VMess and Trojan enabled. Fetch its real `/sub/<token>` URL and confirm all expected links are present.
5. Import each generated link/subscription into v2rayNG on an external Android network and test handshake, traffic upload/download and ping. A WebSocket HTTP 101 check alone is not proof of a working VPN tunnel.
6. Delete the disposable test user after verification.

The repository's `tests/runtime-smoke.sh` exercises the local Docker image, user creation, subscription output, WebSocket handshakes and persistence. It does not replace the external Railway + Android v2rayNG test.

## Current status

This branch now contains Railway's Docker/healthcheck config and this deployment checklist. The actual Railway Volume, domain target-port setting, owner secret, deployment and external v2rayNG test still require access to the Railway service and a real deployment. No live connectivity is claimed until those checks pass.
