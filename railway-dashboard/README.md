# POMP NET MOHAMMAD — SUPER JINX: Railway dashboard

This is a standalone management dashboard for account metadata. It supports administrator login, account records, quota labels, expiry dates, activation/suspension and a protected JSON listing endpoint. SQLite data is stored under `/data`.

**Important limitation:** this service does not run Xray, VPN, proxy, anonymization, generate VLESS/VMess/Trojan connection profiles, enforce network traffic quotas, or provide working VPN subscriptions. Railway prohibits VPN/proxy/anonymization workloads; this dashboard is intentionally limited to permitted non-network account management.

## Deploy
1. Create a new Railway service from branch `railway-safe-dashboard`.
2. Set Root Directory to `/railway-dashboard`.
3. Add a Railway Volume mounted at `/data`.
4. Set `ADMIN_USERNAME` (3+ characters), `ADMIN_PASSWORD` (14+ characters), and `SESSION_SECRET` (at least 32 random characters).
5. Set healthcheck path to `/health` and deploy. Railway supplies `PORT`.
6. Open the generated HTTPS domain and sign in at `/login`.

Do not commit passwords or session secrets.
