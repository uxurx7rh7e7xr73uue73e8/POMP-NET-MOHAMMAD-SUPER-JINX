# Official SideRail runtime for POMP NET MOHAMMAD.
# The application source, React UI, login flow and API are built unchanged
# from the upstream commit pinned below. No POMP NET UI/i18n/theme patches.
FROM node:24-bookworm-slim AS build
ARG SIDERAIL_COMMIT=6d794ce2303a01ecc412941a4f38fd00a3bda65b
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /build
RUN git clone https://github.com/icubaby/SideRail.git upstream \
 && cd upstream \
 && git checkout --detach "$SIDERAIL_COMMIT" \
 && test "$(git rev-parse HEAD)" = "$SIDERAIL_COMMIT"
WORKDIR /build/upstream
ENV npm_config_audit=false npm_config_fund=false
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
