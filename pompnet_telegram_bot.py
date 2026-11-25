#!/usr/bin/env python3
# POMP NET MOHAMMAD — independent Telegram control bot for the Marzban/Xray panel.
# Uses the real local Marzban API; no fake subscription links or in-memory users.
import json, os, re, time, urllib.parse, urllib.request, urllib.error

CFG = "/var/lib/marzban/pompnet_bot.json"
PANEL = "http://127.0.0.1:8000"
offset = 0
token_cache = {"value": "", "until": 0}

def cfg():
    try:
        with open(CFG, encoding="utf-8") as f: c = json.load(f)
        return c if isinstance(c, dict) else {}
    except Exception: return {}

def api(url, token=None, data=None, method=None, form=False, timeout=20):
    raw = None
    headers = {}
    if data is not None:
        raw = urllib.parse.urlencode(data).encode() if form else json.dumps(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    if token: headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(PANEL + url, data=raw, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")

def panel_token():
    if token_cache["value"] and time.time() < token_cache["until"]: return token_cache["value"]
    u, p = os.getenv("ADMIN_USERNAME", ""), os.getenv("ADMIN_PASSWORD", "")
    if not u or not p: raise RuntimeError("اطلاعات ورود پنل در محیط سرویس تنظیم نشده است.")
    d = api("/api/admin/token", data={"username":u,"password":p,"grant_type":"password"}, method="POST", form=True)
    token_cache["value"], token_cache["until"] = d["access_token"], time.time()+1800
    return token_cache["value"]

def tg(token, method, data=None, timeout=35):
    raw = json.dumps(data or {}).encode()
    req = urllib.request.Request("https://api.telegram.org/bot"+token+"/"+method, data=raw,
        headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode())

def send(token, chat, text, markup=None):
    p={"chat_id":chat,"text":text,"disable_web_page_preview":True}
    if markup: p["reply_markup"]=markup
    try: tg(token,"sendMessage",p)
    except Exception as e: print("[pompnet-bot] send error:",str(e)[:180],flush=True)

def process(c, msg):
    chat=str((msg.get("chat") or {}).get("id",""))
    if chat not in set(map(str,c.get("chat_ids") or [])): return
    text=(msg.get("text") or "").strip()
    if not text: return
    token=c["token"]
    parts=text.split()
    cmd=parts[0].split("@")[0].lower()
    if cmd in ("/start","/help"):
        send(token,chat,
          "⚡ <b>POMP NET MOHAMMAD | SUPER JINX</b>\n"
          "ربات مدیریت واقعی پنل و Xray\n\n"
          "/status — وضعیت پنل\n/users — تعداد کاربران\n"
          "/new نام‌کاربر حجم‌GB روز — ساخت کاربر با VLESS/VMess/Trojan\n"
          "/get نام‌کاربر — دریافت لینک اشتراک\n"
          "/del نام‌کاربر — حذف کاربر\n\n"
          "مثال: <code>/new ali 20 30</code>",
          {"keyboard":[[{"text":"/status"},{"text":"/users"}],[{"text":"/help"}]],"resize_keyboard":True})
        return
    try:
        t=panel_token()
        if cmd=="/status":
            d=api("/api/system",t)
            send(token,chat,"✅ <b>POMP NET پنل متصل است</b>\nنسخه: "+str(d.get("version","فعال"))+"\nهسته: Xray/Marzban API")
        elif cmd=="/users":
            d=api("/api/users",t)
            us=d.get("users",[]) if isinstance(d,dict) else d
            send(token,chat,"👥 تعداد کاربران: <b>"+str(len(us) if isinstance(us,list) else "نامشخص")+"</b>")
        elif cmd=="/new":
            if len(parts)!=4: return send(token,chat,"فرمت: <code>/new username GB days</code>")
            name=parts[1]
            if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}",name): return send(token,chat,"نام کاربری نامعتبر است.")
            gb=float(parts[2]); days=int(parts[3])
            if not (0.01<=gb<=100000 and 1<=days<=3650): return send(token,chat,"حجم باید 0.01 تا 100000 گیگ و زمان 1 تا 3650 روز باشد.")
            payload={"username":name,"proxies":{"vless":{},"vmess":{},"trojan":{}},
              "inbounds":{"vless":["VLESS WS"],"vmess":["VMESS WS"],"trojan":["TROJAN WS"]},
              "expire":int(time.time())+days*86400,"data_limit":int(gb*1024**3),
              "data_limit_reset_strategy":"no_reset","status":"active"}
            d=api("/api/user",t,payload,"POST")
            sub=d.get("subscription_url","")
            if not sub: 
                try: sub=api("/api/user/"+urllib.parse.quote(name,safe=""),t).get("subscription_url","")
                except Exception: pass
            send(token,chat,"✅ کاربر در Marzban ثبت شد.\nنام: <code>"+name+"</code>\nحجم: "+str(gb)+" GB\nمدت: "+str(days)+" روز\nاشتراک: "+(sub or "ساخته شد؛ آدرس اشتراک از پنل قابل دریافت است."))
        elif cmd=="/get" and len(parts)==2:
            d=api("/api/user/"+urllib.parse.quote(parts[1],safe=""),t)
            sub=d.get("subscription_url","")
            send(token,chat,("🔗 <b>اشتراک واقعی کاربر</b>\n<code>"+sub+"</code>") if sub else "برای این کاربر لینک اشتراک برنگشت.")
        elif cmd=="/del" and len(parts)==2:
            api("/api/user/"+urllib.parse.quote(parts[1],safe=""),t,method="DELETE")
            send(token,chat,"🗑 کاربر از Marzban حذف شد: <code>"+parts[1]+"</code>")
        else: send(token,chat,"دستور ناشناخته است. /help")
    except urllib.error.HTTPError as e:
        try: detail=e.read().decode()[:350]
        except Exception: detail=str(e)
        send(token,chat,"❌ خطای پنل (HTTP "+str(e.code)+"): "+detail)
    except Exception as e:
        token_cache["until"]=0
        send(token,chat,"❌ عملیات انجام نشد: "+str(e)[:300])

def main():
    global offset
    print("[pompnet-bot] worker started; waiting for owner configuration",flush=True)
    while True:
        c=cfg()
        if not c.get("enabled") or not c.get("token") or not c.get("chat_ids"):
            time.sleep(4); continue
        try:
            updates=tg(c["token"],"getUpdates",{"offset":offset,"timeout":25,"allowed_updates":["message"]},timeout=35)
            if not updates.get("ok"): raise RuntimeError(updates.get("description","Telegram API error"))
            for u in updates.get("result",[]):
                offset=max(offset,int(u.get("update_id",0))+1)
                if u.get("message"): process(c,u["message"])
        except Exception as e:
            print("[pompnet-bot] polling error:",str(e)[:200],flush=True)
            time.sleep(5)

if __name__=="__main__": main()
