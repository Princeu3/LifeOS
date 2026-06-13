# LifeOS — Phase Roadmap

> Tracking doc. ⬜ not started · 🔄 in progress · ✅ done.

## Phase 0 — Discovery & Grounding ✅
Decisions, full feature catalog, and grounding (reader3/EPUB, landscape, Withings, image pipeline, gym sheet, RevampPrince seed) — see `DECISIONS.md`, `FEATURE-CATALOG.md`, `research/`.

## Phase 1 — Product & Architecture Spec ✅
`ARCHITECTURE.md`, `CLAUDE.md`, stack grounded & pinned (`research/stack-grounding.md`), adversarial review (`research/architecture-review.md`).

## Phase 2 — Foundation / MVP 🔄
- ✅ Stack & architecture locked; review folded in; scaffold regenerated to final stack.
- ✅ Public OSS repo: github.com/Princeu3/LifeOS (MIT).
- ✅ **Railway `LifeOS` project + Postgres 18.4 provisioned**; **Cloudflare R2 `lifeos-media` wired + verified**.
- ✅ **Alembic `0001` migration applied** — `pgvector` extension + `timeline_events` spine + 11 domain tables (sleep, food, body_metrics, photos, mood, bristol, urine, products, care_routines, care_routine_runs).
- ✅ **Capture → DSPy/OpenRouter parsing verified end-to-end** (freeform → routed structured entry → persisted). Parsed `structured` stored on each event.
- ✅ **Normalize `structured` → typed domain rows** (`app/normalize.py`): capture now projects the parse into SleepLog/FoodLog/MoodLog/Bristol|UrineLog/CareRoutineRun and back-links via `event.ref_table/ref_id` (lossless — full parse stays on `event.structured`). Lenient Pydantic coercion (AliasChoices + `mode=before` validators, never raises) + range clamping. Parser hardened: `now` input for relative-time→ISO, per-domain key hints, `JSONAdapter`. `GET /timeline/{event_id}` hydrates the typed row; web entries expand to show structured fields.
- ✅ Timeline **read API** + daily **timeline UI** + capture screen wired to the live API.
- ✅ **Capture idempotency** (`0003`): client generates a UUID `client_token` once per queued capture (Dexie), reused on every sync retry, sent as the `Idempotency-Key` header. Server dedupes on `UNIQUE (user_id, client_token)` — fast-path returns the existing event (skips the LLM), and races are caught via `IntegrityError`→rollback→re-select. Replay returns 200 with `deduplicated=true`.
- ✅ **Passkey auth (WebAuthn)** (`0004`): up to 2 passkeys + single-use recovery code. py_webauthn server + `@simplewebauthn/browser`; stateless signed **bearer tokens** (localStorage, no cross-site cookies); `rp_id`/origin env-pinned from `FRONTEND_ORIGIN`. First-passkey bootstrap gated by `AUTH_BOOTSTRAP_TOKEN`. capture/timeline/photos now require auth; `<img>` uses a short-lived per-photo **media token** (`?t=`). Web gate (`Auth.tsx`) + CSP. ⚠️ `*.up.railway.app` is a public suffix → rp_id works but a **custom domain** is recommended (hostname churn invalidates passkeys).
- ⬜ Seed care products/routines from RevampPrince (local-only seed).
- ✅ **Photo capture vertical slice** — upload face/skin/body/nails/hair → R2 (AES-256-GCM on sensitive; `0002` migration adds `enc_nonce`/`content_type`) → **ZDR Claude vision** observations (`app/vision.py`, `exclude_from_cloud_ai` respected) → `photo` TimelineEvent → thumbnail + observations on the timeline. Client downsamples to ≤2048px pre-upload. Routes: `POST /photos`, `GET /photos/{id}`, `GET /photos/{id}/image` (decrypt-on-read proxy). ⬜ ghost-overlay (prev_photo_id is stored, alignment UI later).
- ⬜ Withings webhook → `body_metrics` (worker job).
- ✅ **`api` deployed & live on Railway** (Docker) → https://api-production-507b.up.railway.app (`/docs`, `/health`, `/timeline`). `worker` deferred until its jobs exist.
- ✅ **Web PWA deployed & live** → https://web-production-168bf.up.railway.app (Caddy static + SPA fallback; CORS wired to the api). Full stack verified end-to-end in prod (capture → OpenRouter → timeline).

## Phase 3 — Rich Domains ⬜
Books + EPUB reader · wardrobe + outfits (nano-banana + rembg, R2) · gym (Nippard schema) · work-hours · supplements/meds · symptoms · weather+location.

## Phase 4 — AI Layer ⬜
Voice (ElevenLabs) → structured entry · photo feature-extraction · nightly insight engine (confidence-scored, causal-leaning). Begin LAZY embedding generation.

## Phase 5 — Analysis, Polish & Future-Ready ⬜
Dashboards/trends · doctor PDF reports · annual wrap-ups · semantic search (chat substrate) · one-click export · **(future, owner-gated)** conversational assistant, autonomous agents, proactive SMS/email.
