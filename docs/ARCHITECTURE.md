# LifeOS — Architecture & Data Model (Phase 1)

> Single-user, web-first **PWA**, **self-hosted on Railway**, **AI-native data substrate** (chat/agents deferred but architected-for). Last updated 2026-06-13.

## 1. Guiding principles
1. **Capture friction is the enemy** — fewest taps, voice/photo-first, AI structures the rest. (#1 churn driver across all research.)
2. **Structured default, freeform fallback** — every domain has structured columns *and* a freeform/`notes` field; raw input is always retained. AI fills structure where confident, leaves prose where not.
3. **AI-native substrate now, chat later** — append-only timeline + retained media + embedding-ready text so insights/chat/agents switch on without re-modeling.
4. **Never lose data; never overclaim** — one-click full export; insights are confidence-scored and uncertainty-aware.
5. **Privacy by construction** — sensitive media (body/medical) encrypted, access-gated; AI analysis is opt-out-able per album.

## 2. Tech stack (grounded & pinned, 2026-06-13 — see `research/stack-grounding.md`)

| Layer | Choice | Why |
|---|---|---|
| **PWA** | React **19.2** + TS + **Vite 8** (Rolldown) + `vite-plugin-pwa` 1.3 + Workbox Background Sync | Installable; IDB-first offline capture queue; React 19 `useOptimistic`/`useActionState`. Node 22. |
| **UI** | **Tailwind v4** (`@tailwindcss/vite`) + **shadcn/ui** + TanStack Query 5.101 | shadcn supports Tailwind v4 + React 19 (ref-as-prop). |
| **Offline capture** | IndexedDB queue (Dexie) → Background Sync on reconnect | Durable even before the SW is active; optimistic UI. |
| **Backend** | Python **3.13** + **FastAPI 0.136** (`[standard]`) + Pydantic **2.13** | Full Pydantic v2; lifespan via asynccontextmanager. uv-managed. |
| **LLM abstraction** | **DSPy 3.2.1** signatures (`Signature` + `Literal`) over OpenRouter (LiteLLM) | Structured I/O; provider-swappable. |
| **DB** | **PostgreSQL 18** + **pgvector 0.8.2** (single instance) | One datastore: JOIN embeddings ⨝ timeline. `vector(1024)` for Voyage-4; HNSW deferred until search. No separate vector DB until ~5–10M vectors. |
| **ORM / migrations** | **SQLAlchemy 2.0.50 async** + **psycopg 3** driver + **Alembic 1.18** + pgvector 0.4.2 | One async-capable driver for app + sync Alembic; eager-load to avoid `MissingGreenlet`. |
| **Object storage** | **Cloudflare R2** (S3-compat, zero egress) + **app-side AES-256** on sensitive media | Holds only ciphertext for sensitive media; presigned PUT/GET (client↔bucket direct). Postgres/compute stay on Railway. |
| **Queue / jobs** | **Procrastinate** (Postgres-backed) — **no Redis** | Transactional enqueue in the same txn; in-worker cron; arq is now maintenance-only. |
| **Auth** | Single-user **WebAuthn passkey** (+ password fallback) | No external dependency; biometric gate fits sensitive data. |
| **EPUB reader** | **epub.js** via **react-reader** | CFI/locations/annotations; strict CSP on upload. |
| **AI — all via OpenRouter** (1 key) | image-gen `google/gemini-3.1-flash-image-preview` · vision/categorize `google/gemini-3.5-flash` + `google/gemini-3.1-flash-lite` · health-vision/insight `anthropic/claude-sonnet-4.6` · capture-parse `anthropic/claude-haiku-4.5` | One key for chat+vision+image-gen. **ZDR routing (`provider.zdr`) for sensitive data.** |
| **Embeddings** | **Voyage 4** (`voyage-4`, 1024-dim) — **direct Voyage key** | Voyage is NOT on OpenRouter → its own key. int8 quantization for cheap storage. |
| **Dominant color** | Python **Pillow + sklearn k-means (LAB)** / colorthief; **webcolors + CIEDE2000** naming | Deterministic, free. AI only for cutout/tagging/season verdict. |
| **STT (voice log)** | **ElevenLabs Scribe v2** (batch) — **direct key** | Accuracy + 90+ langs for dictate-then-store. Not on OpenRouter. |
| **Deploy** | Railway services: `web`, `api`, `worker`, `postgres` (no Redis), `bucket` | Private networking; `/health` zero-downtime; uv multi-stage Docker. |

## 3. Repo structure
```
LifeOS/
  web/        # React + Vite PWA (TypeScript)
  api/        # FastAPI + DSPy + Alembic migrations (Python)
  worker/     # arq jobs + cron (Withings sync, photo analysis, insight batch)
  docs/       # this folder (decisions, phases, research, seeds)
  CLAUDE.md
```
TS types are generated from FastAPI's OpenAPI (`openapi-typescript`) — one source of truth, no drift.

## 4. Data model — timeline spine + normalized domains

**The spine:** an append-only `timeline_events` index unifies everything for the timeline, search, and embeddings; each row points to a normalized domain record.

```sql
timeline_events (
  id            uuid pk default gen_random_uuid(),
  user_id       uuid not null,
  occurred_at   timestamptz not null,        -- when it happened
  logged_at     timestamptz not null default now(),
  domain        text not null,               -- sleep|nutrition|hydration|care|photo|body_metric|
                                              -- work|book|wardrobe|egestion|gym|mood|symptom|
                                              -- supplement|media|location  (enum, lockstep w/ TS+DSPy)
  ref_table     text,                         -- normalized table name
  ref_id        uuid,                         -- row in that table
  source        text not null,                -- manual|voice|photo|withings|auto
  raw_input     text,                         -- original freeform text / transcript (always kept)
  summary       text,                         -- human + embeddable one-liner
  embedding     vector(1024),                 -- pgvector; nullable until embedded
  media         jsonb default '[]',           -- [{bucket_key, kind, analysis_ref}]
  confidence    real,
  created_at    timestamptz default now()
);
-- indexes: (user_id, occurred_at desc), (domain, occurred_at), ivfflat(embedding)
```

**Normalized domain tables** (structured cols + `notes` freeform each):
- `sleep_logs` (bed_at, wake_at, duration, quality 1–5, awakenings, naps[], notes)
- `food_logs` (occurred_at, meal_type, dish_text, ingredients jsonb[from AI], photo_key, macros jsonb[estimate, non-authoritative], caffeine_mg, alcohol_units, notes)
- `hydration_logs` (volume_ml, kind)
- `care_routines` / `care_routine_versions` (phased over time) / `care_routine_runs` (which steps done, exceptions) / `products` (name, brand, role, inci jsonb, category) / `product_rules` (conflict/warning engine — seeded from RevampPrince)
- `photos` (photo_type face|skin|body|hair|nails, bucket_key, capture_pose, prev_photo_id[ghost-overlay], analysis jsonb, ai_model)
- `body_metrics` (from Withings: weight, fat_pct, fat_mass, lean_mass, muscle_mass, body_water, bone_mass, hr, source) — see `research/withings-api.md`
- `bristol_logs` (type 1–7, color, straining, blood, pain, notes) + `urine_logs` (color_scale 1–8, notes)
- `gym_sessions` → `gym_sets` (exercise_id, set#, load, reps, rpe, is_warmup) + `exercises` (name, category, demo_url, substitutions[], notes) — schema modeled on Nippard sheet (Program→Block→Week→Day→Exercise)
- `clothing_items` / `outfits` / `outfit_items` — full SQL in `research/gemini-image-pipeline.md`
- `books` / `editions` (physical|ebook|audio) / `reading_sessions` (cfi/%/page) / `highlights` / `tags` — full model in `research/reader3-epub.md`
- `mood_logs` (mood, energy, stress 1–5, journal) · `symptom_logs` (type, severity, notes)
- `supplements` (inventory) / `supplement_logs` (taken_at, dose) — folded into food/drink flow
- `work_days` (date, scheduled 9–5 WFH, actual blocks, ooo_toggles[])
- `location_log` (occurred_at, lat/lng or place, source) — **daily location changelog** · `weather_snapshots` (auto via weather API, joined to day)
- `habits` / `habit_events` — generalized; **nail-biting** = relapse-tolerant streak + trigger/context tags

## 5. AI pipeline — "structured default, freeform fallback"
1. **Capture** (text/voice/photo) → lands in offline queue → `api`.
2. **Parse:** Claude Haiku 4.5 via a DSPy signature with a per-domain Pydantic schema → fills structured fields it's confident about, routes ambiguous content to `raw_input`/`notes`, sets `confidence`. Low confidence → UI asks a one-tap confirm.
3. **Photo flow:** detect-then-generate gate (cheap classify) → if needed, Nano Banana cutout/normalize (wardrobe) → understanding model extracts structured analysis (Gemini Flash for garment/food; Claude Sonnet for skin/body/nail) → store `analysis` + provenance (`ai_model`, `ai_confidence`).
4. **Embed:** summary → Voyage/gemini-embedding → pgvector (populated continuously; queried when chat ships).

**Model-routing table** lives in `research/gemini-image-pipeline.md` §routing.

## 6. Insight & correlation engine (lightweight now, causal-leaning)
- **Nightly batch** (`worker` cron): compute associations across domains over lagged windows (e.g., dairy/sleep → next-day skin/egestion/mood).
- **Anti-spurious guards:** minimum sample size, multiple-comparison correction (BH-FDR), require a plausible lag, flag confounders. Prefer effect-size + CI over raw p.
- **LLM as careful interpreter, not generator:** Claude Sonnet turns vetted statistical signals into **confidence-scored, uncertainty-aware insight cards** ("*weak* signal: breakouts tend to follow <6h sleep — 7 of 9 instances, n small"). Never asserts causation.
- Clean **executive summary** over a deep (hidden) data layer — research's clear UX lesson.

## 7. Withings integration
Verdict **EASY**. Webhook (`Notify appli=1`) → `worker` fetches `getmeas` (meastypes 1,5,6,8,11,76,77,88) → upsert `body_metrics`. HMAC signature/nonce + refresh-token rotation handled by a Withings-aware lib. Full recipe: `research/withings-api.md`. Sleep/steps available via `user.activity` as an off-by-default toggle.

## 8. Privacy & security
- All media in **Railway Buckets**, presigned URLs only, never public. **App-side AES-256-GCM encryption** on sensitive body/medical media before upload (key in `MEDIA_ENCRYPTION_KEY`, never in the bucket) → Railway stores only ciphertext. Nightly backup → R2/B2.
- **OpenRouter ZDR for sensitive data:** every request sends `provider.zdr=true` + `data_collection=deny`; account prompt-logging OFF + training OFF. Claude 4.6/4.5 + Gemini 3.x text/vision have ZDR endpoints (Vertex/Bedrock).
- **Sensitive body/medical images NEVER go to nano-banana** (`gemini-3.1-flash-image` has no ZDR endpoint) — only to ZDR Claude vision, and only when the album is opt-in. Nano-banana handles **wardrobe** images only.
- **Sensitive albums:** app-lock (passkey re-auth) + per-album **`exclude_from_cloud_ai`** flag (no cloud call at all when set).
- Secrets in Railway env vars. Postgres + buckets in your project only. **One-click full export** (media ZIP + JSON/CSV) — anti-lock-in.

## 9. Future-ready hooks (built as substrate, not features yet)
- Embeddings populated now → **semantic search & RAG chat** later.
- Append-only timeline + structured payloads → **autonomous agents / proactive SMS-email** later (owner-gated).
- DSPy signatures + traceable `ai_model` stamps → models swappable without migration.

## 10. Deployment (Railway)
Provision via the `use-railway` skill / railway MCP: `postgres` (PG18 + pgvector), `api` (FastAPI, uv multi-stage Docker), `worker` (Procrastinate — same image, different start cmd, no domain), `web` (static PWA). **No Redis; media on Cloudflare R2 (external).** Private networking + private `DATABASE_URL` (not public, zero egress) between services; `/health` for zero-downtime; bind `api` to `::`; run Alembic in the pre-deploy/start step (not build). `api` public HTTPS domain doubles as the Withings webhook callback.

## 11. Architecture-review refinements (adversarial review, 2026-06-13)
Full register + sources: `research/architecture-review.md`.

**Adopted now (no-brainers):**
- **Lazy embeddings** — store raw text/extractions now; do NOT generate Voyage vectors until the chat phase (avoids paying for never-queried vectors + forced re-embed on a model upgrade). Keep `embedding` nullable + tag `embedding_model_version` per row.
- **AI vision = observation, not metric** — store in `photos.analysis` with `ai_model`/`ai_confidence`/prompt-version; surface relative TRENDS only; island each photo's prompt (no prior values) to avoid trend-fitting.
- **Worker resilience** — idempotent jobs; Railway restart policy; watchdog alert when a job sits in `doing` past a threshold (Procrastinate bugs #1518/#1523); LISTEN/NOTIFY is a latency hint only — polling is the source of truth.
- **Cutout fallback** — deterministic `rembg`/u2net path on the worker so wardrobe cutouts survive a nano-banana regression.
- **Auth recovery** — register ≥2 passkeys + an offline recovery code at setup (no support desk on a self-hosted single-user app).

**Owner decisions (2026-06-13):**
- **Media → Cloudflare R2 direct** (S3-compatible; zero egress; stores only AES ciphertext for sensitive media). Postgres/compute on Railway. Need R2 creds (`S3_ENDPOINT`/`S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY`/`S3_BUCKET`).
- **Sensitive-AI → OpenRouter for everything** with ZDR (`provider.zdr=true` + `data_collection=deny`; account logging/training OFF). Kept per owner; DSPy keeps a direct-provider swap cheap. Sensitive images still never go to nano-banana.
- **Bleeding-edge kept** (Vite 8/Rolldown) — fall back to Vite's stable engine only if a Rolldown panic blocks builds.

**Build order (validated):** spine + 3 domains end-to-end first → live with them → expand to the full 12+. The spine makes incremental domain addition cheap.
