import os, sqlite3, secrets, hmac, html
from datetime import datetime, timezone
from contextlib import contextmanager
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
input,button{font:inherit;padding:11px 13px;border-radius:10px;border:1px solid #51465f;background:#0e0c17;color:#fff;margin:4px;max-width:100%}input:focus{outline:1px solid var(--blue)}button{background:linear-gradient(110deg,#6222b2,#245eb6);border:0;cursor:pointer}button.danger{background:#702a43}button.secondary{background:#30263f;border:1px solid #51465f}a{color:#8dbbff;text-decoration:none}.row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;min-width:740px}td,th{padding:12px 9px;border-bottom:1px solid #383344;text-align:right;white-space:nowrap}th{color:#bca0ff;font-weight:600}.pill{display:inline-block;padding:4px 9px;border-radius:30px;background:#163d32;color:#8ff0c5;font-size:12px}.pill.off{background:#492132;color:#ff9fbd}.actions form{display:inline}.actions input{width:105px}.search{display:flex;gap:6px;flex-wrap:wrap}.search input{flex:1;min-width:150px}.foot{margin:22px 0;color:#8e879e;font-size:12px}
@media(max-width:620px){main{margin:8px auto;padding:10px}.card{padding:14px}.stats{grid-template-columns:1fr}.hero{font-size:25px}}
</style></head><body><main><header class="top"><div><div class="brand">POMP NET MOHAMMAD</div><h1 class="hero">SUPER JINX</h1><div class="tag">به پنل پمپ نت محمد خوش آمدید</div></div></header>""" + body + '<footer class="foot">قدرت ساخت، آزادی انتخاب، کنترل در دستان تو</footer></main></body></html>'
    return HTMLResponse(page, status_code=code)

def authenticated(request):
    return request.session.get('admin') is True

@app.get('/health')
def health():
    return {'status':'ok','service':'SUPER JINX management dashboard','mode':'management-only'}

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
        status = '<span class="pill">فعال</span>' if r['status']=='active' else '<span class="pill off">تعلیق‌شده</span>'
        table_rows.append(
            '<tr><td>{}</td><td><b>{}</b><br><small class="muted">{}</small></td><td>{} GB</td><td>{}</td><td>{}</td><td class="actions">'
            '<form method="post" action="/accounts/{}/toggle"><button class="secondary">تغییر وضعیت</button></form>'
            '<form method="post" action="/accounts/{}/delete" onsubmit="return confirm(\'حذف این رکورد؟\')"><button class="danger">حذف</button></form></td></tr>'.format(
                r['id'], html.escape(r['username']), html.escape(r['note'] or 'بدون یادداشت'),
                r['quota_gb'], html.escape(r['expires'] or 'بدون انقضا'), status, r['id'], r['id'])
        )
    body = '<section class="stats"><div class="stat"><span class="muted">کل حساب‌ها</span><b>{}</b></div><div class="stat"><span class="muted">فعال</span><b>{}</b></div><div class="stat"><span class="muted">تعلیق‌شده</span><b>{}</b></div></section>'.format(total,active,suspended)
    body += '<section class="card"><div class="row" style="justify-content:space-between"><h2>مدیریت حساب‌ها</h2><a href="/logout">خروج از پنل ↗</a></div><p class="muted">مدیریت اطلاعات و وضعیت رکوردهای حساب کاربری.</p><form method="post" action="/accounts" class="row"><input name="username" placeholder="نام کاربری" required maxlength="64"><input name="quota" type="number" min="0" step="0.1" placeholder="حجم ثبت‌شده GB" required><input name="expires" type="date"><input name="note" placeholder="یادداشت"><button>＋ ایجاد حساب</button></form></section>'
    body += '<section class="card"><div class="row" style="justify-content:space-between"><h2>فهرست حساب‌ها</h2><span class="muted">نمایش {} مورد</span></div><form class="search" method="get"><input name="q" value="{}" placeholder="جست‌وجوی نام یا یادداشت"><button>جست‌وجو</button><a class="row" href="/">پاک‌کردن</a></form><div class="tablewrap"><table><tr><th>#</th><th>حساب</th><th>سهمیه ثبت‌شده</th><th>انقضا</th><th>وضعیت</th><th>عملیات</th></tr>{}</table></div></section>'.format(len(rows),html.escape(query),''.join(table_rows) or '<tr><td colspan="6" class="muted">رکوردی پیدا نشد.</td></tr>')
    body += '<section class="card"><h2>وضعیت سرویس</h2><p class="muted">پنل مدیریتی مستقل · پایگاه داده SQLite · مسیر ذخیره‌سازی پایدار /data</p><p class="muted">این نسخه فقط اطلاعات مدیریتی حساب‌ها را نگه‌داری می‌کند؛ سهمیه ثبت‌شده را روی ترافیک شبکه اعمال نمی‌کند و پروفایل اتصال VPN یا Proxy تولید نمی‌کند.</p></section>'
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
            con.execute('INSERT INTO accounts(username,quota_gb,expires,note,status,public_id,created_at) VALUES(?,?,?,?,?,?,?)', (username,quota,expires,note,'active',secrets.token_urlsafe(18),datetime.now(timezone.utc).isoformat()))
    except sqlite3.IntegrityError:
        return render('<section class="card">این نام کاربری از قبل ثبت شده است. <a href="/">بازگشت</a></section>', 'خطا', 409)
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
    with database() as con: rows = con.execute('SELECT id,username,quota_gb,expires,note,status,created_at FROM accounts ORDER BY id DESC').fetchall()
    return [dict(row) for row in rows]

@app.get('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=303)
