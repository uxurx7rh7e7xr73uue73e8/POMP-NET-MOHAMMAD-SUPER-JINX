from pathlib import Path

p = Path("apps/server/src/tunnel.ts")
s = p.read_text(encoding="utf-8")

anchor = 'const xhttpProxy = httpProxy.createProxyServer({ ws: false, xfwd: true });\nxhttpProxy.on("error", () => {});'
replacement = '''const xhttpProxy = httpProxy.createProxyServer({ ws: false, xfwd: true });
xhttpProxy.on("error", () => {});'''
if anchor not in s:
    raise SystemExit("WebSocket proxy insertion anchor not found")
s = s.replace(anchor, replacement, 1)

old = '    pipeToCore(req, socket as Socket, head, inbound);'
new = '    pipeToCore(req, socket as Socket, head, inbound);'
if old not in s:
    raise SystemExit("attachTunnel relay anchor not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")


# In CI only, allow the isolated TCP echo destination on the container's own
# interface. Xray v26.9+ intentionally blocks private/reserved destinations
# by default for VLESS-originated traffic. Keep production defaults locked down.
core = Path("apps/server/src/core-settings.ts")
cs = core.read_text(encoding="utf-8")
if 'import os from "node:os";' not in cs:
    cs = cs.replace('import { config } from "./config.js";', 'import os from "node:os";\nimport { config } from "./config.js";', 1)
helper = '''
function directOutboundSettings(): Record<string, unknown> {
  const settings: Record<string, unknown> = {};
  if (process.env.POMP_NET_E2E_PRIVATE_ECHO !== "1") return settings;
  const address = Object.values(os.networkInterfaces())
    .flat()
    .find((entry) => entry && entry.family === "IPv4" && !entry.internal)?.address;
  if (address) {
    settings.finalRules = [
      { action: "allow", network: "tcp", port: "18090", ip: [`${address}/32`] },
    ];
  }
  return settings;
}

'''
if "function directOutboundSettings()" not in cs:
    marker = "function streamSettings(inbound: Inbound) {"
    if marker not in cs:
        raise SystemExit("core-settings helper insertion anchor not found")
    cs = cs.replace(marker, helper + marker, 1)
old_direct = '{ tag: "direct", protocol: "freedom", settings: {} },'
new_direct = '{ tag: "direct", protocol: "freedom", settings: directOutboundSettings() },'
if old_direct in cs:
    cs = cs.replace(old_direct, new_direct, 1)
elif new_direct not in cs:
    raise SystemExit("direct freedom outbound anchor not found")
core.write_text(cs, encoding="utf-8")
