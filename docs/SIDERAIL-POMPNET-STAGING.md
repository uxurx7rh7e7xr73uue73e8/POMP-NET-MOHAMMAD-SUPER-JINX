# POMP NET × SideRail — isolated runtime staging

## What this branch contains

- The official SideRail source is pinned as a submodule at `vendor/SideRail`.
- `siderail/Dockerfile` builds the same upstream revision directly from its immutable commit SHA, so Railway does not need to initialize Git submodules.
- `siderail/railway.json` is the Railway config for a **separate SideRail service**. Select this config file in that service's Railway settings.
- The existing POMP NET service, Marzban database, subscription routes, and Xray process are not modified by this staging deployment.

## Deploy an isolated SideRail service

Create a new Railway service from this same repository and branch. Set its Railway config file path to `siderail/railway.json`. Attach a dedicated persistent Volume at `/data`. Do not attach or reuse the current POMP NET/Marzban volume.

Required service variables:
- `PORT=8080`
- `SIDERAIL_DATA_DIR=/data`
- `CORE_DIR=/data/core`
- `CORE_VERSION=v26.9.9`
- `CORE_API_PORT=10085`
- `CORE_INBOUND_BASE_PORT=20000`
- `NODE_ENV=production`

Set a long, unique `JWT_SECRET` in Railway Variables (at least 48 random bytes encoded as hex). Do not reuse the POMP NET admin password or any Marzban secret. SideRail's first-run setup endpoint is only for initializing the isolated staging instance; complete it immediately and do not expose an uninitialized admin setup to the public.

Railway edge HTTPS terminates at the service. SideRail's own Xray listeners are separate from Marzban. Keep the two services and their volumes isolated.

## Verification gates

After Railway builds and starts the service, verify:
1. Railway deployment build succeeds.
2. `/healthz` returns HTTP 200 and includes the upstream attribution fields.
3. First-run setup and subsequent login work.
4. SideRail downloads and starts its own Xray binary.
5. Xray config validates and its internal API is reachable.
6. A real client handshake succeeds against a deliberately configured test inbound.
7. Create, update, disable, delete, expiry, quota, and subscription operations work on the staging database.
8. Restart/redeploy preserves the SideRail database and generated secrets under `/data`.

Do not call this live or working until these checks have actually passed.

## POMP NET integration boundary

The current POMP NET panel still runs its existing Marzban runtime. Do not point existing POMP NET `/sub/{token}` links at SideRail yet. SideRail has a different user schema, token format, database, authentication model, and Xray lifecycle.

The next integration change must add an authenticated server-to-server adapter and a read-only migration inventory first. It must map existing user IDs, UUIDs, expiry, quota, enabled state, inbounds, and subscription tokens with collision detection and rollback. Existing POMP NET dashboard/login/subscription routes must remain the public interface. Only after staging handshake and migration tests pass may traffic be switched.

## License and attribution

The upstream repository's LICENSE, README, author attribution, headers, signature, and watermark are retained. This integration does not remove SideRail attribution or claim authorship of upstream code.

## Current status

This commit adds a reproducible, isolated SideRail runtime build definition and Railway service configuration. It does not create a Railway service, attach a volume, deploy, migrate POMP NET users, proxy POMP NET APIs, change the production panel, or prove an Xray client handshake. Those require Railway-side service configuration and live test results.
