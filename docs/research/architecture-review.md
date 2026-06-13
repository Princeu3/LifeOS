# Adversarial Architecture Review — LifeOS (2026-06-13)

> ~20 searches across Reddit, X, GitHub, Railway docs, Firecrawl. Goal: find what breaks it. Reconciled with owner decisions (bleeding-edge kept, OpenRouter accepted, full-scope phased, AI-metric/passkey flags deprioritized).

## CRITICAL
- **C1 — OpenRouter for body/medical data.** Practitioners: *"OpenRouter and privacy is an irreconcilable contradiction… for experimentation, not vulnerable data"* (r/LocalLLaMA 1n293h7). ZDR ≠ a BAA/DPA, and an aggregator can't sign one; downstream provider policies vary. Reliability: 3 outages/8mo, no SLA, 5.5% fee, returned bogus `401`s during failures, model-version drift (ofox.ai review 2026). → **Recommend sensitivity-split** (OpenRouter for non-sensitive; direct-provider-under-DPA or on-device for body/medical vision + symptom/supplement reasoning). DSPy makes it a config flag. **[OWNER DECISION]**
- **C2 — Scope vs solo-maintainer.** Base rate: nobody sustains a hand-built 12-domain tracker; survivors use SaaS or a spreadsheet (r/Fire 1m3a06r). Failure is at *maintenance* time, ×12 domains. → Build the spine + 3 domains end-to-end, live with them a quarter, then expand. (Owner wants full scope → this is the *delivery order*, not a cut.)

## HIGH
- **H1 — Procrastinate open bugs:** #1518 (jobs stuck in `doing`, no recovery), #1523 (worker dies on DB conn loss, fix reverted). → idempotent jobs + supervisor restart + stuck-job watchdog. ADOPTED.
- **H2 — LISTEN/NOTIFY unreliable** (*"can't use it to deliver jobs… only speed"* — Graphile Worker author). → polling is source of truth; NOTIFY is a latency hint only. ADOPTED.
- **H3 — Railway economics + buckets egress trap.** ~$35–50/mo for one user; idle + build minutes + backups billed; **Railway Buckets are NOT on the private network → every upload + backup is billed public egress ($0.10/GB)**, and **bucket access is suspended on a usage-cap overrun** (docs.railway.com/storage-buckets/billing). For a photo-heavy app this leaks cost and risks "photos go dark." → **Recommend media on Cloudflare R2 direct** (no egress fees; holds only our AES ciphertext), Postgres/compute stay on Railway. **[OWNER DECISION]**
- **H4 — AI body/skin "metrics."** Someone did exactly this on 40 photos; conclusion = hallucination + trend-fitting + *"DEXA would be better"* (r/MacroFactor 1t5gxms). → store as observation-with-provenance, relative trends only, island prompts, standing "not medical advice." ADOPTED.

## MEDIUM
- **M1 — Bleeding-edge frontend.** Rolldown has open dev-engine panics (#9730/#9728); combining React 19 + Rolldown + Tailwind v4 + Compiler = 4 young things where one peer conflict wedges the build. → keep React 19/Tailwind v4/Compiler but consider **stable Vite (Rollup), not rolldown-vite**, for v1 — cheapest build-blocker risk to retire. **[OWNER: keeping bleeding-edge — flagging Rolldown specifically.]**
- **M2 — Embed-now-query-later waste + re-embed on model upgrade** (tianpan.co index-drift; r/Rag "re-embedded 5M docs"). → lazy embeddings + `embedding_model_version` tag. ADOPTED.
- **M3 — Passkey single-device lockout, no recovery** (r/KrakenSupport 1lc7yp3). → 2 passkeys + recovery code. ADOPTED.
- **M4 — nano-banana churn** (*"Enshittification of Nano Banana"*, silent weight swaps, r/GeminiAI 1rs58vz). → deterministic `rembg` fallback; treat cutouts as best-effort. ADOPTED.

## Validated GOOD
`timeline_events` spine (best decision) · pgvector single store · Procrastinate-as-pattern · deferring chat to build substrate first · app-side AES + IndexedDB+Workbox capture · SQLAlchemy 2.0/Pydantic 2/uv/FastAPI (boring, stable).

## The one change the review would make
Sensitivity-split the AI path **and** put media on R2 — *"retires your only Critical privacy exposure and your worst cost leak in one move, costs nothing in features."* → the two owner decisions below.
