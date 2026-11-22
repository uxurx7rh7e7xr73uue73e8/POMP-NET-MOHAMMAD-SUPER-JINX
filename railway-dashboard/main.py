import os, sqlite3, secrets, hmac, html, uuid
from datetime import datetime, timezone, date
from contextlib import contextmanager
from urllib.parse import urljoin
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

TITLE = 'POMP NET MOHAMMAD — SUPER JINX'
USER = os.getenv('ADMIN_USERNAME', '')
PASSWORD = os.getenv('ADMIN_PASSWORD', '')
SECRET = os.getenv('SESSION_SECRET', '')
DATA = os.getenv('DATA_DIR', '/data')
DB = os.path.join(DATA, 'super_jinx.sqlite3')
if len(USER) < 3 or len(PASSWORD) < 14 or len(SECRET) < 32:
    raise RuntimeError('Set ADMIN_USERNAME (3+), ADMIN_PASSWORD (14+), SESSION_SECRET (32+ chars).')
os.makedirs(DATA, exist_ok=True)
app = FastAPI(title=TITLE)
app.add_middleware(SessionMiddleware, secret_key=SECRET, same_site='lax', https_only=True, max_age=3600)

@contextmanager
def database():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()

with database() as con:
    con.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        quota_gb REAL NOT NULL DEFAULT 0,
        expires TEXT,
        note TEXT NOT NULL DEFAULT "",
        status TEXT NOT NULL DEFAULT "active",
        public_id TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )''')

def render(body, title='داشبورد', code=200):
    page = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#080711">
<title>SUPER JINX | """ + html.escape(title) + """</title><style>
:root{color-scheme:dark;--bg:#080711;--panel:#151321;--line:#3a2858;--purple:#8b35ff;--blue:#168cff;--text:#f6f2ff;--muted:#aaa2bd}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 85% 0%,#28134b 0,transparent 38%),var(--bg);color:var(--text);font-family:Vazirmatn,Tahoma,Arial,sans-serif;min-height:100vh}
main{max-width:1180px;margin:28px auto;padding:16px}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}.brand{font-size:13px;color:#bca0ff;letter-spacing:1px}.hero{font-size:clamp(24px,5vw,38px);margin:7px 0;color:#fff}.tag{color:var(--muted);font-size:13px}
.card{background:linear-gradient(145deg,#191525,#11101b);border:1px solid #8b35ff55;border-radius:19px;padding:20px;margin:15px 0;box-shadow:0 12px 36px #0006}
h2{color:#d6bcff;margin:0 0 15px;font-size:19px}.muted{color:var(--muted)}.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.stat{padding:16px;border:1px solid #ffffff13;border-radius:14px;background:#0d0b16}.stat b{display:block;font-size:26px;color:#fff;margin-top:5px}
input,button{font:inherit;padding:11px 13px;border-radius:10px;border:1px solid #51465f;background:#0e0c17;color:#fff;margin:4px;max-width:100%}input:focus{outline:1px solid var(--blue)}button{background:linear-gradient(110deg,#6222b2,#245eb6);border:0;cursor:pointer}button.danger{background:#702a43}button.secondary{background:#30263f;border:1px solid #51465f}a{color:#8dbbff;text-decoration:none}.row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:850px}td,th{padding:12px 9px;border-bottom:1px solid #383344;text-align:right;white-space:nowrap}th{color:#bca0ff;font-weight:600}.pill{display:inline-block;padding:4px 9px;border-radius:30px;background:#163d32;color:#8ff0c5;font-size:12px}.pill.off{background:#492132;color:#ff9fbd}.actions form{display:inline}.actions input{width:135px}.search{display:flex;gap:6px;flex-wrap:wrap}.search input{flex:1;min-width:150px}.foot{margin:22px 0;color:#8e879e;font-size:12px}.suburl{font-size:11px;max-width:220px;overflow-wrap:anywhere;color:#9bc7ff}
@media(max-width:620px){main{margin:8px auto;padding:10px}.card{padding:14px}.stats{grid-template-columns:1fr}.hero{font-size:25px}}

/* SUPER JINX independent SideRail-inspired visual refresh */
:root{--bg:#090812;--panel:#11101b;--line:#373044;--purple:#8b35ff;--blue:#168cff;--text:#f6f2ff;--muted:#aaa2bd}
body{background:radial-gradient(ellipse at 75% -10%,#30135b 0,transparent 34%),linear-gradient(135deg,#090812,#0c0a15 60%,#080711)}
.shell{min-height:100vh;display:grid;grid-template-columns:250px minmax(0,1fr);direction:rtl}
.sidebar{position:sticky;top:0;height:100vh;padding:24px 17px;background:#0d0b15;border-left:3px solid #282033;display:flex;flex-direction:column;gap:22px}
.sidebrand{padding:16px 13px;border:2px solid #8b35ff;border-radius:12px;background:#171126;box-shadow:5px 5px 0 #4c2780}
.sidebrand strong{display:block;font-size:15px;letter-spacing:.4px}.sidebrand small{display:block;color:#b9a6d7;margin-top:7px}
.side-label{font-size:10px;color:#80768f;font-weight:800;letter-spacing:1.5px;padding:0 10px}
.sidenav{display:grid;gap:9px}.sidenav a{display:flex;align-items:center;gap:11px;padding:12px 13px;border:2px solid transparent;border-radius:10px;color:#d9d1e8;font-weight:700;font-size:13px;transition:.18s}
.sidenav a:hover,.sidenav a.active{background:#211633;border-color:#8b35ff;color:#fff;box-shadow:4px 4px 0 #43256b;transform:translate(-2px,-2px)}
.side-icon{width:27px;height:27px;display:grid;place-items:center;border:1px solid #58416e;border-radius:8px;background:#171121;color:#a77aff}
.side-bottom{margin-top:auto;border:1px solid #352941;border-radius:11px;padding:13px;color:#a99bbd;font-size:11px;line-height:1.9}
.workspace{min-width:0;padding:28px clamp(12px,3vw,36px);max-width:1500px;width:100%;margin:0 auto}
.top{padding:17px 21px;border:2px solid #3c3150;border-radius:13px;background:#12101c;box-shadow:6px 6px 0 #241936;margin-bottom:23px}
.brand{font-size:11px;font-weight:800;letter-spacing:2px;color:#b991ff}.hero{font-size:clamp(24px,4vw,34px);margin:5px 0}.tag{font-size:12px}
.stats{margin:18px 0}.stat,.card{border:2px solid #383044;border-radius:13px;box-shadow:5px 5px 0 #21182e;background:linear-gradient(145deg,#171321,#100e18)}
.stat{position:relative;overflow:hidden}.stat:before{content:"";position:absolute;inset:0 auto 0 0;width:4px;background:linear-gradient(#8b35ff,#168cff)}
.stat b{font-size:29px;color:#fff}
.card{padding:21px;margin:20px 0}.card h2{font-weight:800;color:#d9c5ff}
button{border-radius:8px;box-shadow:3px 3px 0 #291b3b;font-weight:800;transition:transform .15s,box-shadow .15s}
button:hover{transform:translate(-1px,-1px);box-shadow:5px 5px 0 #291b3b}
input{border-radius:8px;border:2px solid #40364d}
table{border-collapse:separate;border-spacing:0 5px;min-width:850px}
td,th{border-bottom:1px solid #30283b;background:#151220}th{background:#211831;color:#c9a9ff}
td:first-child,th:first-child{border-radius:0 8px 8px 0}td:last-child,th:last-child{border-radius:8px 0 0 8px}
.pill{border:1px solid #2c8d68}.pill.off{border-color:#8a3c59}
.foot{border-top:1px solid #30283b;padding-top:15px}
@media(max-width:850px){.shell{grid-template-columns:1fr}.sidebar{position:relative;height:auto;padding:12px 14px;border-left:0;border-bottom:2px solid #282033;gap:12px}.sidebrand{padding:10px 13px}.sidenav{grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.sidenav a{padding:9px;font-size:12px}.side-bottom{display:none}.workspace{padding:14px 10px}}
@media(max-width:520px){.sidenav{grid-template-columns:repeat(2,minmax(0,1fr))}.workspace{padding:10px 8px}.top{padding:14px}.card{padding:14px}.stats{grid-template-columns:1fr}.stat{padding:14px}}
</style></head><body><div class="shell"><aside class="sidebar"><div class="sidebrand"><strong>POMP NET MOHAMMAD</strong><small>SUPER JINX · CONTROL CENTER</small></div><div class="side-label">منوی مدیریت</div><nav class="sidenav"><a class="active" href="/"><span class="side-icon">⌂</span>داشبورد اصلی</a><a href="/#accounts"><span class="side-icon">▤</span>مدیریت حساب‌ها</a><a href="/#create"><span class="side-icon">＋</span>ایجاد حساب</a><a href="/#subscription-info"><span class="side-icon">↗</span>اطلاعات اشتراک</a><a href="/logout"><span class="side-icon">⇥</span>خروج امن</a></nav><div class="side-bottom">به پنل پمپ نت محمد خوش آمدید<br>قدرت ساخت، آزادی انتخاب، کنترل در دستان تو</div></aside><main class="workspace"><header class="top"><div><div class="brand">POMP NET MOHAMMAD</div><h1 class="hero">SUPER JINX</h1><div class="tag">به پنل پمپ نت محمد خوش آمدید</div></div></header>""" + body + '<footer class="foot">قدرت ساخت، آزادی انتخاب، کنترل در دستان تو</footer></main></div></body></html>'
    return HTMLResponse(page, status_code=code)

def authenticated(request):
    return request.session.get('admin') is True

def subscription_state(row):
    if row['status'] != 'active':
        return 'تعلیق‌شده', False
    exp = row['expires']
    if exp:
        try:
            if date.fromisoformat(exp) < date.today():
                return 'منقضی‌شده', False
        except ValueError:
            return 'تاریخ نامعتبر', False
    return 'فعال', True

@app.get('/health')
def health():
    return {'status':'ok','service':'SUPER JINX management dashboard','mode':'management-only','subscription_info_pages':True}

@app.get('/login')
def login_page():
    return render('<section class="card"><h2>ورود مدیر</h2><form method="post" action="/login"><input name="username" autocomplete="username" placeholder="نام کاربری" required><br><input name="password" type="password" autocomplete="current-password" placeholder="رمز عبور" required><br><button>ورود امن</button></form></section>', 'ورود')

@app.post('/login')
async def login(request: Request):
    form = await request.form()
    u, p = str(form.get('username','')), str(form.get('password',''))
    if hmac.compare_digest(u, USER) and hmac.compare_digest(p, PASSWORD):
        request.session.clear()
        request.session['admin'] = True
        return RedirectResponse('/', status_code=303)
    return render('<section class="card"><h2>ورود ناموفق</h2>نام کاربری یا رمز نادرست است. <a href="/login">تلاش دوباره</a></section>', 'خطا', 401)

@app.get('/')
def dashboard(request: Request):
    if not authenticated(request): return RedirectResponse('/login', status_code=303)
    query = request.query_params.get('q','').strip()[:64]
    with database() as con:
        total = con.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]
        active = con.execute("SELECT COUNT(*) FROM accounts WHERE status='active'").fetchone()[0]
        suspended = total - active
        if query:
            rows = con.execute('SELECT * FROM accounts WHERE username LIKE ? OR note LIKE ? ORDER BY id DESC', (f'%{query}%',f'%{query}%')).fetchall()
        else:
            rows = con.execute('SELECT * FROM accounts ORDER BY id DESC').fetchall()
    table_rows = []
    for r in rows:
        state, is_active = subscription_state(r)
        status = '<span class="pill">فعال</span>' if is_active else '<span class="pill off">{}</span>'.format(html.escape(state))
        sub_url = urljoin(str(request.base_url), 'sub/' + r['public_id'])
        table_rows.append(
            '<tr><td>{}</td><td><b>{}</b><br><small class="muted">{}</small></td><td>{} GB</td><td>{}</td><td>{}</td><td><a class="suburl" href="{}" target="_blank" rel="noopener">مشاهده صفحه ساب ↗</a><br><button class="secondary" type="button" onclick="navigator.clipboard.writeText(\'{}\')">کپی لینک</button></td><td class="actions">'
            '<form method="post" action="/accounts/{}/renew"><input name="expires" type="date" required aria-label="تاریخ تمدید"><button class="secondary">تمدید</button></form>'
            '<form method="post" action="/accounts/{}/toggle"><button class="secondary">تغییر وضعیت</button></form>'
            '<form method="post" action="/accounts/{}/delete" onsubmit="return confirm(\'حذف این رکورد؟\')"><button class="danger">حذف</button></form></td></tr>'.format(
                r['id'], html.escape(r['username']), html.escape(r['note'] or 'بدون یادداشت'),
                r['quota_gb'], html.escape(r['expires'] or 'بدون انقضا'), status,
                html.escape(sub_url, quote=True), html.escape(sub_url, quote=True), r['id'], r['id'], r['id'])
        )
    body = '<section class="stats" id="overview"><div class="stat"><span class="muted">کل حساب‌ها</span><b>{}</b></div><div class="stat"><span class="muted">فعال</span><b>{}</b></div><div class="stat"><span class="muted">تعلیق‌شده</span><b>{}</b></div></section>'.format(total,active,suspended)
    body += '<section class="card" id="create"><div class="row" style="justify-content:space-between"><h2>مدیریت حساب‌ها و ساب</h2><a href="/logout">خروج از پنل ↗</a></div><p class="muted">برای هر حساب یک شناسه اشتراک خصوصی و صفحه اطلاعات عمومی ساخته می‌شود.</p><form method="post" action="/accounts" class="row"><input name="username" placeholder="نام کاربری" required maxlength="64"><input name="quota" type="number" min="0" step="0.1" placeholder="حجم ثبت‌شده GB" required><input name="expires" type="date"><input name="note" placeholder="یادداشت مدیر"><button>＋ ایجاد حساب و ساب</button></form></section>'
    body += '<section class="card" id="accounts"><div class="row" style="justify-content:space-between"><h2>فهرست حساب‌ها</h2><span class="muted">نمایش {} مورد</span></div><form class="search" method="get"><input name="q" value="{}" placeholder="جست‌وجوی نام یا یادداشت"><button>جست‌وجو</button><a class="row" href="/">پاک‌کردن</a></form><div class="tablewrap"><table><tr><th>#</th><th>حساب</th><th>حجم ثبت‌شده</th><th>انقضا</th><th>وضعیت</th><th>صفحه اشتراک</th><th>عملیات</th></tr>{}</table></div></section>'.format(len(rows),html.escape(query),''.join(table_rows) or '<tr><td colspan="7" class="muted">رکوردی پیدا نشد.</td></tr>')
    body += '<section class="card" id="subscription-info"><h2>درباره بخش اشتراک</h2><p class="muted">این بخش صفحه اطلاعات اشتراک، شناسه خصوصی، وضعیت، حجم ثبت‌شده و تاریخ انقضا را مدیریت می‌کند. حجم در این نسخه صرفاً مقدار ثبت‌شده است و مصرف شبکه را اندازه‌گیری یا محدود نمی‌کند؛ این لینک کانفیگ VPN یا لینک اتصال مرزبان نیست.</p><p class="muted">پایگاه داده SQLite · ذخیره‌سازی پایدار در /data · پورت وب از متغیر PORT پلتفرم</p></section>'
    return render(body)

@app.post('/accounts')
async def add_account(request: Request):
    if not authenticated(request): return RedirectResponse('/login', status_code=303)
    form = await request.form()
    username = str(form.get('username','')).strip()
    try: quota = float(form.get('quota','0'))
    except ValueError: return render('<section class="card">مقدار حجم نامعتبر است.</section>', 'خطا', 400)
    expires = str(form.get('expires','')).strip() or None
    note = str(form.get('note','')).strip()[:300]
    if not username or len(username)>64 or quota < 0: return render('<section class="card">اطلاعات نامعتبر است.</section>', 'خطا', 400)
    try:
        with database() as con:
            con.execute('INSERT INTO accounts(username,quota_gb,expires,note,status,public_id,created_at) VALUES(?,?,?,?,?,?,?)', (username,quota,expires,note,'active',str(uuid.uuid4()),datetime.now(timezone.utc).isoformat()))
    except sqlite3.IntegrityError:
        return render('<section class="card">این نام کاربری از قبل ثبت شده است. <a href="/">بازگشت</a></section>', 'خطا', 409)
    return RedirectResponse('/', status_code=303)

@app.get('/sub/{public_id}')
def public_subscription(public_id: str):
    with database() as con:
        row = con.execute('SELECT username,quota_gb,expires,status,public_id,created_at FROM accounts WHERE public_id=?', (public_id,)).fetchone()
    if not row:
        return render('<section class="card"><h2>اشتراک پیدا نشد</h2><p class="muted">لینک اشتراک نامعتبر یا حذف شده است.</p></section>', 'اشتراک ناموجود', 404)
    state, is_active = subscription_state(row)
    pill = '<span class="pill">فعال</span>' if is_active else '<span class="pill off">{}</span>'.format(html.escape(state))
    body = '<section class="card"><div class="brand">POMP NET MOHAMMAD — SUPER JINX SUB</div><h1 class="hero">اطلاعات اشتراک</h1><p class="muted">به صفحه اختصاصی اطلاعات اشتراک خوش آمدید.</p><div class="stats"><div class="stat"><span class="muted">نام کاربری</span><b style="font-size:20px">{}</b></div><div class="stat"><span class="muted">حجم ثبت‌شده</span><b>{} GB</b></div><div class="stat"><span class="muted">وضعیت</span><b style="font-size:20px">{}</b></div></div><div class="card"><p>تاریخ انقضا: <b>{}</b></p><p>شناسه اشتراک: <code>{}</code></p><p class="muted">این صفحه فقط اطلاعات ثبت‌شده را نمایش می‌دهد. مصرف واقعی شبکه و اتصال VPN در این سرویس ارائه نمی‌شود.</p></div></section>'.format(html.escape(row['username']),row['quota_gb'],pill,html.escape(row['expires'] or 'بدون انقضا'),html.escape(row['public_id']))
    return render(body, 'اطلاعات اشتراک')

@app.post('/accounts/{account_id}/renew')
async def renew_account(account_id: int, request: Request):
    if not authenticated(request): return RedirectResponse('/login', status_code=303)
    form = await request.form()
    expires = str(form.get('expires','')).strip()
    try: date.fromisoformat(expires)
    except ValueError: return render('<section class="card">تاریخ تمدید نامعتبر است. <a href="/">بازگشت</a></section>', 'خطا', 400)
    with database() as con:
        con.execute('UPDATE accounts SET expires=? WHERE id=?', (expires, account_id))
    return RedirectResponse('/', status_code=303)

@app.post('/accounts/{account_id}/toggle')
def toggle(account_id: int, request: Request):
    if not authenticated(request): return RedirectResponse('/login', status_code=303)
    with database() as con:
        row = con.execute('SELECT status FROM accounts WHERE id=?', (account_id,)).fetchone()
        if row: con.execute('UPDATE accounts SET status=? WHERE id=?', ('suspended' if row['status']=='active' else 'active', account_id))
    return RedirectResponse('/', status_code=303)

@app.post('/accounts/{account_id}/delete')
def delete_account(account_id: int, request: Request):
    if not authenticated(request): return RedirectResponse('/login', status_code=303)
    with database() as con:
        con.execute('DELETE FROM accounts WHERE id=?', (account_id,))
    return RedirectResponse('/', status_code=303)

@app.get('/api/accounts')
def list_accounts(request: Request):
    if not authenticated(request): return JSONResponse({'detail':'unauthorized'}, status_code=401)
    with database() as con: rows = con.execute('SELECT id,username,quota_gb,expires,note,status,public_id,created_at FROM accounts ORDER BY id DESC').fetchall()
    return [dict(row) for row in rows]

@app.get('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=303)
