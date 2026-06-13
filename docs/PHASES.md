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
- 🔄 Per-domain endpoints + normalize `structured` into domain tables (sleep · nutrition · mood · egestion · care).
- ⬜ Timeline **read API** + daily **timeline UI** + capture screen wired to the live API.
- ⬜ Passkey auth (2 passkeys + recovery code).
- ⬜ Seed care products/routines from RevampPrince (local-only seed).
- ⬜ Photo capture → R2 (AES on sensitive) + ghost-overlay.
- ⬜ Withings webhook → `body_metrics` (worker job).
- ⬜ Deploy `api` + `worker` services to Railway.

## Phase 3 — Rich Domains ⬜
Books + EPUB reader · wardrobe + outfits (nano-banana + rembg, R2) · gym (Nippard schema) · work-hours · supplements/meds · symptoms · weather+location.

## Phase 4 — AI Layer ⬜
Voice (ElevenLabs) → structured entry · photo feature-extraction · nightly insight engine (confidence-scored, causal-leaning). Begin LAZY embedding generation.

## Phase 5 — Analysis, Polish & Future-Ready ⬜
Dashboards/trends · doctor PDF reports · annual wrap-ups · semantic search (chat substrate) · one-click export · **(future, owner-gated)** conversational assistant, autonomous agents, proactive SMS/email.
