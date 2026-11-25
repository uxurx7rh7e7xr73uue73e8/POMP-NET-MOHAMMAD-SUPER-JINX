#!/usr/bin/env python3
"""POMP NET native Xray manager.

Standalone control plane for Xray. It deliberately does not import Marzban modules.
Activation is opt-in until the existing users/subscription tokens have been migrated
and the old runtime can be stopped safely.
"""
import json, os, secrets, shutil, signal, sqlite3, subprocess, threading, time, uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote

DB = os.environ.get("POMPNET_CORE_DB", "/var/lib/pompnet-core/core.sqlite3")
CONFIG = os.environ.get("POMPNET_CORE_CONFIG", "/var/lib/pompnet-core/xray.json")
XRAY = os.environ.get("XRAY_EXECUTABLE_PATH") or shutil.which("xray") or "/usr/local/bin/xray"
TOKEN = os.environ.get("POMPNET_CORE_TOKEN", "")
PUBLIC_HOST = os.environ.get("POMPNET_PUBLIC_HOST", "")
PUBLIC_PORT = int(os.environ.get("POMPNET_PUBLIC_PORT", "443"))
TLS = os.environ.get("POMPNET_PUBLIC_TLS", "1") == "1"
WS_PATH = os.environ.get("POMPNET_WS_PATH", "/pompnet/ws")
LOCK = threading.RLock()
PROC = None

@contextmanager
def db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB, timeout=20)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA journal_mode=WAL")
    try:
        c.execute("""CREATE TABLE IF NOT EXISTS inbounds(
      id INTEGER PRIMARY KEY AUTOINCREMENT, tag TEXT UNIQUE NOT NULL,
      protocol TEXT NOT NULL CHECK(protocol='vless'), port INTEGER UNIQUE NOT NULL,
      network TEXT NOT NULL CHECK(network='ws'), path TEXT NOT NULL,
      enabled INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS clients(
          id TEXT PRIMARY KEY, inbound_tag TEXT NOT NULL, name TEXT NOT NULL,
          uuid TEXT UNIQUE NOT NULL, enabled INTEGER NOT NULL DEFAULT 1,
          expire_at INTEGER NOT NULL DEFAULT 0, quota_bytes INTEGER NOT NULL DEFAULT 0,
          created_at INTEGER NOT NULL, FOREIGN KEY(inbound_tag) REFERENCES inbounds(tag))""")
        c.commit()
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()

def init():
    with db() as c:
        if c.execute("SELECT COUNT(*) FROM inbounds").fetchone()[0] == 0:
            c.execute("INSERT INTO inbounds(tag,protocol,port,network,path,created_at) VALUES(?,?,?,?,?,?)",
                      ("POMP-NET-VLESS-WS", "vless", 2001, "ws", WS_PATH, int(time.time())))
            c.commit()

def build_config():
    with LOCK, db() as c:
        ins=[]
        for ib in c.execute("SELECT * FROM inbounds WHERE enabled=1 ORDER BY id"):
            clients=[{"id":x["uuid"],"email":x["name"],"level":0} for x in
                     c.execute("SELECT * FROM clients WHERE inbound_tag=? AND enabled=1 AND (expire_at=0 OR expire_at>?)",
                               (ib["tag"],int(time.time())))]
            ins.append({"tag":ib["tag"],"listen":"127.0.0.1","port":ib["port"],"protocol":"vless",
              "settings":{"clients":clients,"decryption":"none"},
              "streamSettings":{"network":"ws","security":"none","wsSettings":{"path":ib["path"]}},
              "sniffing":{"enabled":False,"destOverride":[]}})
        cfg={"log":{"loglevel":"warning"},"inbounds":ins,
             "outbounds":[{"tag":"DIRECT","protocol":"freedom"},{"tag":"BLOCK","protocol":"blackhole"}],
             "routing":{"domainStrategy":"AsIs","rules":[{"type":"field","ip":["geoip:private"],"outboundTag":"BLOCK"}]}}
        os.makedirs(os.path.dirname(CONFIG),exist_ok=True)
        tmp=CONFIG+".tmp"
        with open(tmp,"w",encoding="utf-8") as f: json.dump(cfg,f,ensure_ascii=False,indent=2)
        os.chmod(tmp,0o600); os.replace(tmp,CONFIG)
        return len(ins)

def validate():
    if not os.path.isfile(XRAY): raise RuntimeError("xray_binary_missing")
    p=subprocess.run([XRAY,"run","-test","-config",CONFIG],capture_output=True,text=True,timeout=25)
    if p.returncode: raise RuntimeError(("xray_config_rejected: "+(p.stderr or p.stdout)[-1500:]).strip())
    return True

def reload_core():
    global PROC
    build_config(); validate()
    with LOCK:
        if PROC and PROC.poll() is None:
            PROC.send_signal(signal.SIGTERM)
            try: PROC.wait(timeout=8)
            except subprocess.TimeoutExpired: PROC.kill(); PROC.wait(timeout=3)
        PROC=subprocess.Popen([XRAY,"run","-config",CONFIG],stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                              close_fds=True)

def link(row, inbound):
    if not PUBLIC_HOST: return None
    host=PUBLIC_HOST
    sec="tls" if TLS else "none"
    params=f"type=ws&security={sec}&path={quote(inbound['path'],safe='/')}&host={quote(host)}"
    label=quote("POMP NET MOHAMMAD | "+row["name"],safe="")
    return f"vless://{row['uuid']}@{host}:{PUBLIC_PORT}?{params}#{label}"

class API(BaseHTTPRequestHandler):
    server_version="POMP-NET-Core/1.0"
    def log_message(self,*a): pass
    def send(self,code,obj):
        b=json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(b))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(b)
    def auth(self):
        return bool(TOKEN) and secrets.compare_digest(self.headers.get("Authorization",""),"Bearer "+TOKEN)
    def body(self):
        n=int(self.headers.get("Content-Length","0"))
        if n<1 or n>32768: raise ValueError("invalid_body_size")
        return json.loads(self.rfile.read(n))
    def do_GET(self):
        if self.path=="/health":
            self.send(200,{"ok":True,"service":"pompnet-native-xray","process_running":bool(PROC and PROC.poll() is None)}); return
        if not self.auth(): self.send(401,{"error":"unauthorized"}); return
        with db() as c:
            if self.path=="/api/core/inbounds":
                self.send(200,{"items":[dict(x) for x in c.execute("SELECT * FROM inbounds ORDER BY id")]}); return
            if self.path=="/api/core/users":
                rows=[]
                for x in c.execute("SELECT * FROM clients ORDER BY created_at DESC"):
                    d=dict(x); ib=c.execute("SELECT * FROM inbounds WHERE tag=?",(d["inbound_tag"],)).fetchone()
                    d["link"]=link(d,dict(ib)) if ib else None
                    rows.append(d)
                self.send(200,{"items":rows}); return
        self.send(404,{"error":"not_found"})
    def do_POST(self):
        if not self.auth(): self.send(401,{"error":"unauthorized"}); return
        try: d=self.body()
        except Exception: self.send(400,{"error":"invalid_json"}); return
        try:
            with db() as c:
                if self.path=="/api/core/inbounds":
                    tag=str(d.get("tag","")).strip()
                    port=int(d.get("port",0)); path=str(d.get("path",WS_PATH))
                    if not tag or len(tag)>64 or not 1024<=port<=65535 or not path.startswith("/") or len(path)>160:
                        self.send(400,{"error":"invalid_inbound"}); return
                    c.execute("INSERT INTO inbounds(tag,protocol,port,network,path,created_at) VALUES(?,?,?,?,?,?)",
                              (tag,"vless",port,"ws",path,int(time.time())))
                    c.commit(); reload_core()
                    self.send(201,{"ok":True,"tag":tag}); return
                if self.path=="/api/core/users":
                    name=str(d.get("name","")).strip(); tag=str(d.get("inbound_tag","POMP-NET-VLESS-WS"))
                    if not name or len(name)>80: self.send(400,{"error":"invalid_name"}); return
                    ib=c.execute("SELECT * FROM inbounds WHERE tag=? AND enabled=1",(tag,)).fetchone()
                    if not ib: self.send(404,{"error":"inbound_not_found"}); return
                    uid=str(uuid.uuid4()); cid=secrets.token_hex(16); now=int(time.time())
                    exp=int(d.get("expire_at",0)); quota=int(d.get("quota_bytes",0))
                    if exp<0 or quota<0: self.send(400,{"error":"invalid_limits"}); return
                    c.execute("INSERT INTO clients VALUES(?,?,?,?,1,?,?,?)",(cid,tag,name,uid,exp,quota,now)); c.commit()
                    reload_core()
                    row=dict(c.execute("SELECT * FROM clients WHERE id=?",(cid,)).fetchone())
                    self.send(201,{"ok":True,"user":row,"link":link(row,dict(ib))}); return
        except sqlite3.IntegrityError as e: self.send(409,{"error":"duplicate_tag_or_port_or_client"}); return
        except Exception as e: self.send(500,{"error":str(e)[:500]}); return
        self.send(404,{"error":"not_found"})
    def do_DELETE(self):
        if not self.auth(): self.send(401,{"error":"unauthorized"}); return
        if not self.path.startswith("/api/core/users/"): self.send(404,{"error":"not_found"}); return
        cid=self.path.rsplit("/",1)[-1]
        with db() as c:
            cur=c.execute("DELETE FROM clients WHERE id=?",(cid,)); c.commit()
            if not cur.rowcount: self.send(404,{"error":"user_not_found"}); return
        try: reload_core()
        except Exception as e: self.send(500,{"error":str(e)[:500]}); return
        self.send(200,{"ok":True,"deleted":cid})

def main():
    if not TOKEN:
        raise SystemExit("POMPNET_CORE_TOKEN must be set; refusing unauthenticated control API")
    init()
    if os.environ.get("POMPNET_NATIVE_CORE_AUTOSTART","0")=="1": reload_core()
    host=os.environ.get("POMPNET_CORE_BIND","127.0.0.1")
    port=int(os.environ.get("POMPNET_CORE_PORT","8092"))
    print(f"[pompnet-core] control API listening on {host}:{port}; autostart={os.environ.get('POMPNET_NATIVE_CORE_AUTOSTART','0')}",flush=True)
    ThreadingHTTPServer((host,port),API).serve_forever()

if __name__=="__main__": main()
