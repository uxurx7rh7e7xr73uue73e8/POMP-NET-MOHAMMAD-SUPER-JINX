# Build the pinned SideRail backend as an internal engine for the POMP NET single-service panel.
# Its SPA is not exposed; operators use the POMP NET login, dashboard and subscription skin.
FROM node:24-bookworm-slim AS siderail-build
ARG SIDERAIL_COMMIT=6d794ce2303a01ecc412941a4f38fd00a3bda65b
RUN apt-get update && apt-get install -y --no-install-recommends git python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN git clone https://github.com/icubaby/SideRail.git upstream \
 && cd upstream \
 && git checkout --detach "$SIDERAIL_COMMIT" \
 && test "$(git rev-parse HEAD)" = "$SIDERAIL_COMMIT"
WORKDIR /build/upstream
ENV npm_config_audit=false npm_config_fund=false
COPY siderail/pompnet-theme.css /tmp/pompnet-theme.css
COPY siderail/patch_i18n.py /tmp/patch_i18n.py
COPY siderail/patch_tunnel.py /tmp/patch_tunnel.py
COPY siderail/patch_brand.py /tmp/patch_brand.py
RUN cat /tmp/pompnet-theme.css >> apps/web/src/index.css \
 && python3 /tmp/patch_i18n.py \
 && python3 /tmp/patch_tunnel.py \
 && python3 /tmp/patch_brand.py
RUN npm ci --prefer-offline --no-audit --no-fund \
 && npm run build \
 && npm prune --omit=dev

FROM gozargah/marzban:latest

RUN apt-get update \\
 && apt-get install -y --no-install-recommends nginx curl ca-certificates procps libstdc++6 \\
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default
# Node 24 runs SideRail privately; only Nginx port 8080 is public.
COPY --from=siderail-build /usr/local/bin/node /usr/local/bin/node
RUN chmod 0755 /usr/local/bin/node && node --version
RUN mkdir -p /opt/siderail/apps/server /opt/siderail/apps/web
COPY --from=siderail-build /build/upstream/package.json /opt/siderail/package.json
COPY --from=siderail-build /build/upstream/package-lock.json /opt/siderail/package-lock.json
COPY --from=siderail-build /build/upstream/LICENSE /opt/siderail/LICENSE
COPY --from=siderail-build /build/upstream/NOTICE /opt/siderail/NOTICE
COPY --from=siderail-build /build/upstream/README.md /opt/siderail/UPSTREAM-README.md
COPY --from=siderail-build /build/upstream/apps/server/package.json /opt/siderail/apps/server/package.json
COPY --from=siderail-build /build/upstream/node_modules /opt/siderail/node_modules
COPY --from=siderail-build /build/upstream/apps/server/dist /opt/siderail/apps/server/dist
COPY --from=siderail-build /build/upstream/apps/web/dist /opt/siderail/apps/web/dist
# ⚡ nginx defaults allow only 768 connections per worker: every config uses 2 (phone + core), so busy panels got slow.
#    Raised to 16384 per worker with a matching file limit (never fails the build)
RUN ( sed -i 's/worker_connections [0-9]*;/worker_connections 16384;/; s/# *multi_accept on;/multi_accept on;/' /etc/nginx/nginx.conf \
      && (grep -q '^worker_rlimit_nofile' /etc/nginx/nginx.conf || sed -i '1i worker_rlimit_nofile 65535;' /etc/nginx/nginx.conf) \
      && grep -E 'worker_connections|worker_rlimit_nofile|multi_accept' /etc/nginx/nginx.conf ) || echo "nginx tuning skipped"
# Cloudflare tunnel client (optional feature): a download hiccup never fails the build
RUN ( curl -fsSL --retry 3 --retry-delay 2 -o /usr/local/bin/cloudflared https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
      && chmod +x /usr/local/bin/cloudflared && cloudflared --version ) || ( rm -f /usr/local/bin/cloudflared; echo "cloudflared download skipped, tunnel mode disabled" )

COPY ws.inc /etc/nginx/ws.inc
COPY gate.inc /etc/nginx/gate.inc
COPY nginx.conf /etc/nginx/conf.d/marzban.conf
COPY nginx.conf /opt/jinx/nginx.conf.tpl
COPY xray_config.json locked_inbound.json lock.py enforce_hosts.py ensure_admin.py doctor.py jinx_api.py /opt/
COPY migration/pompnet_3xui_bridge.py /opt/pompnet_3xui_bridge.py
COPY migration/audit_marzban_db.py /opt/audit_marzban_db.py
COPY migration/import_marzban_to_3xui.py /opt/import_marzban_to_3xui.py
COPY jinx.css jinx.js donate.html donate-config.js bot.html /opt/jinx/
COPY pompnet-dashboard.html /opt/jinx/pompnet-dashboard.html
COPY pompnet-motion.css pompnet-motion.js /opt/jinx/
COPY sub.html /opt/jinx/templates/subscription/index.html
COPY sub.html /opt/jinx/sub.golden.html
COPY donate.html /opt/jinx/donate.golden.html
COPY donate-config.js /opt/jinx/donate-config.golden.js

# QR codes for the subscription page are made on our own server (no external site). Never fails the build.
RUN pip install --no-cache-dir segno==1.6.6 || echo "segno install skipped, QR button will hide itself"

# Persian font bundled inside the image (works even when Google Fonts is blocked). Never fails the build.
RUN mkdir -p /opt/jinx/fonts \
 && ( curl -fsSL -o /tmp/vz.zip https://github.com/rastikerdar/vazirmatn/releases/download/v33.003/vazirmatn-v33.003.zip \
      && mkdir -p /tmp/vz && cd /tmp/vz && python -c "import zipfile; zipfile.ZipFile('/tmp/vz.zip').extractall('.')" \
      && for w in Regular Medium Bold; do f=$(find /tmp/vz -name "Vazirmatn-$w.woff2" | head -1); [ -n "$f" ] && cp "$f" /opt/jinx/fonts/; done \
      ; rm -rf /tmp/vz /tmp/vz.zip ) || echo "font download skipped, using system font" \
 && ls /opt/jinx/fonts
COPY pompnet_telegram_bot.py /opt/pompnet_telegram_bot.py
COPY doctor.html /opt/jinx/doctor.html
COPY xray_preflight.py /opt/xray_preflight.py
# Package the independent manager without activating a second Xray process.
COPY native_core/pompnet_core.py /opt/pompnet_core.py
COPY start.sh /start.sh

# fix Windows line endings, just in case
RUN sed -i 's/\r$//' /start.sh /opt/*.py /opt/*.json /opt/jinx/jinx.css /opt/jinx/jinx.js /opt/jinx/pompnet-motion.css /opt/jinx/pompnet-motion.js /opt/jinx/donate.html /opt/jinx/donate-config.js /opt/jinx/templates/subscription/index.html /opt/jinx/sub.golden.html /opt/jinx/donate.golden.html /opt/jinx/donate-config.golden.js /opt/jinx/doctor.html /etc/nginx/ws.inc /etc/nginx/gate.inc /etc/nginx/conf.d/marzban.conf /opt/jinx/nginx.conf.tpl \
 && chmod +x /start.sh && chmod -R a+rX /opt/jinx

ENV PORT=8080 \
    UVICORN_HOST=127.0.0.1 \
    UVICORN_PORT=8000 \
    XRAY_JSON=/var/lib/marzban/xray_config.json \
    SQLALCHEMY_DATABASE_URL=sqlite:////var/lib/marzban/db.sqlite3 \
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES=43200 \
    CUSTOM_TEMPLATES_DIRECTORY=/opt/jinx/templates/ \
    SUBSCRIPTION_PAGE_TEMPLATE=subscription/index.html
EXPOSE 8080
ENTRYPOINT ["/start.sh"]
CMD []
