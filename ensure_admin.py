# POMP NET SUPER JINX: real owner-account bootstrap.
# The owner is sudo in the real Marzban database. Passwords are never committed.
import json, os, secrets, sys
from datetime import datetime, timezone

sys.path.insert(0, "/code")
ADMIN = "ADMIN_tanel9990"
PASSWORD_FILE = "/var/lib/marzban/.pompnet-admin-password"
APPLIED_MARKER = "/var/lib/marzban/.pompnet-default-admin-applied"
SYSTEM = "jinx-system"
CRED = "/run/jinx/system.json"

# The owner password must be supplied as a Railway service secret.
# Never generate a different password automatically and never print credentials to logs.
DEFAULT_PW = os.environ.get("ADMIN_PASSWORD", "").strip()
# Do not read a previously generated one-time password file: owner credentials
# are operator-controlled and must come from the ADMIN_PASSWORD secret only.
ALLOW_INSECURE = os.environ.get("ALLOW_INSECURE_ADMIN_PASSWORD", "").strip().lower() in ("1", "true", "yes", "on")
RESET = os.environ.get("RESET_ADMIN_PASSWORD", "").strip().lower() in ("1", "true", "yes", "on")

if not DEFAULT_PW and (not os.path.exists(APPLIED_MARKER) or RESET):
    print("[admin] FATAL: a password is required for a fresh owner or an explicit password reset", flush=True)
    sys.exit(1)
if DEFAULT_PW and len(DEFAULT_PW) < 14 and not ALLOW_INSECURE:
    print("[admin] FATAL: ADMIN_PASSWORD must contain at least 14 characters.", flush=True)
    sys.exit(1)

from passlib.context import CryptContext
from app.db import GetDB
from app.db.models import Admin

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

def set_pw(admin, password):
    admin.hashed_password = pwd.hash(password)
    admin.is_sudo = True
    if hasattr(admin, "password_reset_at"):
        admin.password_reset_at = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

RESELLERS = set()
STORE_BROKEN = False
_seen = False
for path in ("/var/lib/marzban/jinx_resellers.json", "/var/lib/marzban/jinx_resellers.json.bak"):
    if not os.path.exists(path):
        continue
    _seen = True
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("bad format")
        RESELLERS = set(data)
        break
    except Exception:
        continue
else:
    STORE_BROKEN = _seen

with GetDB() as db:
    panel_admins = [x for x in db.query(Admin).all() if x.username != SYSTEM]
    owners = [x for x in panel_admins if x.username not in RESELLERS]
    if STORE_BROKEN:
        print("[admin] WARNING: reseller data unreadable; existing owner accounts left unchanged", flush=True)
    else:
        conflict = any(x.username == ADMIN and x.username in RESELLERS for x in panel_admins)
        if conflict:
            print(f"[admin] FATAL: {ADMIN} is assigned to a reseller; rename that reseller account first", flush=True)
            sys.exit(1)

        applied_before = os.path.exists(APPLIED_MARKER)
        if not owners:
            existing = db.query(Admin).filter(Admin.username == ADMIN).first()
            if existing is None:
                if not DEFAULT_PW:
                    print("[admin] FATAL: no owner exists and no initial ADMIN_PASSWORD is available", flush=True)
                    sys.exit(1)
                owner = Admin(username=ADMIN, hashed_password=pwd.hash(DEFAULT_PW), is_sudo=True)
                db.add(owner)
                print(f"[admin] created full-access owner account {ADMIN}", flush=True)
            else:
                print("[admin] FATAL: no owner account is available; refusing to overwrite reseller access", flush=True)
                sys.exit(1)
        else:
            owner = next((x for x in owners if x.username == ADMIN), None) or next((x for x in owners if x.is_sudo), owners[0])
            name_conflict = any(x.username == ADMIN and x is not owner for x in panel_admins)
            if name_conflict:
                print(f"[admin] FATAL: username {ADMIN} is already in use by another account", flush=True)
                sys.exit(1)
            owner.username = ADMIN
            owner.is_sudo = True
            if not applied_before or RESET:
                set_pw(owner, DEFAULT_PW)
                print(f"[admin] full-access owner credentials applied for {ADMIN}", flush=True)
            else:
                print(f"[admin] existing owner password preserved for {ADMIN}", flush=True)

        db.commit()
        if not applied_before or RESET:
            fd = os.open(APPLIED_MARKER, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as marker:
                marker.write("completed\n")
                marker.flush()
                os.fsync(marker.fileno())

# Internal support-bot account remains separate and randomly credentialed.
sys_pw = secrets.token_urlsafe(24)
with GetDB() as db:
    system_admin = db.query(Admin).filter(Admin.username == SYSTEM).first()
    if system_admin is None:
        db.add(Admin(username=SYSTEM, hashed_password=pwd.hash(sys_pw), is_sudo=True))
    else:
        set_pw(system_admin, sys_pw)
    db.commit()

os.makedirs("/run/jinx", exist_ok=True)
tmp = CRED + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump({"username": SYSTEM, "password": sys_pw}, f)
    f.flush()
    os.fsync(f.fileno())
os.chmod(tmp, 0o600)
os.replace(tmp, CRED)
print("[admin] support bots credentials ready", flush=True)
