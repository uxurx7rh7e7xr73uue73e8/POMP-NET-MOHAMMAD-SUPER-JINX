# Railway deployment for the official PasarGuard panel.
# Railway terminates HTTPS at its edge; the app listens on the injected HTTP port.
# Persistent data must be mounted at /var/lib/pasarguard in Railway.
FROM pasarguard/panel:latest

COPY start-railway.sh /usr/local/bin/start-railway.sh
RUN chmod 0755 /usr/local/bin/start-railway.sh

ENV UVICORN_HOST=0.0.0.0 \
    SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:////var/lib/pasarguard/db.sqlite3 \
    DEBUG=false

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/start-railway.sh"]
