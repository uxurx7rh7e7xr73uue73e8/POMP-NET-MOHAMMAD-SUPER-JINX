# POMP NET × SideRail integration staging

This branch pins the upstream SideRail source as a Git submodule. It does not replace the current Marzban runtime and does not migrate or modify production users, subscriptions, databases, or Xray listeners.

## Source pin

- Upstream: https://github.com/icubaby/SideRail
- Pinned upstream commit: 6d794ce2303a01ecc412941a4f38fd00a3bda65b
- Local path: vendor/SideRail
- Keep the upstream LICENSE, NOTICE, copyright headers, response headers, repository URL, and embedded watermark intact unless a verifiable written authorization from the upstream copyright holder expressly permits specific changes.

## What was verified from source

SideRail is a Node 24 application with a React/Vite frontend and Express backend. Its Dockerfile builds both workspaces and runs `apps/server/dist/index.js` on port 8080. Its server starts and manages its own Xray process, uses a separate SQLite database at `SIDERAIL_DATA_DIR/siderail.db`, and generates its own Xray config and internal listener ports.

## Safety boundary

The current POMP NET service is still built on the existing Marzban image and existing POMP NET API/database/subscription routes. SideRail uses a separate database and a separate Xray process. Starting both engines against the same listener ports or sharing their data directories would risk port collisions and data loss.

Therefore this staging branch deliberately does NOT:
- change the production Docker base image or startup command;
- start SideRail's Xray process beside the existing Xray process;
- point SideRail at Marzban's database or Xray config;
- import users or subscriptions without a tested mapping and backup;
- claim live connectivity, traffic statistics, or production readiness.

## Required cutover work

1. Build and run SideRail in an isolated staging service with a dedicated persistent volume and dedicated internal ports.
2. Confirm its health endpoint, setup/login, Xray binary download, Xray config validation, and actual VLESS client handshake.
3. Implement a read-only migration inventory for the existing Marzban users, inbounds, expiry, quota, and subscription tokens; redact credentials in logs.
4. Build and test an explicit importer with duplicate handling, rollback, and backup/restore. Do not migrate historical traffic unless a reliable mapping exists.
5. Adapt the POMP NET visual theme and Persian RTL only in permitted UI files while preserving upstream attribution and security headers.
6. Add an authenticated compatibility layer for existing POMP NET dashboard/subscription routes, then run end-to-end tests against staging.
7. Switch traffic only after successful tests and an operator-approved maintenance window. Keep the previous deployment and database backup for rollback.

## Current status

Source pin added; runtime integration, user migration, Xray handshake, production deployment, and UI re-skin are NOT yet completed or verified.
