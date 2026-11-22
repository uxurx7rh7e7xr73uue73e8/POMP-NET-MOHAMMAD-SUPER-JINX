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
    con.execute('CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, quota_gb REAL NOT NULL DEFAULT 0, expires TEXT, note TEXT NOT NULL DEFAULT "", status TEXT NOT NULL DEFAULT "active", public_id TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL)')

def render(body, title='داشبورد', code=200):
    page = '''<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SUPER JINX</title><style>
    *{box-sizing:border-box}body{margin:0;background:#050509;color:#f5f5fa;font-family:Tahoma,Arial,sans-serif}main{max-width:1100px;margin:28px auto;padding:16px}.card{background:#171721;border:1px solid #8B35FF66;border-radius:18px;padding:20px;margin:14px 0;box-shadow:0 8px 30px #0008}h1,h2{color:#c9a6ff}.muted{color:#aaa}input,button{padding:12px;border-radius:10px;border:1px solid #51465f;background:#101019;color:#fff;margin:5px}button{background:#5b28a8;cursor:pointer}a{color:#8dbbff}table{width:100%;border-collapse:collapse;display:block;overflow:auto}td,th{padding:10px;border-bottom:1px solid #383344;text-align:right;white-space:nowrap}.row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}</style></head><body><main><div class="muted">POMP NET MOHAMMAD</div><h1>SUPER JINX</h1>''' + body + '<p class="muted">قدرت ساخت، آزادی انتخاب، کنترل در دستان تو</p></main></body></html>'
    return HTMLResponse(page, status_code=code)

def authenticated(request):
    return request.session.get('admin') is True

@app.get('/health')
def health():
    return {'status':'ok','service':'SUPER JINX management dashboard','mode':'management-only'}

@app.get('/login')
def login_page():
    return render('<section class="card"><h2>ورود مدیر</h2><form method="post"><input name="username" placeholder="نام کاربری" required><br><input name="password" type="password" placeholder="رمز عبور" required><br><button>ورود</button></form></section>', 'ورود')

@app.post('/login')
async def login(request: Request):
    form = await request.form()
    u, p = str(form.get('username','')), str(form.get('password',''))
    if hmac.compare_digest(u, USER) and hmac.compare_digest(p, PASSWORD):
        request.session.clear()
        request.session['admin'] = True
        return RedirectResponse('/', status_code=303)
    return render('<section class="card">نام کاربری یا رمز نادرست است. <a href="/login">تلاش دوباره</a></section>', 'خطا', 401)

@app.get('/')
def dashboard(request: Request):
    if not authenticated(request): return RedirectResponse('/login', status_code=303)
    with database() as con: rows = con.execute('SELECT * FROM accounts ORDER BY id DESC').fetchall()
    table = ''.join('<tr><td>{}</td><td>{}</td><td>{} GB</td><td>{}</td><td>{}</td><td><form method="post" action="/accounts/{}/toggle"><button>تغییر وضعیت</button></form></td></tr>'.format(r['id'], html.escape(r['username']), r['quota_gb'], html.escape(r['expires'] or 'بدون انقضا'), html.escape(r['status']), r['id']) for r in rows)
    body = '<section class="card"><div class="row"><h2>مدیریت حساب‌ها</h2><a href="/logout">خروج</a></div><p>ثبت و مدیریت اطلاعات حساب‌ها، سهمیه و تاریخ انقضا.</p><form method="post" action="/accounts" class="row"><input name="username" placeholder="نام کاربری" required maxlength="64"><input name="quota" type="number" min="0" step="0.1" placeholder="حجم GB (صفر=نامحدود)" required><input name="expires" type="date"><input name="note" placeholder="یادداشت"><button>ایجاد حساب</button></form></section>'
    body += '<section class="card"><h2>حساب‌ها ({})</h2><table><tr><th>شناسه</th><th>کاربر</th><th>سهمیه ثبت‌شده</th><th>انقضا</th><th>وضعیت</th><th>عملیات</th></tr>{}</table></section>'.format(len(rows), table)
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
    if not username or quota < 0: return render('<section class="card">اطلاعات نامعتبر است.</section>', 'خطا', 400)
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

@app.get('/api/accounts')
def list_accounts(request: Request):
    if not authenticated(request): return JSONResponse({'detail':'unauthorized'}, status_code=401)
    with database() as con: rows = con.execute('SELECT id,username,quota_gb,expires,note,status,created_at FROM accounts ORDER BY id DESC').fetchall()
    return [dict(row) for row in rows]

@app.get('/logout')
def logout(request: Request):
    request.session.clear()
    return RedirectResponse('/login', status_code=303)