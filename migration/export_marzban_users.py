#!/usr/bin/env python3
"""Read-only Marzban user export for the POMP NET 3X-UI migration.

Run inside the existing Marzban container. This script NEVER writes to the
Marzban database and NEVER changes users. It exports only migration fields;
admin password hashes and other credential-like columns are excluded.
"""
from __future__ import annotations

import argparse
import datetime as dt
import decimal
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/code")

try:
    from app.db import GetDB
    from app.db.models import User
except Exception as exc:
    raise SystemExit(
        "Cannot load the installed Marzban ORM. Run this inside the current "
        f"Marzban container. Import error: {exc}"
    )

# Explicit allowlist: do not accidentally export passwords, API keys, or hashes.
SAFE_FIELDS = {
    "id", "username", "status", "expire", "data_limit", "used_traffic",
    "data_limit_reset_strategy", "ip_limit", "proxies", "inbounds", "note", "admin_id",
    "created_at", "modified_at", "online_at", "sub_updated_at",
    "subscription_url", "token", "uuid",
}
SECRET_FIELD_PARTS = ("password", "secret", "token_hash", "api_key", "private_key")


def json_value(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (dict, list)):
        return value
    if hasattr(value, "value"):
        return value.value
    return str(value)


def export_rows():
    cols = [c.name for c in User.__table__.columns]
    selected = [
        name for name in cols
        if name in SAFE_FIELDS
        and not any(part in name.lower() for part in SECRET_FIELD_PARTS)
    ]
    if not {"username"}.issubset(selected):
        raise RuntimeError("Installed User model has no username field; refusing export.")
    rows = []
    with GetDB() as db:
        for user in db.query(User).order_by(User.id).all():
            row = {}
            for name in selected:
                try:
                    row[name] = json_value(getattr(user, name))
                except Exception:
                    row[name] = None
            rows.append(row)
    return selected, rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/pompnet-marzban-users-export.json")
    args = parser.parse_args()

    fields, users = export_rows()
    payload = {
        "format": "pompnet-marzban-export-v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "Marzban ORM (read-only export)",
        "fields": fields,
        "user_count": len(users),
        "users": users,
        "migration_notes": [
            "This is an export only; it does not create or modify 3X-UI users.",
            "UUIDs are included only when the installed Marzban model exposes them.",
            "Subscription tokens are not assumed to be portable to 3X-UI.",
            "Traffic counters and expiry values require validation before import.",
            "Inbound transport/security settings must be exported separately.",
        ],
    }

    target = Path(args.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=target.name + ".", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    print(f"Exported {len(users)} users to {target}")
    print("Read-only: Marzban database was not modified.")


if __name__ == "__main__":
    main()
