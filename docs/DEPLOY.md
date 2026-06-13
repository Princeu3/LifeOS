# LifeOS — Deploy & Ops (Railway)

## Live
- **Web (PWA):** https://web-production-168bf.up.railway.app
- **API + docs:** https://api-production-507b.up.railway.app (`/health`, `/timeline`, `/docs`)
- **Repo:** https://github.com/Princeu3/LifeOS

## Railway IDs (project "LifeOS", personal workspace)
- project `c2f15945-e339-40f2-af50-6a84d2ab2fce` · env (production) `4ef9dfd1-5c24-4a39-a955-5c833042e1d4`
- services: `api` `132b14be-…` · `web` `3a4d74a2-…` · `Postgres` `d3d3146f-…`
- CLI is authed as `Princeu3`; prefix CLI calls with `RAILWAY_CALLER=skill:use-railway@1.2.3 RAILWAY_AGENT_SESSION=railway-skill-lifeos`.

## Redeploy (monorepo — must use `--path-as-root`)
```bash
# from repo root, with the local .env present (for first-time var setup only)
railway up ./api --path-as-root --service api --ci    # builds api/Dockerfile
railway up ./web --path-as-root --service web --ci    # builds web/Dockerfile (Caddy)
```
`railway up` uploads the **git root**, so `--path-as-root ./<dir>` is REQUIRED to build a subdir.

## Hard-won gotchas (don't relearn these)
1. **Railway's Metal builder rejects BuildKit mounts** — no `--mount=type=cache` (needs a `s/<svcid>-` cacheKey prefix) and **no `--mount=type=bind`** at all. Use plain `COPY` in Dockerfiles. ✅ done.
2. **Bind `0.0.0.0`, not `::`** — the HTTP edge reaches the container via IPv4; `--host ::` → 502. (api CMD uses `--host 0.0.0.0`.)
3. **Monorepo** → `--path-as-root` (above).
4. **CORS:** api reads `FRONTEND_ORIGIN`; set it to the web URL: `railway variables --service api --set "FRONTEND_ORIGIN=https://web-production-168bf.up.railway.app"` (triggers an api redeploy).
5. **DB URL:** Railway gives plain `postgresql://`; `Settings.sqlalchemy_url` normalizes to `postgresql+psycopg://`. `DATABASE_URL` on api is a reference: `${{Postgres.DATABASE_URL}}` (private network).
6. **Secrets:** set once via `railway variables --service api --set "K=$K"` sourced from local `api/.env` (OPENROUTER/VOYAGE/ELEVENLABS/MEDIA_ENCRYPTION_KEY/S3_*). `.env` is gitignored; `.dockerignore` excludes it from images.

## Migrations
The api Dockerfile CMD runs `alembic upgrade head` on start (idempotent). To run locally against Railway PG: `cd api && uv run alembic upgrade head` (uses public proxy URL in `.env`).

## Worker (not deployed yet)
Deploy when its jobs exist: `railway add --service worker` + `railway up ./worker --path-as-root --service worker`, start command `procrastinate --app=worker.app worker`, set `PROCRASTINATE_DSN=${{Postgres.DATABASE_URL}}`.

## ⚠️ Rotate the dev API keys (OpenRouter/Voyage/ElevenLabs/R2) — they were pasted in chat during setup.
