#!/usr/bin/env python3
"""Independent POMP NET Xray engine for Railway.

This service owns a separate Xray process and SQLite registry. It does not
modify Marzban's database/configuration. Public transports are TLS WebSocket
through Railway HTTPS ingress; raw TCP/UDP protocols are deliberately absent.
"""
import base64, json, os, re, secrets, shutil, signal, sqlite3, subprocess, threading, time, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DATA = os.environ.get("POMPNET_ENGINE_DATA", "/var/lib/marzban/pompnet-engine")
DB = os.path.join(DATA, "engine.sqlite3")
CFG = os.path.join(DATA, "xray-engine.json")
PID = os.path.join(DATA, "xray-engine.pid")
HOST = "127.0.0.1"
PORT = int(os.environ.get("POMPNET_ENGINE_PORT", "8092"))
BASE_PATH = "/pompnet"
INBOUNDS = {
    "vless": {"tag": "POMP-VLESS-WS", "port": 21001, "path": BASE_PATH + "/vless"},
    "vmess": {"tag": "POMP-VMESS-WS", "port": 21002, "path": BASE_PATH + "/vmess"},
    "trojan": {"tag": "POMP-TROJAN-WS", "port": 21003, "path": BASE_PATH + "/trojan"},
}
LOCK = threading.RLock()
PROC = None
STOP = False

def db():
    os.makedirs(DATA, mode=0o700, exist_ok=True)
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("""CREATE TABLE IF NOT EXISTS users(
      id TEXT PRIMARY KEY, username TEXT NOT NULL, protocol TEXT NOT NULL,
      secret TEXT NOT NULL, sub_token TEXT NOT NULL, expire INTEGER NOT NULL DEFAULT 0,
      data_limit_gb REAL NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1,
      created INTEGER NOT NULL, UNIQUE(username, protocol))""")
    c.commit()
    return c

def xray_bin():
    p = os.environ.get("XRAY_EXECUTABLE_PATH") or shutil.which("xray")
    if not p or not os.path.isfile(p):
        raise RuntimeError("Xray executable not found in image")
    return p

def active_users(c):
    now = int(time.time())
    return c.execute("SELECT * FROM users WHERE enabled=1 AND (expire=0 OR expire>?)", (now,)).fetchall()

def make_config(c):
    ins = []
    rows = active_users(c)
    for proto, meta in INBOUNDS.items():
        clients = []
        for u in rows:
            if u["protocol"] != proto: continue
            if proto == "vless":
                clients.append({"id": u["secret"], "email": u["username"], "level": 0})
            elif proto == "vmess":
                clients.append({"id": u["secret"], "alterId": 0, "email": u["username"], "level": 0})
            else:
                clients.append({"password": u["secret"], "email": u["username"], "level": 0})
        settings = {"clients": clients}
        if proto == "vless": settings["decryption"] = "none"
        if proto == "trojan": settings["fallbacks"] = []
        ins.append({
            "tag": meta["tag"], "listen": HOST, "port": meta["port"], "protocol": proto,
            "settings": settings,
            "streamSettings": {"network": "ws", "security": "none",
              "wsSettings": {"path": meta["path"], "heartbeatPeriod": 30}},
            "sniffing": {"enabled": False, "destOverride": []}
        })
    return {
      "log": {"loglevel": "warning"},
      "inbounds": ins,
      "outbounds": [{"protocol":"freedom","tag":"DIRECT"},{"protocol":"blackhole","tag":"BLOCK"}],
      "policy": {"levels":{"0":{"handshake":10,"connIdle":300,"uplinkOnly":2,"downlinkOnly":5}}}
    }

def restart_engine():
    global PROC
    with LOCK:
        c = db()
        cfg = make_config(c)
        c.close()
        # Xray selects the parser from the file extension; keep .json as the final suffix.
        tmp = CFG + ".tmp.json"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, separators=(",", ":"))
            f.flush(); os.fsync(f.fileno())
        exe = xray_bin()
        test = subprocess.run([exe, "run", "-test", "-config", tmp], capture_output=True, text=True, timeout=25)
        if test.returncode:
            try: os.unlink(tmp)
            except OSError: pass
            raise RuntimeError("Xray config validation failed: " + (test.stderr or test.stdout)[-1200:])
        os.replace(tmp, CFG)
        if PROC and PROC.poll() is None:
            PROC.terminate()
            try: PROC.wait(timeout=8)
            except subprocess.TimeoutExpired: PROC.kill(); PROC.wait(timeout=3)
        PROC = subprocess.Popen([exe, "run", "-config", CFG], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                start_new_session=True)
        time.sleep(0.7)
        if PROC.poll() is not None:
            raise RuntimeError("Xray process exited during startup")
        with open(PID, "w") as f: f.write(str(PROC.pid))
        print("[pompnet-engine] independent Xray process running; inbounds=3", flush=True)

def admin_ok(token):
    if not token: return False
    try:
        req = Request("http://127.0.0.1:8000/api/admin", headers={"Authorization":"Bearer "+token})
        with urlopen(req, timeout=5) as r: a = json.loads(r.read())
        return bool(a.get("is_sudo"))
    except Exception:
        return False

def host_for(handler):
    h = handler.headers.get("X-Forwarded-Host") or handler.headers.get("Host") or ""
    h = h.split(",")[0].strip().split(":")[0].lower()
    if not re.fullmatch(r"[a-z0-9.-]{4,253}", h): return ""
    return h

def links_for(row, host):
    if not host: return []
    m = INBOUNDS[row["protocol"]]
    path = quote(m["path"], safe="/")
    common = f"type=ws&security=tls&host={host}&path={quote(path, safe='')}&sni={host}#POMP-NET-{quote(row['username'])}"
    if row["protocol"] == "vless":
        return [f"vless://{row['secret']}@{host}:443?{common}"]
    if row["protocol"] == "trojan":
        return [f"trojan://{row['secret']}@{host}:443?{common}"]
    obj = {"v":"2","ps":"POMP-NET-"+row["username"],"add":host,"port":"443","id":row["secret"],
           "aid":"0","net":"ws","type":"none","host":host,"path":m["path"],"tls":"tls","sni":host}
    return ["vmess://"+base64.b64encode(json.dumps(obj,separators=(",",":")).encode()).decode()]

class Handler(BaseHTTPRequestHandler):
    server_version = "POMP-NET-Engine/1.0"
    def log_message(self, *_): pass
    def send(self, code, obj, ctype="application/json; charset=utf-8"):
        b = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length",str(len(b)))
        self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(b)
    def body(self):
        n = min(int(self.headers.get("Content-Length","0")), 32768)
        return json.loads(self.rfile.read(n) or b"{}")
    def token(self):
        h = self.headers.get("Authorization","")
        return h[7:].strip() if h.lower().startswith("bearer ") else ""
    def do_GET(self):
        p = urlsplit(self.path).path
        if p == "/health":
            ok = bool(PROC and PROC.poll() is None)
            return self.send(200 if ok else 503, {"ok":ok,"engine":"xray-independent","pid":PROC.pid if ok else None})
        if p.startswith("/sub/"):
            tok = p.rsplit("/",1)[-1]
            c=db(); rows=c.execute("SELECT * FROM users WHERE sub_token=? AND enabled=1 AND (expire=0 OR expire>?)",(tok,int(time.time()))).fetchall(); c.close()
            if not rows: return self.send(404,b"not found","text/plain")
            lines=[link for row in rows for link in links_for(row,host_for(self))]
            if not lines: return self.send(400,b"host unavailable","text/plain")
            raw=base64.b64encode(("\n".join(lines)+"\n").encode())
            return self.send(200,raw,"text/plain; charset=utf-8")
        if not admin_ok(self.token()): return self.send(401,{"detail":"مالک پنل لازم است"})
        if p == "/api/users":
            c=db(); rows=c.execute("SELECT username,MIN(id) AS id,MIN(expire) AS expire,MIN(data_limit_gb) AS data_limit_gb,MAX(enabled) AS enabled,MIN(created) AS created,MIN(sub_token) AS sub_token,GROUP_CONCAT(protocol) AS protocols FROM users GROUP BY username ORDER BY created DESC").fetchall(); c.close()
            host=host_for(self); result=[]
            for r in rows:
                d=dict(r); d["protocols"]=d["protocols"].split(",") if d["protocols"] else []
                d["status"]="active" if d["enabled"] and (not d["expire"] or d["expire"]>int(time.time())) else "disabled"
                d["used_traffic"]=0; d["data_limit"]=int(float(d["data_limit_gb"] or 0)*1024**3)
                d["subscription_url"]=("https://"+host+"/pompnet-sub/"+d.pop("sub_token")) if host else None
                result.append(d)
            return self.send(200,{"users":result,"count":len(result)})
        if p == "/api/inbounds":
            return self.send(200,[{"protocol":k,"tag":v["tag"],"remark":"POMP NET "+k.upper()+" WS","transport":"ws","security":"tls-at-railway-edge","port":443,"path":v["path"],"id":v["port"],"enable":True} for k,v in INBOUNDS.items()])
        if p == "/api/system":
            return self.send(200,{"engine":"independent-xray","running":bool(PROC and PROC.poll() is None),"pid":PROC.pid if PROC else None,"protocols":list(INBOUNDS),"traffic_accounting":False,"quota_enforcement":False})
        if p == "/api/diagnostics":
            c=db(); count=c.execute("SELECT COUNT(DISTINCT username) FROM users").fetchone()[0]; mappings=c.execute("SELECT COUNT(DISTINCT sub_token) FROM users").fetchone()[0]; c.close()
            return self.send(200,{"client_count":count,"inbound_count":len(INBOUNDS),"subscription_mappings":mappings,"checks":{"independent_xray_running":bool(PROC and PROC.poll() is None),"persistent_sqlite":os.path.exists(DB),"railway_websocket_edge":True,"traffic_stats":False},"configured_inbound_tags":{k:{"found":True,"tag":v["tag"]} for k,v in INBOUNDS.items()}})
        return self.send(404,{"detail":"not found"})
    def do_POST(self):
        p=urlsplit(self.path).path
        if not admin_ok(self.token()): return self.send(401,{"detail":"مالک پنل لازم است"})
        if p == "/api/users":
            try:
                b=self.body(); name=str(b.get("username","")).strip()
                protocols=b.get("protocols") or ([b.get("protocol","vless")] if b.get("protocol") else list((b.get("proxies") or {}).keys()))
                protocols=list(dict.fromkeys(str(x).lower() for x in protocols if str(x).lower() in INBOUNDS))
                if not re.fullmatch(r"[A-Za-z0-9_.-]{2,48}",name): return self.send(400,{"detail":"نام کاربر نامعتبر است"})
                if not protocols: return self.send(400,{"detail":"select at least one of vless, vmess, trojan"})
                exp=int(b.get("expire",0) or 0); limit=float(b.get("data_limit_gb",0) or 0)
                if exp<0 or limit<0 or limit>100000: return self.send(400,{"detail":"expiry/quota invalid"})
                sub=secrets.token_urlsafe(32); created=[]; c=db()
                try:
                    for proto in protocols:
                        uid=str(uuid.uuid4()); secret=str(uuid.uuid4()) if proto!="trojan" else secrets.token_urlsafe(24)
                        c.execute("INSERT INTO users(id,username,protocol,secret,sub_token,expire,data_limit_gb,enabled,created) VALUES(?,?,?,?,?,?,?,?,?)",
                                  (uid,name,proto,secret,sub,exp,limit,1,int(time.time())))
                        created.append({"id":uid,"username":name,"protocol":proto,"secret":secret,"sub_token":sub})
                    c.commit()
                except sqlite3.IntegrityError:
                    c.rollback(); c.close(); return self.send(409,{"detail":"username already exists for one or more selected protocols"})
                c.close(); restart_engine()
                links=[link for row in created for link in links_for(row,host_for(self))]
                return self.send(201,{"ok":True,"username":name,"protocols":protocols,"links":links,
                  "subscription_url":("https://"+host_for(self)+"/pompnet-sub/"+sub) if host_for(self) else None,
                  "note":"data_limit_gb is stored as metadata only; live traffic accounting/quota enforcement is not enabled"})
            except Exception as e: return self.send(500,{"detail":str(e)[:800]})
        if p == "/api/inbounds":
            b=self.body(); proto=str(b.get("protocol","")).lower()
            if proto not in INBOUNDS: return self.send(400,{"detail":"unsupported protocol"})
            v=INBOUNDS[proto]
            return self.send(200,{"ok":True,"protocol":proto,"remark":"POMP NET "+proto.upper()+" WS","port":443,"path":v["path"],"message":"این Listener از قبل در هسته مستقل فعال است."})
        if p.startswith("/api/users/") and p.endswith("/toggle"):
            uid=p.split("/")[-2]; c=db(); r=c.execute("SELECT enabled FROM users WHERE id=?",(uid,)).fetchone()
            if not r: c.close(); return self.send(404,{"detail":"user not found"})
            c.execute("UPDATE users SET enabled=? WHERE id=?",(0 if r["enabled"] else 1,uid)); c.commit(); c.close()
            try: restart_engine()
            except Exception as e: return self.send(500,{"detail":str(e)[:800]})
            return self.send(200,{"ok":True,"enabled":not bool(r["enabled"])})
        return self.send(404,{"detail":"not found"})
    def do_DELETE(self):
        p=urlsplit(self.path).path
        if not admin_ok(self.token()): return self.send(401,{"detail":"مالک پنل لازم است"})
        if p.startswith("/api/users/"):
            uid=unquote(p.rsplit("/",1)[-1]); c=db()
            cur=c.execute("DELETE FROM users WHERE id=? OR username=?",(uid,uid)); c.commit(); c.close()
            if not cur.rowcount: return self.send(404,{"detail":"user not found"})
            try: restart_engine()
            except Exception as e: return self.send(500,{"detail":str(e)[:800]})
            return self.send(200,{"ok":True,"deleted":uid})
        return self.send(404,{"detail":"not found"})

def expiry_loop():
    while not STOP:
        try:
            c=db(); now=int(time.time())
            cur=c.execute("UPDATE users SET enabled=0 WHERE enabled=1 AND expire>0 AND expire<=?",(now,))
            c.commit(); c.close()
            if cur.rowcount: restart_engine(); print("[pompnet-engine] expired users disabled",flush=True)
        except Exception as e: print("[pompnet-engine] expiry error:",str(e)[:300],flush=True)
        time.sleep(30)

def main():
    global STOP
    os.makedirs(DATA,mode=0o700,exist_ok=True)
    db().close()
    restart_engine()
    threading.Thread(target=expiry_loop,daemon=True).start()
    srv=ThreadingHTTPServer(("127.0.0.1",PORT),Handler)
    print(f"[pompnet-engine] API listening on 127.0.0.1:{PORT}",flush=True)
    try: srv.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt: pass
    finally:
        STOP=True; srv.server_close()
        if PROC and PROC.poll() is None: PROC.terminate()

if __name__=="__main__": main()
