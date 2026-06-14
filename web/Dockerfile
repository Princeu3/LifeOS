# ---- build ----
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Baked into the bundle at build time. Railway can override via a VITE_API_URL build arg/var.
ARG VITE_API_URL=https://api.os.princeuniverse.dev
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

# ---- serve (static, SPA fallback) ----
FROM caddy:2-alpine
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
