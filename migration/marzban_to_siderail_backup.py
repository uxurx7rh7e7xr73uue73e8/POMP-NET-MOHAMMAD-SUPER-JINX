#!/usr/bin/env python3
"""Convert a read-only Marzban export into a SideRail v2 backup.

This tool NEVER contacts SideRail and NEVER mutates either database.
It refuses unsupported transports/protocols and ambiguous credentials.
An explicit inbound map is required because SideRail supports only VLESS/VMess/
Trojan over WS/XHTTP/HTTPUpgrade; it cannot represent arbitrary Marzban inbounds.
"""
from __future__ import annotations
import argparse, datetime as dt, json, os, sys, tempfile, time
from pathlib import Path

SUPPORTED_PROTOCOLS = {"vless", "vmess", "trojan"}
SUPPORTED_TRANSPORTS = {"ws", "xhttp", "httpupgrade"}

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def epoch_ms(value):
    if value in (None, 0, "", "0"):
        return None
    if isinstance(value, str) and not value.strip().isdigit():
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return int(parsed.timestamp() * 1000)
    n = int(value)
    return n * 1000 if n < 10_000_000_000 else n

def proxy_credentials(proxies):
    found = []
    if not isinstance(proxies, dict):
        raise ValueError("user_proxies_missing_or_invalid")
    for proto, conf in proxies.items():
        p = str(proto).lower()
        if p not in SUPPORTED_PROTOCOLS:
            raise ValueError("unsupported_protocol:" + p)
        if not isinstance(conf, dict):
            raise ValueError("invalid_proxy_config:" + p)
        cred = conf.get("id") or conf.get("password")
        if not cred:
            raise ValueError("missing_client_credential:" + p)
        found.append((p, str(cred)))
    if not found:
        raise ValueError("no_supported_client_credential")
    unique = {v for _, v in found}
    if len(unique) != 1:
        raise ValueError("protocol_credentials_differ; SideRail stores one UUID/password per user")
    return found[0][1]

def inbound_keys(user):
    raw = user.get("inbounds") or {}
    if not isinstance(raw, dict):
        raise ValueError("user_inbounds_invalid")
    keys = []
    for proto, names in raw.items():
        p = str(proto).lower()
        if p not in SUPPORTED_PROTOCOLS:
            if names:
                raise ValueError("unsupported_inbound_protocol:" + p)
            continue
        if isinstance(names, list):
            keys.extend(str(x) for x in names)
        elif names:
            raise ValueError("inbound_names_must_be_arrays")
    return sorted(set(keys))

def convert(source, inbound_map):
    if source.get("format") != "pompnet-marzban-export-v1":
        raise ValueError("unsupported_marzban_export_format")
    if not isinstance(source.get("users"), list):
        raise ValueError("users_array_missing")
    if not isinstance(inbound_map, dict) or not inbound_map:
        raise ValueError("inbound_map_required")
    inbounds = []
    key_to_id = {}
    for key, item in inbound_map.items():
        if not isinstance(item, dict):
            raise ValueError("invalid_inbound_mapping:" + str(key))
        proto = str(item.get("protocol", "")).lower()
        transport = str(item.get("transport", "")).lower()
        if proto not in SUPPORTED_PROTOCOLS or transport not in SUPPORTED_TRANSPORTS:
            raise ValueError("unsupported_inbound_mapping:" + str(key))
        required = ("id", "tag", "port", "path")
        if any(k not in item for k in required):
            raise ValueError("inbound_mapping_missing_fields:" + str(key))
        iid = int(item["id"])
        if iid <= 0 or iid in key_to_id.values():
            raise ValueError("duplicate_or_invalid_inbound_id")
        key_to_id[str(key)] = iid
        inbounds.append({
            "id": iid, "tag": str(item["tag"]), "protocol": proto,
            "transport": transport, "port": int(item["port"]),
            "path": str(item["path"]), "host": str(item.get("host", "")),
            "sni": str(item.get("sni", "")), "address": str(item.get("address", "")),
            "proxies": [], "enabled": 1 if item.get("enabled", True) else 0,
            "created_at": int(item.get("created_at") or time.time() * 1000)
        })
    users, links, seen_ids, seen_tokens, blockers = [], [], set(), set(), []
    for pos, row in enumerate(source["users"]):
        label = str(row.get("username") or row.get("id") or pos)
        try:
            uid = int(row.get("id") or pos + 1)
            if uid <= 0 or uid in seen_ids: raise ValueError("duplicate_or_invalid_user_id")
            seen_ids.add(uid)
            email = str(row.get("username") or "").strip()
            if not email: raise ValueError("username_missing")
            cred = proxy_credentials(row.get("proxies"))
            keys = inbound_keys(row)
            if not keys: raise ValueError("user_has_no_inbound_assignment")
            missing = [k for k in keys if k not in key_to_id]
            if missing: raise ValueError("inbound_mapping_missing:" + ",".join(missing))
            token = str(row.get("token") or row.get("subscription_url") or "").strip()
            if token.startswith("http"): token = token.rstrip("/").split("/")[-1]
            if not token: raise ValueError("subscription_token_missing")
            if token in seen_tokens: raise ValueError("duplicate_subscription_token")
            seen_tokens.add(token)
            expire = epoch_ms(row.get("expire"))
            limit = int(row.get("data_limit") or 0)
            used = int(row.get("used_traffic") or 0)
            if limit < 0 or used < 0: raise ValueError("negative_traffic_value")
            status = str(row.get("status") or "active").lower()
            enabled = status == "active" and (expire is None or expire > int(time.time()*1000))
            users.append({
                "id": uid, "email": email, "uuid": cred, "password": cred,
                "sub_token": token, "fingerprint": "chrome", "alpn": "h2,http/1.1",
                "fragment": "", "ech_config": "", "data_limit": limit,
                "ip_limit": max(0, int(row.get("ip_limit") or 0)), "expire_at": expire, "sub_expire_days": 0,
                "sub_first_seen": None, "traffic_reset": str(row.get("data_limit_reset_strategy") or "never")
                    if str(row.get("data_limit_reset_strategy") or "never") in {"never","daily","weekly","monthly"} else "never",
                "telegram_id": "", "comment": str(row.get("note") or "")[:200],
                "enabled": 1 if enabled else 0, "up": 0, "down": used,
                "last_reset": int(time.time()*1000), "online_at": None,
                "created_by": None, "created_at": epoch_ms(row.get("created_at")) or int(time.time()*1000)
            })
            links.extend({"user_id": uid, "inbound_id": key_to_id[k]} for k in keys)
        except Exception as e:
            blockers.append({"row": pos, "user_ref": label[:64], "reason": str(e)})
    if blockers:
        raise ValueError(json.dumps({"conversion_blockers": blockers}, ensure_ascii=False))
    if len({u["id"] for u in users}) != len(users) or len({u["sub_token"] for u in users}) != len(users):
        raise ValueError("duplicate_user_or_subscription_identity")
    return {
        "version": 2, "exported_at": int(time.time()*1000),
        "users": users, "user_inbounds": links, "inbounds": inbounds,
        "settings": [{"key":"sub_title","value":"POMP NET MOHAMMAD"}]
    }

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", required=True, help="Read-only export from export_marzban_users.py")
    ap.add_argument("--inbound-map", required=True, help="Reviewed JSON mapping Marzban inbound names to SideRail-supported inbound definitions")
    ap.add_argument("--output", required=True, help="Output SideRail backup JSON; not auto-imported")
    args=ap.parse_args()
    payload=convert(load_json(args.source),load_json(args.inbound_map))
    target=Path(args.output).resolve()
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=target.name+".",dir=str(target.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,target); os.chmod(target,0o600)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print(json.dumps({"ok":True,"users":len(payload["users"]),"inbounds":len(payload["inbounds"]),"links":len(payload["user_inbounds"]),"output":str(target),"live_import_performed":False},ensure_ascii=False))
if __name__=="__main__":
    try: main()
    except Exception as e:
        print(json.dumps({"ok":False,"error":str(e)},ensure_ascii=False),file=sys.stderr); raise SystemExit(2)
