# Static Vue build + Caddy (TLS, security headers, reverse proxy). Build context: repository root.
FROM docker.io/library/node:22-alpine AS build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM docker.io/library/caddy:2-alpine
COPY deploy/web/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv/www
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -q -O /dev/null http://127.0.0.1:2019/config/ || exit 1
