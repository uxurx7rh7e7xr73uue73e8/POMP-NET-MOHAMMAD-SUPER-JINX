# POMP NET isolated SideRail runtime.
# Builds the exact upstream revision; keeps upstream LICENSE and attribution intact.
FROM node:24-alpine AS build
ARG SIDERAIL_COMMIT=6d794ce2303a01ecc412941a4f38fd00a3bda65b
RUN apk add --no-cache git
WORKDIR /build
RUN git clone https://github.com/icubaby/SideRail.git upstream \
 && cd upstream \
 && git checkout --detach "$SIDERAIL_COMMIT" \
 && test "$(git rev-parse HEAD)" = "$SIDERAIL_COMMIT"
WORKDIR /build/upstream
ENV npm_config_audit=false npm_config_fund=false
COPY siderail/pompnet-theme.css /tmp/pompnet-theme.css
RUN cat /tmp/pompnet-theme.css >> apps/web/src/index.css
RUN npm ci --prefer-offline --no-audit --no-fund
RUN npm run build
RUN npm prune --omit=dev

FROM node:24-alpine AS runtime
ENV NODE_ENV=production PORT=8080 SIDERAIL_DATA_DIR=/data CORE_DIR=/data/core CORE_VERSION=v26.9.9
WORKDIR /app
RUN apk add --no-cache ca-certificates unzip \
 && mkdir -p /data /data/core \
 && chown -R node:node /data /app
COPY --from=build --chown=node:node /build/upstream/package.json ./package.json
COPY --from=build --chown=node:node /build/upstream/package-lock.json ./package-lock.json
COPY --from=build --chown=node:node /build/upstream/LICENSE ./LICENSE
COPY --from=build --chown=node:node /build/upstream/README.md ./UPSTREAM-README.md
COPY --from=build --chown=node:node /build/upstream/apps/server/package.json ./apps/server/package.json
COPY --from=build --chown=node:node /build/upstream/apps/web/package.json ./apps/web/package.json
COPY --from=build --chown=node:node /build/upstream/apps/web/public ./public
COPY --from=build --chown=node:node /build/upstream/node_modules ./node_modules
COPY --from=build --chown=node:node /build/upstream/apps/server/dist ./apps/server/dist
COPY --from=build --chown=node:node /build/upstream/apps/web/dist ./public
USER node
EXPOSE 8080
CMD ["node","apps/server/dist/index.js"]
