# POMP NET MOHAMMAD × SUPER JINX — official SideRail runtime with a branded build layer.
# Upstream application, authentication, API and Xray logic remain pinned and intact.
FROM node:24-bookworm-slim AS build
ARG SIDERAIL_COMMIT=6d794ce2303a01ecc412941a4f38fd00a3bda65b
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates python3  && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN git clone https://github.com/icubaby/SideRail.git upstream \
 && cd upstream \
 && git checkout --detach "$SIDERAIL_COMMIT" \
 && test "$(git rev-parse HEAD)" = "$SIDERAIL_COMMIT"
WORKDIR /build/upstream
ENV npm_config_audit=false npm_config_fund=false

# Apply the same POMP NET RTL/theme/subscription patches used by the dedicated
# SideRail image. These alter presentation and generated labels only; they do
# not replace routes, authentication, user records, subscription tokens or Xray.
COPY siderail/pompnet-theme.css /tmp/pompnet-theme.css
COPY siderail/patch_i18n.py /tmp/patch_i18n.py
COPY siderail/patch_tunnel.py /tmp/patch_tunnel.py
COPY siderail/patch_subscription.py /tmp/patch_subscription.py
COPY siderail/patch_brand.py /tmp/patch_brand.py
RUN cat /tmp/pompnet-theme.css >> apps/web/src/index.css \
 && python3 /tmp/patch_i18n.py \
 && python3 /tmp/patch_tunnel.py \
 && python3 /tmp/patch_subscription.py \
 && python3 /tmp/patch_brand.py

RUN npm ci --prefer-offline --no-audit --no-fund \
 && npm run build \
 && npm prune --omit=dev

FROM node:24-bookworm-slim AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates unzip \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /build/upstream/node_modules ./node_modules
COPY --from=build /build/upstream/package.json ./package.json
COPY --from=build /build/upstream/apps/server/package.json ./apps/server/package.json
COPY --from=build /build/upstream/apps/server/dist ./apps/server/dist
COPY --from=build /build/upstream/apps/web/dist ./public
# Preserve upstream license, NOTICE, authorship and source attribution.
COPY --from=build /build/upstream/LICENSE ./LICENSE
COPY --from=build /build/upstream/NOTICE ./NOTICE
COPY --from=build /build/upstream/README.md ./UPSTREAM-README.md

# Keep the former POMP NET Railway Volume intact; SideRail stores its own
# SQLite database and Xray state in a separate subdirectory, not over Marzban.
ENV PORT=8080 \
    SIDERAIL_DATA_DIR=/var/lib/marzban/siderail \
    CORE_DIR=/var/lib/marzban/siderail/core \
    CORE_VERSION=v26.9.9
EXPOSE 8080
CMD ["node", "apps/server/dist/index.js"]
