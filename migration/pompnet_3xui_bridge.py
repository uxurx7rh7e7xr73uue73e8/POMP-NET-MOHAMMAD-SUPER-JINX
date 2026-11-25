"""POMP NET compatibility bridge for MHSanaei 3X-UI v3.11.0.

Staging-only HTTP adapter for the existing dashboard's core endpoints.
No legacy database is modified. Existing /sub tokens are mapped through a
separate persistent SQLite table; unmapped links retain the Marzban fallback.
"""
import base64, hashlib, hmac, http.cookiejar, json, os, re, secrets, sqlite3, threading, time
import urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = os.getenv("XUI_BASE_URL", "").rstrip("/")
USER = os.getenv("XUI_USERNAME", "")
PASSWORD = os.getenv("XUI_PASSWORD", "")
API_TOKEN = os.getenv("XUI_API_TOKEN", "")
SECRET = os.getenv("POMPNET_ADAPTER_SECRET", "")
PORT = int(os.getenv("POMPNET_3XUI_BRIDGE_PORT", "8091"))
SUB_MAP_DB = os.getenv("POMPNET_SUB_MAP_DB", "/var/lib/marzban/pompnet-sub-map.sqlite3")
XUI_SUBSCRIPTION_BASE_URL = os.getenv("XUI_SUBSCRIPTION_BASE_URL", "").rstrip("/") or (BASE + "/sub" if BASE else "")
INBOUND_TAGS = {
    "vless": os.getenv("XUI_VLESS_INBOUND_TAG", "VLESS WS"),
    "vmess": os.getenv("XUI_VMESS_INBOUND_TAG", "VMESS WS"),
    "trojan": os.getenv("XUI_TROJAN_INBOUND_TAG", "TROJAN WS"),
}
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
csrf = ""
lock = threading.RLock()

class BridgeError(Exception): pass

def request(method, path, payload=None, form=False):
    global csrf
    if not BASE:
        raise BridgeError("XUI_BASE_URL is not configured")
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        if form:
            data = urllib.parse.urlencode(payload).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(payload, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
    if API_TOKEN:
        headers["Authorization"] = "Bearer " + API_TOKEN
    elif csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=18) as res:
            raw = res.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise BridgeError("3X-UI HTTP %s: %s" % (e.code, e.read().decode("utf-8","replace")[:240]))
    except Exception as e:
        raise BridgeError("3X-UI connection failed: " + str(e)[:180])
    try: result = json.loads(raw) if raw else {}
    except Exception: raise BridgeError("3X-UI returned invalid JSON")
    if isinstance(result, dict) and result.get("success") is False:
        raise BridgeError(str(result.get("msg") or "3X-UI API rejected request"))
    return result.get("obj", result) if isinstance(result, dict) else result

def login_xui(username, password):
    global csrf
    # Always authenticate the dashboard owner, even when the upstream API token is configured.
    if not USER or not PASSWORD or not hmac.compare_digest(username, USER) or not hmac.compare_digest(password, PASSWORD):
        raise BridgeError("نام کاربری یا رمز عبور نادرست است")
    # A configured API token authenticates upstream 3X-UI calls after owner login.
    if API_TOKEN:
        return
    with lock:
        try:
            c = request("GET", "/panel/csrf-token")
            if isinstance(c, dict): csrf = str(c.get("token") or c.get("csrfToken") or "")
        except BridgeError:
            csrf = ""
        # 3X-UI login endpoint accepts form-encoded credentials.
        request("POST", "/login", {"username": USER, "password": PASSWORD}, form=True)
        try:
            c = request("GET", "/panel/csrf-token")
            if isinstance(c, dict): csrf = str(c.get("token") or c.get("csrfToken") or "")
        except BridgeError:
            pass

def token_make(username):
    payload = json.dumps({"u": username, "exp": int(time.time()) + 12*3600}, separators=(",",":")).encode()
    body = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    sig = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    return body + "." + sig

def token_check(header):
    if not SECRET: raise BridgeError("POMPNET_ADAPTER_SECRET is not configured")
    if not header.startswith("Bearer "): raise BridgeError("login_required")
    try:
        body, sig = header[7:].split(".", 1)
        expected = hmac.new(SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected): raise ValueError()
        data = json.loads(base64.urlsafe_b64decode(body + "="*((4-len(body)%4)%4)))
        if int(data["exp"]) < time.time(): raise ValueError()
        return data["u"]
    except Exception: raise BridgeError("invalid_or_expired_token")

def obj(response):
    return response.get("obj", response) if isinstance(response, dict) else response

def inbound_index():
    rows = obj(request("GET", "/panel/api/inbounds/list"))
    if not isinstance(rows, list): raise BridgeError("3X-UI inbound list is not an array")
    index = {str(x.get("tag") or x.get("remark") or ("inbound-"+str(x.get("id")))): x for x in rows if isinstance(x, dict)}
    # Backward-compatible aliases for the existing dashboard protocol selectors.
    for proto, alias in (("vless","VLESS WS"),("vmess","VMESS WS"),("trojan","TROJAN WS")):
        matches = [x for x in rows if isinstance(x,dict) and str(x.get("protocol","")).lower()==proto and x.get("enable",True)]
        if alias not in index and len(matches)==1:
            index[alias] = matches[0]
    return index

def normalize(client, inbound_map):
    traffic = client.get("traffic") or {}
    up, down = int(traffic.get("up", 0) or 0), int(traffic.get("down", 0) or 0)
    total = int(client.get("totalGB", 0) or 0)
    expiry_ms = int(client.get("expiryTime", 0) or 0)
    proto_map = {}
    for iid in client.get("inboundIds", []) or []:
        for inbound in inbound_map.values():
            if int(inbound.get("id", -1)) == int(iid):
                proto = str(inbound.get("protocol", "")).lower()
                if proto in ("vless","vmess","trojan"):
                    proto_map.setdefault(proto, []).append(str(inbound.get("tag") or inbound.get("remark") or ""))
    proxies = {}
    inbounds = {}
    for proto, tags in proto_map.items():
        proxies[proto] = {}
        inbounds[proto] = tags
    return {
        "username": client.get("email", ""),
        "status": "active" if client.get("enable", True) else "disabled",
        "used_traffic": up + down,
        "data_limit": total or None,
        "expire": int(expiry_ms/1000) if expiry_ms else None,
        "online_at": None,
        "proxies": proxies,
        "inbounds": inbounds,
        "sub_url": ("/sub/" + str(client.get("subId"))) if client.get("subId") else None,
        "admin": {"is_sudo": False},
    }

def json_body(handler, limit=65536):
    n = int(handler.headers.get("Content-Length") or 0)
    if n < 1 or n > limit: raise BridgeError("invalid_request_body")
    data = json.loads(handler.rfile.read(n).decode("utf-8"))
    if not isinstance(data, dict): raise BridgeError("invalid_request_body")
    return data

def map_db():
    os.makedirs(os.path.dirname(SUB_MAP_DB) or '.', exist_ok=True)
    db = sqlite3.connect(SUB_MAP_DB, timeout=15)
    db.execute('CREATE TABLE IF NOT EXISTS legacy_sub_map (legacy_token TEXT PRIMARY KEY, xui_sub_id TEXT NOT NULL UNIQUE, username TEXT NOT NULL, migrated_at INTEGER NOT NULL)')
    db.commit()
    return db

def lookup_sub_id(legacy_token):
    db = map_db()
    try:
        row = db.execute('SELECT xui_sub_id FROM legacy_sub_map WHERE legacy_token=?', (legacy_token,)).fetchone()
        return row[0] if row else None
    finally:
        db.close()

def register_subscription(username, sub_id):
    """Create a stable legacy /sub token that proxies to this real 3X-UI subId."""
    if not sub_id:
        raise BridgeError("3X-UI client was created without a subscription ID; configure the 3X-UI subscription service")
    legacy_token = secrets.token_urlsafe(32)
    db = map_db()
    try:
        db.execute(
            'INSERT INTO legacy_sub_map (legacy_token,xui_sub_id,username,migrated_at) VALUES (?,?,?,?)',
            (legacy_token, str(sub_id), str(username), int(time.time()))
        )
        db.commit()
    except sqlite3.IntegrityError as exc:
        raise BridgeError("subscription_id_already_mapped; refusing to overwrite another user's mapping") from exc
    finally:
        db.close()
    return legacy_token

def subscription_response(handler, legacy_token, suffix=''):
    sub_id = lookup_sub_id(legacy_token)
    parsed = urllib.parse.urlsplit(handler.path)
    if sub_id and XUI_SUBSCRIPTION_BASE_URL:
        target = XUI_SUBSCRIPTION_BASE_URL + '/' + urllib.parse.quote(sub_id, safe='') + suffix
        if parsed.query: target += '?' + parsed.query
        try:
            headers = {'User-Agent': handler.headers.get('User-Agent', 'POMP-NET'),
                       'X-Forwarded-Proto': 'https',
                       'X-Forwarded-Host': handler.headers.get('Host', '')}
            if handler.headers.get('Accept'): headers['Accept'] = handler.headers.get('Accept')
            if API_TOKEN: headers['Authorization'] = 'Bearer ' + API_TOKEN
            with urllib.request.urlopen(urllib.request.Request(target, headers=headers), timeout=25) as res:
                body = res.read(); handler.send_response(res.status)
                for name in ('Content-Type','Content-Disposition','Subscription-Userinfo','Profile-Update-Interval','Profile-Title','Cache-Control','ETag','Last-Modified'):
                    value = res.headers.get(name)
                    if value: handler.send_header(name, value)
                handler.send_header('Content-Length', str(len(body))); handler.end_headers(); handler.wfile.write(body); return
        except Exception as exc:
            print('[3xui-bridge] 3X-UI subscription failed; using legacy fallback: ' + str(exc)[:160], flush=True)
    # Preserve unmigrated and temporarily unreachable subscriptions via the original Marzban service.
    legacy_path = '/sub/' + urllib.parse.quote(legacy_token, safe='') + suffix
    if parsed.query: legacy_path += '?' + parsed.query
    try:
        req = urllib.request.Request('http://127.0.0.1:8000' + legacy_path, headers={
            'User-Agent': handler.headers.get('User-Agent', 'POMP-NET'),
            'Host': handler.headers.get('Host', 'localhost'),
            'X-Forwarded-Proto': 'https',
            'X-Forwarded-For': handler.headers.get('X-Forwarded-For', ''),
            'X-Real-IP': handler.headers.get('X-Real-IP', '')
        })
        with urllib.request.urlopen(req, timeout=25) as res:
            body = res.read(); handler.send_response(res.status)
            for name in ('Content-Type','Content-Disposition','Subscription-Userinfo','Profile-Update-Interval','Profile-Title','Cache-Control','ETag','Last-Modified'):
                value = res.headers.get(name)
                if value: handler.send_header(name, value)
            handler.send_header('Content-Length', str(len(body))); handler.end_headers(); handler.wfile.write(body)
    except urllib.error.HTTPError as exc:
        body = exc.read(); handler.send_response(exc.code); handler.send_header('Content-Type', exc.headers.get('Content-Type','text/plain; charset=utf-8')); handler.send_header('Content-Length', str(len(body))); handler.end_headers(); handler.wfile.write(body)
    except Exception as exc:
        handler.sendj(502, {'detail':'subscription service unavailable','reason':str(exc)[:160]})

class Handler(BaseHTTPRequestHandler):
    server_version = "POMP-NET-3XUI-Bridge/1.0"
    def sendj(self, status, data):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(raw)))
        self.end_headers(); self.wfile.write(raw)
    def log_message(self, fmt, *args):
        print("[3xui-bridge] " + (fmt % args), flush=True)
    def do_POST(self):
        try:
            if self.path == "/api/admin/token":
                if not SECRET: raise BridgeError("POMPNET_ADAPTER_SECRET is not configured")
                ctype = self.headers.get("Content-Type","")
                if "application/x-www-form-urlencoded" in ctype:
                    raw = int(self.headers.get("Content-Length") or 0)
                    form = urllib.parse.parse_qs(self.rfile.read(min(raw,8192)).decode())
                    username = form.get("username",[""])[0]; password = form.get("password",[""])[0]
                else:
                    body = json_body(self,8192); username=body.get("username",""); password=body.get("password","")
                login_xui(str(username), str(password))
                return self.sendj(200, {"access_token":token_make(str(username)), "token_type":"bearer"})
            if self.path == "/api/user":
                token_check(self.headers.get("Authorization",""))
                body = json_body(self)
                username = str(body.get("username","")).strip()
                if not re.fullmatch(r"[A-Za-z0-9_.@-]{2,64}", username): raise BridgeError("invalid_username")
                requested = body.get("inbounds") or {}
                tags = sorted({str(t) for values in requested.values() if isinstance(values,list) for t in values})
                if not tags: raise BridgeError("select_at_least_one_inbound")
                imap = inbound_index()
                ids=[]
                for tag in tags:
                    inbound=imap.get(tag)
                    if not inbound: raise BridgeError("inbound_not_found: "+tag)
                    proto=str(inbound.get("protocol","")).lower()
                    if proto not in ("vless","vmess","trojan"): raise BridgeError("unsupported_protocol: "+proto)
                    ids.append(int(inbound["id"]))
                expiry=int(body.get("expire") or 0)*1000
                quota=int(body.get("data_limit") or 0)
                client={"email":username,"totalGB":quota,"expiryTime":expiry,"enable":True,"tgId":0,"limitIp":0,"limitHwid":0}
                created=obj(request("POST","/panel/api/clients/add",{"client":client,"inboundIds":ids}))
                return self.sendj(200, {"username":username,"status":"active","result":created})
            if self.path == "/api/inbounds":
                token_check(self.headers.get("Authorization",""))
                body=json_body(self,16384)
                proto=str(body.get("protocol","")).lower()
                if proto not in ("vless","vmess","trojan"): raise BridgeError("unsupported_protocol")
                try: port=int(body.get("port"))
                except Exception: raise BridgeError("invalid_port")
                if port < 1024 or port > 65535: raise BridgeError("port_must_be_1024_to_65535")
                remark=str(body.get("remark") or "").strip()
                if not remark or len(remark)>64 or not re.fullmatch(r"[A-Za-z0-9 _.-]+",remark): raise BridgeError("invalid_inbound_name")
                path=str(body.get("path") or ("/pompnet/"+proto)).strip()
                if not path.startswith("/") or len(path)>96 or any(c in path for c in (" ","?","#")): raise BridgeError("invalid_ws_path")
                rows=obj(request("GET","/panel/api/inbounds/list"))
                if not isinstance(rows,list): raise BridgeError("cannot_read_existing_inbounds")
                if any(int(x.get("port",0) or 0)==port for x in rows if isinstance(x,dict)): raise BridgeError("port_already_in_use")
                settings={"clients":[]}
                if proto=="vless": settings.update({"decryption":"none","fallbacks":[]})
                stream={"network":"ws","security":"none","wsSettings":{"path":path,"headers":{}}}
                sniff={"enabled":True,"destOverride":["http","tls","quic"],"metadataOnly":False,"routeOnly":False}
                form={"up":"0","down":"0","total":"0","remark":remark,"enable":"true","expiryTime":"0","listen":"","port":str(port),"protocol":proto,"settings":json.dumps(settings,separators=(",",":")),"streamSettings":json.dumps(stream,separators=(",",":")),"sniffing":json.dumps(sniff,separators=(",",":"))}
                result=obj(request("POST","/panel/api/inbounds/add",form,form=True))
                return self.sendj(201,{"created":True,"remark":remark,"protocol":proto,"port":port,"network":"ws","security":"none","path":path,"result":result,"note":"WebSocket بدون TLS ساخته شد؛ برای استفاده عمومی باید TLS در reverse proxy یا تنظیمات معتبر سرور فعال شود."})
            raise BridgeError("not_found")
        except BridgeError as e:
            msg=str(e); status=401 if "login" in msg or "رمز" in msg or "token" in msg else 400
            self.sendj(status,{"detail":msg})
        except Exception as e: self.sendj(400,{"detail":str(e)[:300]})
    def do_GET(self):
        try:
            if self.path == "/health": return self.sendj(200,{"ok":True,"engine":"3x-ui-v3.11.0"})
            sub_match = re.fullmatch(r"/sub/([A-Za-z0-9_-]{8,128})(/info)?", urllib.parse.urlsplit(self.path).path)
            if sub_match: return subscription_response(self, sub_match.group(1), sub_match.group(2) or "")
            token_check(self.headers.get("Authorization",""))
            if self.path == "/api/users":
                imap=inbound_index()
                rows=obj(request("GET","/panel/api/clients/list"))
                return self.sendj(200,[normalize(x,imap) for x in (rows or [])])
            if self.path == "/api/system":
                imap=inbound_index()
                rows=obj(request("GET","/panel/api/clients/list")) or []
                return self.sendj(200,{"engine":"3X-UI v3.11.0","inbounds":len(imap),"total_users":len(rows),"active_users":sum(1 for x in rows if x.get("enable")),"online_users":None,"traffic_up":sum(int((x.get("traffic") or {}).get("up",0) or 0) for x in rows),"traffic_down":sum(int((x.get("traffic") or {}).get("down",0) or 0) for x in rows)})
            if self.path == "/api/diagnostics":
                checks={"XUI_BASE_URL":bool(BASE),"POMPNET_ADAPTER_SECRET":bool(SECRET),"XUI_AUTH":bool(API_TOKEN or (USER and PASSWORD)),"XUI_SUBSCRIPTION_BASE_URL":bool(XUI_SUBSCRIPTION_BASE_URL),"POMPNET_SUB_MAP_DB":bool(SUB_MAP_DB)}
                imap=inbound_index()
                rows=obj(request("GET","/panel/api/clients/list")) or []
                protocols={}
                for x in imap.values():
                    p=str(x.get("protocol","")).lower()
                    protocols[p]=protocols.get(p,0)+1
                configured_tags={p:{"tag":tag,"found":tag in imap} for p,tag in INBOUND_TAGS.items()}
                db=map_db()
                try: mapped=db.execute("SELECT COUNT(*) FROM legacy_sub_map").fetchone()[0]
                finally: db.close()
                return self.sendj(200,{"ok":True,"engine":"3X-UI v3.11.0","api_reachable":True,"client_count":len(rows),"inbound_count":len(imap),"protocol_counts":protocols,"configured_inbound_tags":configured_tags,"subscription_mappings":mapped,"checks":checks})
            raise BridgeError("not_found")
        except BridgeError as e:
            msg=str(e); self.sendj(401 if "token" in msg or "login" in msg else 502,{"detail":msg})
        except Exception as e: self.sendj(502,{"detail":str(e)[:300]})
    def do_DELETE(self):
        try:
            token_check(self.headers.get("Authorization",""))
            m=re.fullmatch(r"/api/user/([^/]+)",urllib.parse.urlsplit(self.path).path)
            if not m: raise BridgeError("not_found")
            email=urllib.parse.unquote(m.group(1))
            result=obj(request("POST","/panel/api/clients/del/"+urllib.parse.quote(email,safe="")))
            return self.sendj(200,{"detail":"User deleted","result":result})
        except BridgeError as e: self.sendj(401 if "token" in str(e) else 502,{"detail":str(e)})
        except Exception as e: self.sendj(502,{"detail":str(e)[:300]})

if __name__ == "__main__":
    if os.getenv("POMPNET_3XUI_BRIDGE","0") == "1":
        if not BASE or not SECRET or (not USER or not PASSWORD):
            raise SystemExit("[3xui-bridge] FATAL: set XUI_BASE_URL, POMPNET_ADAPTER_SECRET and XUI_API_TOKEN or XUI_USERNAME/XUI_PASSWORD")
        map_db().close()
        print("[3xui-bridge] staging compatibility API listening on 127.0.0.1:%d" % PORT, flush=True)
        ThreadingHTTPServer(("127.0.0.1",PORT),Handler).serve_forever()
    else:
        print("[3xui-bridge] disabled; set POMPNET_3XUI_BRIDGE=1 to enable",flush=True)
