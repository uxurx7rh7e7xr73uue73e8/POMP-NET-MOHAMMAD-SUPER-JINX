#!/usr/bin/env python3
"""Fail-closed preflight for the exact Xray config that Marzban will load.

This does not start a second Xray process. Marzban remains the sole owner of
its bundled Xray process; this script validates the generated config first.
"""
import json
import os
import shutil
import subprocess
import sys

CONFIG = os.environ.get("XRAY_JSON", "/var/lib/marzban/xray_config.json")
CANDIDATES = [
    os.environ.get("XRAY_EXECUTABLE_PATH", ""),
    shutil.which("xray") or "",
    "/usr/local/bin/xray",
    "/usr/bin/xray",
]
XRAY = next((p for p in CANDIDATES if p and os.path.isfile(p) and os.access(p, os.X_OK)), None)


def fail(message: str, code: int = 1) -> None:
    print(f"[xray-preflight] FATAL: {message}", file=sys.stderr, flush=True)
    raise SystemExit(code)


def main() -> None:
    if not XRAY:
        fail("Xray executable not found; refusing to start with unverified VPN links.")
    if not os.path.isfile(CONFIG):
        fail(f"config file not found: {CONFIG}")

    try:
        with open(CONFIG, encoding="utf-8") as handle:
            config = json.load(handle)
    except Exception as exc:
        fail(f"config JSON is unreadable: {exc}")

    inbounds = config.get("inbounds")
    if not isinstance(inbounds, list) or not inbounds:
        fail("config has no inbounds.")
    ports = []
    tags = set()
    for index, inbound in enumerate(inbounds):
        if not isinstance(inbound, dict):
            fail(f"inbound #{index + 1} is not an object.")
        tag = str(inbound.get("tag") or "")
        if not tag or tag in tags:
            fail(f"inbound #{index + 1} has a missing or duplicate tag.")
        tags.add(tag)
        try:
            port = int(inbound.get("port"))
        except (TypeError, ValueError):
            fail(f"inbound {tag!r} has no valid port.")
        if not 1 <= port <= 65535:
            fail(f"inbound {tag!r} has an out-of-range port.")
        if port in ports:
            fail(f"duplicate inbound port {port}; refusing ambiguous listeners.")
        ports.append(port)

    version = subprocess.run(
        [XRAY, "version"], capture_output=True, text=True, timeout=15
    )
    if version.returncode != 0:
        fail("Xray version command failed: " + (version.stderr or version.stdout)[-1200:])
    print("[xray-preflight] " + (version.stdout.strip().splitlines()[0] if version.stdout.strip() else "Xray version available"), flush=True)

    check = subprocess.run(
        [XRAY, "run", "-test", "-config", CONFIG],
        capture_output=True, text=True, timeout=30
    )
    if check.returncode != 0:
        detail = (check.stderr or check.stdout or "Xray rejected the configuration").strip()
        fail("Xray rejected the generated config: " + detail[-2400:])
    print(
        f"[xray-preflight] OK: Xray accepted {len(inbounds)} inbound(s); "
        f"ports={','.join(map(str, ports))}. Marzban will start the managed core.",
        flush=True,
    )


if __name__ == "__main__":
    main()
