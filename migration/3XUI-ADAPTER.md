# POMP NET 3X-UI adapter module

- Pinned upstream contract: **MHSanaei/3x-ui v3.11.0**.
- Client endpoints are the v3 first-class-client routes under
  `/panel/api/clients`: list, get, add, update, delete, traffic and subscription links.
- Configure `XUI_BASE_URL` and either `XUI_API_TOKEN` or
  `XUI_USERNAME` + `XUI_PASSWORD` as server-side secrets.
- The adapter never sends credentials to browser JavaScript.

## Deliberate staging boundary

This module is an isolated transport/client layer only. It is **not** yet wired
into `start.sh`, `nginx.conf`, `jinx_api.py`, login, dashboard or
`/sub/{token}`. The production Marzban image/database remain untouched.

Before integration, add the persistent legacy-token/client mapping, normalize
the exact current dashboard response shapes, and migrate users/inbounds from a
verified export. The 3X-UI update endpoint replaces the full client row, so
partial update payloads are unsafe. Do not point this at the production volume
or deploy it as a cutover.


## Dashboard bridge deployment variables (staging only)

Required Railway service variables:
- `POMPNET_3XUI_BRIDGE=1`
- `XUI_BASE_URL`: the HTTPS origin/base URL of the 3X-UI panel (including its web base path if configured).
- `XUI_USERNAME` and `XUI_PASSWORD`: dashboard owner credentials used to validate the existing login form.
- `POMPNET_ADAPTER_SECRET`: long random secret used to sign POMP NET adapter access tokens.

Optional:
- `XUI_API_TOKEN`: use a supported 3X-UI bearer API token for API requests.
- `XUI_VLESS_INBOUND_TAG`, `XUI_VMESS_INBOUND_TAG`, `XUI_TROJAN_INBOUND_TAG`: exact existing inbound tags; defaults are the legacy JinX labels.

The staging startup now fails closed if these values are absent. It must not be deployed to the production service or its existing volume.

## Current bridge coverage and known gaps

Implemented dashboard endpoints: login token, list users, create user, delete user, and system counters. The dashboard HTML is not edited.

Not yet migrated: legacy `/sub/{token}` URL resolution and subscription rendering, per-user reset/revoke/extend actions, QR/deep links, reseller permissions and legacy Marzban-to-3X-UI data import. The existing Nginx `/sub/` route still targets the old Marzban app; therefore the overall migration is not complete and client subscriptions must not be considered cut over.


## Legacy subscription URL continuity (staging)

The public `/sub/{token}` route now passes through the compatibility bridge.
It looks up the exact old Marzban token in the persistent SQLite table
`legacy_sub_map`. If a mapping exists and `XUI_SUBSCRIPTION_BASE_URL` is
configured, it requests the corresponding 3X-UI subscription. Otherwise, or
if 3X-UI is temporarily unavailable, it proxies the original Marzban
`/sub/{token}` response unchanged. The `/info` suffix and query string are
preserved. This is a compatibility/fallback route, not proof of cutover.

Set `XUI_SUBSCRIPTION_BASE_URL` to the externally reachable 3X-UI subscription
endpoint prefix, including its configured path (for example, an HTTPS URL
ending in `/sub`; include the subscription server port only if that port is
actually reachable over HTTPS). Do not assume the panel's API origin is also
the subscription origin. Keep the old Marzban service and its Volume available
until every migrated token has been checked from a client device.

## User import procedure

1. Run `migration/export_marzban_users.py` inside the old Marzban container.
   It is read-only and exports the old `token`, username, UUID/proxy data,
   quota, expiry and status when those columns exist.
2. Determine the actual 3X-UI inbound IDs for each supported protocol.
3. Run `migration/import_marzban_to_3xui.py` with the export, inbound map,
   `XUI_BASE_URL`, `XUI_API_TOKEN` and the same persistent
   `POMPNET_SUB_MAP_DB` path used by the bridge. Dry-run is the default;
   review the full preflight report before adding `--apply`.
4. The importer preserves the old subscription token as 3X-UI `subId` and
   writes the token-to-subId map only after each client is accepted by 3X-UI.
   It refuses conflicting/missing UUIDs, missing inbound mappings and
   conflicting existing clients. It never deletes or edits the old Marzban
   records.
5. Historical `used_traffic` is not written by the 3X-UI client-add API and
   is explicitly NOT migrated by this importer. The import report calls this
   out; do not represent the old usage counter as preserved. Unsupported
   protocols are not silently converted.

The current export/import scripts have not been run against the live Railway
Volume or a real 3X-UI instance. A successful dry-run, apply, subscription
fetch, and v2rayNG connection test are still required before cutover.
