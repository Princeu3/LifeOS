# LifeOS — Phase Roadmap

> Tracking doc. ⬜ not started · 🔄 in progress · ✅ done.

## Phase 0 — Discovery & Grounding ✅
Decisions, full feature catalog, and grounding (reader3/EPUB, landscape, Withings, image pipeline, gym sheet, RevampPrince seed) — see `DECISIONS.md`, `FEATURE-CATALOG.md`, `research/`.

## Phase 1 — Product & Architecture Spec ✅
`ARCHITECTURE.md` (data model, AI routing, privacy), `CLAUDE.md`, stack grounded & pinned (`research/stack-grounding.md`), adversarial review (`research/architecture-review.md`).

## Phase 2 — Foundation / MVP 🔄
- ✅ Stack & architecture locked; adversarial review folded in.
- ✅ Scaffold regenerated to final stack: async SQLAlchemy + psycopg3, Procrastinate worker, R2 + AES storage module, OpenRouter config, uv multi-stage Dockerfile, pinned React 19.2/Vite 8/Tailwind v4.
- ⬜ Provision Railway (PG18+pgvector, api, worker) + Cloudflare R2 bucket — **needs R2 creds; greenlight to provision (incurs cost).**
- ⬜ Alembic initial migration (timeline_events + domain tables) + pgvector extension.
- ⬜ Passkey auth (2 passkeys + recovery code).
- ⬜ Wire capture → DSPy/OpenRouter parsing (structured-default-else-freeform); persist into domain tables.
- ⬜ Build first domains end-to-end: **sleep · nutrition(+caffeine/alcohol) · mood · egestion · care (RevampPrince-seeded)** + the daily timeline UI.
- ⬜ Photo capture → R2 (AES on sensitive) + ghost-overlay; import RevampPrince baseline photos.
- ⬜ Withings webhook → `body_metrics`.

## Phase 3 — Rich Domains ⬜
Books + EPUB reader · wardrobe + outfits (nano-banana + rembg fallback, R2) · gym (Nippard schema) · work-hours · supplements/meds · symptoms · weather+location.

## Phase 4 — AI Layer ⬜
Voice (ElevenLabs) → structured entry · photo feature-extraction · nightly insight engine (confidence-scored, causal-leaning). Begin LAZY embedding generation.

## Phase 5 — Analysis, Polish & Future-Ready ⬜
Dashboards/trends · doctor PDF reports · annual wrap-ups · semantic search (chat substrate) · one-click export · **(future, owner-gated)** conversational assistant, autonomous agents, proactive SMS/email.
