#!/usr/bin/env python3
"""Read-only pre-migration audit for a Marzban SQLite database.

This tool never changes the source database and never prints usernames, UUIDs,
subscription tokens, passwords, or other per-user identifying values.
"""
import argparse
import json
import os
import sqlite3
import sys

USER_TABLE_CANDIDATES = ("users", "user")
INBOUND_TABLE_CANDIDATES = ("inbounds", "inbound")
SENSITIVE = {"username", "uuid", "token", "sub_token", "password", "secret", "proxies", "inbounds"}

def table_names(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]

def columns(conn, table):
    return [r[1] for r in conn.execute('PRAGMA table_info("' + table.replace('"', '""') + '")')]

def choose(names, candidates):
    return next((name for name in candidates if name in names), None)

def audit(path):
    if not os.path.isfile(path):
        raise FileNotFoundError("database_file_not_found")
    uri = "file:" + os.path.abspath(path).replace("?", "%3f") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        integrity = [r[0] for r in conn.execute("PRAGMA quick_check")]
        fk_errors = [dict(r) for r in conn.execute("PRAGMA foreign_key_check")]
        names = table_names(conn)
        user_table = choose(names, USER_TABLE_CANDIDATES)
        inbound_table = choose(names, INBOUND_TABLE_CANDIDATES)
        result = {
            "database": os.path.basename(path),
            "read_only": True,
            "integrity_check": integrity,
            "foreign_key_violations": len(fk_errors),
            "tables": {},
            "migration_readiness": {
                "users_table_found": bool(user_table),
                "inbounds_table_found": bool(inbound_table),
                "ready_for_mapping_review": False,
                "blockers": []
            }
        }
        for name in names:
            cols = columns(conn, name)
            count = conn.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
            result["tables"][name] = {"row_count": count, "columns": cols}
        if not user_table:
            result["migration_readiness"]["blockers"].append("users_table_not_found")
        if not inbound_table:
            result["migration_readiness"]["blockers"].append("inbounds_table_not_found")
        if user_table:
            cols = set(columns(conn, user_table))
            required_groups = {
                "stable_user_identity": {"username", "id"},
                "protocol_credentials": {"proxies"},
                "subscription_identity": {"token", "sub_token"}
            }
            for label, alternatives in required_groups.items():
                if not (cols & alternatives):
                    result["migration_readiness"]["blockers"].append(label + "_column_not_found")
            result["users"] = {
                "table": user_table,
                "total": conn.execute('SELECT COUNT(*) FROM "' + user_table + '"').fetchone()[0],
                "columns_present": sorted(cols),
                "sensitive_values_exported": False
            }
            # Only aggregate counts are emitted. Never return individual records.
            for col in ("status", "enabled"):
                if col in cols:
                    result["users"][col + "_distribution"] = {
                        str(r[0]): r[1] for r in conn.execute(
                            'SELECT "' + col + '", COUNT(*) FROM "' + user_table + '" GROUP BY "' + col + '"'
                        )
                    }
        if inbound_table:
            result["inbounds"] = {
                "table": inbound_table,
                "total": conn.execute('SELECT COUNT(*) FROM "' + inbound_table + '"').fetchone()[0],
                "columns_present": columns(conn, inbound_table)
            }
        if integrity != ["ok"]:
            result["migration_readiness"]["blockers"].append("sqlite_integrity_check_failed")
        if fk_errors:
            result["migration_readiness"]["blockers"].append("foreign_key_violations_present")
        result["migration_readiness"]["ready_for_mapping_review"] = not result["migration_readiness"]["blockers"]
        return result
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Path to the existing Marzban SQLite database")
    parser.add_argument("--output", help="Optional JSON report path; report contains schema and aggregate counts only")
    args = parser.parse_args()
    report = audit(args.db)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(rendered + "\n")
        os.chmod(args.output, 0o600)
    print(rendered)
    return 0 if report["migration_readiness"]["ready_for_mapping_review"] else 2

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
