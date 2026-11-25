# Official PasarGuard panel behind an internal TLS hop + Railway HTTP edge.
FROM pasarguard/panel:latest

USER root
RUN apt-get update && apt-get install -y --no-install-recommends nginx openssl curl \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /etc/nginx/sites-enabled/default

COPY start-railway.sh /usr/local/bin/start-railway.sh
RUN chmod 0755 /usr/local/bin/start-railway.sh

ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000 \
    UVICORN_SSL_CERTFILE=/var/lib/pasarguard/certs/railway-cert.pem \
    UVICORN_SSL_KEYFILE=/var/lib/pasarguard/certs/railway-key.pem \
    UVICORN_SSL_CA_TYPE=private \
    UVICORN_PROXY_HEADERS=true \
    UVICORN_FORWARDED_ALLOW_IPS=127.0.0.1 \
    SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:////var/lib/pasarguard/db.sqlite3 \
    DEBUG=false \
    DOCS=false

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/start-railway.sh"]
