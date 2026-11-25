# Marzban → SideRail migration preparation

This is a **conversion and validation tool**, not a live migration. It does not connect to Railway, SideRail, Marzban, or Xray and does not change either database.

## Why an inbound map is mandatory

The pinned SideRail engine model supports only VLESS, VMess and Trojan over WS, XHTTP and HTTPUpgrade. Marzban deployments may use Reality, gRPC, TCP, Shadowsocks, Hysteria, TUIC, or other settings that SideRail's current data model cannot represent. The converter rejects unsupported transports/protocols instead of silently generating broken links.

Create a reviewed mapping file only after inspecting the actual Marzban Xray configuration. Example:

```json
{
  "vless-ws": {
    "id": 1,
    "tag": "VLESS-WS",
    "protocol": "vless",
    "transport": "ws",
    "port": 20000,
    "path": "/actual-ws-path",
    "host": "your-domain.example",
    "sni": "your-domain.example",
    "address": "your-domain.example",
    "enabled": true
  }
}
```

The key (`vless-ws` above) must exactly match the inbound name stored in each user's Marzban `inbounds` field. Ports, path, host, SNI, TLS termination and transport must be copied from the real deployed configuration; never use the example values as production settings.

## Read-only export from the existing Marzban container

```bash
python3 /path/to/migration/export_marzban_users.py --output /tmp/marzban-export.json
```

Copy that export and the reviewed mapping file to a protected staging workspace. The export contains UUIDs and subscription tokens, so protect it as a secret: chmod 600, do not commit it to GitHub, and delete temporary copies after verified migration.

## Convert to SideRail backup format

```bash
python3 migration/marzban_to_siderail_backup.py \
  --source /secure/marzban-export.json \
  --inbound-map /secure/inbound-map.json \
  --output /secure/siderail-import.json
```

The converter preserves supported user IDs, credentials, subscription token values, expiry, data limit, current used traffic, compatible IP limits, enabled/disabled state, notes, and inbound assignments. Once imported, the POMP NET `/sub/{token}` compatibility gateway tries SideRail first for imported tokens and falls back to Marzban on a SideRail 404; thus old token URLs remain unchanged for supported migrated users. Current used traffic is represented as download usage because the Marzban export field is a combined counter; upload/download split and online/IP history cannot be reconstructed from that export. Admin accounts/password hashes are intentionally not migrated.

It rejects duplicate IDs/tokens, missing mappings, unsupported protocols/transports and differing per-protocol credentials because SideRail stores one client credential per user.

## Critical import warning

SideRail's upstream `POST /api/backup/import` implementation deletes the target SideRail database's existing `user_inbounds`, `users`, and `inbounds` before inserting the backup, inside a transaction. It can also replace admin records if admins are included. Therefore:
- Use a brand-new, empty SideRail staging volume for the first import.
- Do not import into a SideRail instance containing valuable users.
- Never mount the old Marzban volume into SideRail.
- Keep Marzban online and untouched until real client tests and rollback are complete.
- This converter omits admin data, so the SideRail first-run owner remains in place.
- Do not call the import endpoint automatically from this script.

## Current limitations

This conversion cannot be called production-ready until the live Marzban export and actual Xray inbound configuration have been inspected. In particular, SideRail's supported protocol/transport matrix is narrower than a typical Marzban deployment. Unsupported Reality/gRPC/TCP or non-supported protocols need a separately implemented and tested SideRail core/model extension, or those clients must remain on the existing engine.

The Railway project cannot currently be provisioned by the connected account while the Railway trial is expired; no separate `/data` volume is live. No SideRail API import, live Xray handshake, subscription fetch, or production cutover is claimed.
