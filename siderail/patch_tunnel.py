from pathlib import Path

p = Path("apps/server/src/tunnel.ts")
s = p.read_text(encoding="utf-8")

anchor = 'const xhttpProxy = httpProxy.createProxyServer({ ws: false, xfwd: true });\nxhttpProxy.on("error", () => {});'
replacement = '''const xhttpProxy = httpProxy.createProxyServer({ ws: false, xfwd: true });
xhttpProxy.on("error", () => {});

// Route WebSocket upgrades with the maintained http-proxy WS implementation.
const wsProxy = httpProxy.createProxyServer({ ws: true, xfwd: true });
wsProxy.on("error", (...args: any[]) => {
  const socket = args[2];
  if (socket && typeof socket.destroy === "function") socket.destroy();
});
wsProxy.on("proxyReqWs", (proxyReq: any, req: IncomingMessage) => {
  const realIp = clientIp(req);
  proxyReq.on("socket", (upstreamSocket: any) => {
    const save = () => {
      if (realIp && upstreamSocket.localPort) {
        portToIp.set(upstreamSocket.localPort, { ip: realIp, ts: Date.now() });
      }
    };
    if (upstreamSocket.connecting) upstreamSocket.once("connect", save);
    else save();
  });
});'''
if anchor not in s:
    raise SystemExit("WebSocket proxy insertion anchor not found")
s = s.replace(anchor, replacement, 1)

old = '    pipeToCore(req, socket as Socket, head, inbound);'
new = '''    wsProxy.ws(req, socket as Socket, head, {
      target: `http://127.0.0.1:${inbound.port}`,
    });'''
if old not in s:
    raise SystemExit("attachTunnel relay anchor not found")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
