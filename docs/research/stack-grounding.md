# Research — Stack Grounding (9 agents, 2026-06-13)

All versions verified live against npm/PyPI/python.org/official docs + the OpenRouter `/models` API. Each row = an agent's opinionated verdict.

## Pinned version matrix
| Area | Locked | Latest verified |
|---|---|---|
| React / Vite | React **19.2.7**, Vite **8.0.16** (Rolldown), `@vitejs/plugin-react` **6.0.2** (peer-locked to Vite 8), vite-plugin-pwa **1.3.0**, workbox **7.4.1**, TanStack Query **5.101**, Tailwind **v4** (`@tailwindcss/vite` 4.3.1), shadcn (Tailwind-v4 + React-19 ready), Node 22 | idem |
| Python / FastAPI | Python **3.13.13** (3.14.6 exists; DSPy wheels safest on 3.13), FastAPI **0.136.3** (`[standard]`), Pydantic **2.13.4** (v1 shim being removed), uv **0.11.21**, DSPy **3.2.1** (NOT 3.3.0b1) | idem |
| DB / vector | **PostgreSQL 18** + **pgvector 0.8.2**. `vector(1024)` for Voyage-4 (HNSW ≤2000 dims; use `halfvec(2048)` if 2048-dim). HNSW `m=8, ef_construction=32`, cosine; defer index until search exists. | idem |
| ORM | **SQLAlchemy 2.0.50 async** + **psycopg 3** (one driver for async app + sync Alembic) + **Alembic 1.18.4** + **pgvector 0.4.2**. Eager-load (`selectinload`) to avoid `MissingGreenlet`; `expire_on_commit=False`. | (asyncpg 0.31 is faster — keep for hot paths only) |
| Queue | **Procrastinate 3.8.1** (Postgres) — NO Redis. Transactional enqueue, `@periodic` cron, queueing locks. (arq → maintenance-only; pgqueuer = runner-up; Taskiq if ever forced onto Redis.) | idem |
| Object storage | **Railway Buckets** (GA, S3-compat, encrypted, $0.015/GB-mo, free egress, presigned ≤90d). Buckets NOT on private net → presigned PUT/GET direct. App-side AES-256-GCM for sensitive media; nightly backup → R2/B2. | — |
| AI models | nano-banana `gemini-3.1-flash-image` (~$0.045–0.15/img, SynthID) · `gemini-3.5-flash` ($1.50/$9) · `gemini-3.1-flash-lite` ($0.25/$1.50) · `claude-sonnet-4-6` ($3/$15) · `claude-haiku-4-5` ($1/$5) | confirmed available |
| Embeddings | **Voyage 4** (`voyage-4`/`-large`/`-lite`, 32K ctx, dims 256–2048, int8/binary). **Direct Voyage key** (not on OpenRouter). | — |
| STT | **ElevenLabs Scribe v2** (batch) — most accurate, 90+ langs, fits dictate-then-store. Deepgram if we pivot to live/on-prem. Direct key. | — |
| Gateway | **OpenRouter** for chat+vision+image-gen. | 337 models live |

## OpenRouter — definitive (queried live)
- **Slugs:** `anthropic/claude-sonnet-4.6`, `anthropic/claude-haiku-4.5`, `google/gemini-3.5-flash`, `google/gemini-3.1-flash-lite`, `google/gemini-3.1-flash-image-preview` (image output via `/chat/completions` + `modalities:["image","text"]`, base64 in `message.images[]`).
- **Image-gen: YES** on OpenRouter → no direct Google key. **Embeddings: YES (26 models, since Nov 2025) but NO Voyage** → Voyage 4 needs its own key. **STT:** Whisper/MAI on OpenRouter, but ElevenLabs is not → direct key.
- **DSPy:** `dspy.LM("openrouter/google/gemini-3.5-flash")` (reads `OPENROUTER_API_KEY`) or `dspy.LM("openai/<slug>", api_base=..., api_key=...)`. Pin `provider` for deterministic structured-output/tool behaviour.
- **Pricing:** 5.5% credit-purchase fee; per-token pass-through. Rate limits per-account.
- **Privacy:** ZDR by default; set account prompt-logging OFF + training OFF; per-request `provider.zdr=true` + `data_collection=deny`. ZDR endpoints exist for Claude 4.6/4.5 + Gemini 3.x text/vision (Vertex/Bedrock). **Nano-banana image endpoints are NOT ZDR** → keep sensitive body/medical images off nano-banana.

## Color pipeline
Cutout (nano-banana, wardrobe only / rembg) → **LAB k-means** (Pillow + sklearn) or colorthief → **webcolors + CIEDE2000** naming → per-axis (temperature/value/chroma) → **Claude Sonnet 4.6** season verdict → Voyage 4 search. Don't use an LLM to count pixels.

## Railway deployment (key practices)
One project; `api` binds `::`; `web` references `api` public domain (build-time env); `worker` = same image, different start cmd, no domain; Postgres via reference var; **private `DATABASE_URL`** (no egress); Dockerfile when system libs needed (e.g. audio); migrations in pre-deploy/start (NOT build — private net is runtime-only); `/health` → zero-downtime (stateless services only; volumes block it); usage + replica limits; serverless app-sleeping for cost (DB pools/long-lived worker prevent sleep).

## Sources
React/Vite (npm + react.dev + vite-pwa docs) · Python/FastAPI/uv/DSPy (PyPI + python.org + Context7) · PG/pgvector (postgresql.org + pgvector repo + dbi-services) · ORM (pgvector-python supported-libs + r/FastAPI + SQLAlchemy docs) · storage (docs.railway.com/storage-buckets + R2/B2 docs) · queue (Railway docs + Procrastinate/pgqueuer docs + arq maintenance notice) · models (ai.google.dev + claude-api skill + Context7 voyageai) · STT/Railway (Deepgram/ElevenLabs docs + benchmarks + Railway docs) · OpenRouter (openrouter.ai/docs + live /models API).
