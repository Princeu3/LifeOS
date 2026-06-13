# LifeOS — Locked Decisions

> Single source of truth for product/architecture decisions. Last updated: 2026-06-13.
> Status legend: ✅ locked · 🔬 pending research verdict.

## Foundational

| Area | Decision |
|---|---|
| **Form factor** | ✅ Web-first **PWA** — installable on phone home-screen, full camera access for capture, works on phone + desktop from one codebase. |
| **Scope** | ✅ **Single-user** (Prince). No multi-tenant complexity. |
| **Hosting / Privacy** | ✅ **Self-hosted on Railway** — own DB + encrypted object storage for sensitive media (body/medical photos). Owner controls the data. |
| **Project name** | ✅ **LifeOS** |

## AI posture (from owner point 16)

- ✅ **Build the AI-native data substrate now, defer the conversational/agentic layer.**
- Capture every entry as **structured data + retained raw media + embedding-ready text** on an **event-sourced timeline**, so insights / chat / autonomous agents can switch on later **without re-modeling**.
- **In from the start:** frictionless capture (voice/text → structured), **photo analysis** (every photo auto-classified, routed, and feature-extracted), **lightweight insights/correlations**.
- **Deferred (architected-for, not built):** conversational chatbot, autonomous agents, proactive notifications (future: SMS/email).

## Per-domain decisions

| Domain | Decision |
|---|---|
| **Body composition** | ✅ **Withings auto-sync** — feasibility verdict = **EASY** (no approval gate, free, demo user). Pull `meastype 1,5,6,8,11,76,77,88` (weight, lean, fat %, fat kg, HR, muscle, water, bone) via **Notify webhook `appli=1`** on Railway. Gotcha = HMAC signature/nonce on auth endpoints + refresh-token rotation → use a Withings-aware lib + persist rotating token. Manual entry stays as fallback. Details: `research/withings-api.md`. |
| **Sleep / Steps / Activity** | Manual by default. Since Withings is wired anyway, **sleep + steps are an optional one-toggle bonus** (scope `user.activity`) — owner's call, **off by default**. |
| **Nutrition** | Freeform "what I made" + optional photo → **AI estimates macros/calories** (secondary, not gospel). **Track caffeine & alcohol.** **No pantry/ingredient inventory** — AI derives ingredients from description/photo; owner maintains nothing. |
| **Care routines** | **1-tap routine templates** (AM/PM/shower/hair/body). **No depletion/repurchase tracking.** **Seed from RevampPrince.** Products carry INCI/role for skin-correlation; zero inventory overhead. Routines are **phase-versioned over time** (actives ramp "low and slow"). A **product-interaction/conflict rules** engine surfaces warnings (e.g., keep minoxidil off face). |
| **Body/Face/Hair/Nails photos** | Face daily-optional, body/hair weekly, nails on-demand. **Ghost-overlay alignment.** **Encrypted + app-locked** sensitive albums. Nail-biting = **relapse-tolerant streak + trigger logging.** Seed photo timeline from existing RevampPrince baseline photos. |
| **Work hours** | **Fully WFH, 9–5, M–F**; Sat/Sun freeform; mid-day out-of-office toggle. |
| **Books** | Library + EPUB upload + in-browser reader + sessions/highlights/tags + StoryGraph-style ratings/mood-pace/DNF/annual wrap-up + filter-by-format. **No AI book-chat yet** (architected for later; reader3 has the pattern). |
| **Wardrobe** | 🔬 **Gemini "nano banana" (2.5 Flash Image)** for image work (bg-removal + tagging) — model routing being confirmed. Watches/shoes/accessories/socks **first-class**. Cost-per-wear, wear counts, movable capsules, color↔palette linkage (sane taxonomy, not "15 greens"). One-click full export. Reference **StyleOS** repo selectively. |
| **Egestion** | **Bowel** (true 7-type Bristol + flags: blood/pain/straining) **+ urination** (urine **color scale** + notes). **Doctor-shareable PDF export.** |
| **Gym** | **Manual logging.** Data model modeled on Jeff Nippard *Bodybuilding Transformation System* sheet: Program → Block → Week → Day(focus) → Exercise (warm-up sets, working sets, rep range, per-set load+reps ×4, early/last-set RPE, rest, 2 substitutions, demo link, notes). PR detection/celebration; export/API. |
| **Media** | Every photo auto-classified & routed; quick-capture surface; voice memo → transcript → structured entry. |
| **Mood / Energy / Stress** | Quick daily check-in + freeform journal. |
| **Supplements & Meds** | Inventory + intake logging, folded into the food/drink flow (timing/adherence). |
| **Weather + Location** | **Auto weather API** + **daily location capture with a location changelog/history.** |
| **Symptoms** | Symptom/illness log feeding correlations. |

## Research-backed design principles (from landscape study)

1. **Logging friction is the #1 churn driver** — minimize taps, prefer passive/AI capture, make derived lists editable, never re-enter.
2. **Causal, not just correlational** — lean toward causal methods; **confidence-scored, uncertainty-aware** insight cards; never overclaim.
3. **Trust is fragile** — be conservative with claims, show confidence, **never lose data** (one-click full export is a first-class feature).
4. **Cause-and-effect across domains is the wedge** — unified schema + cross-domain overlays (product usage vs. skin photos; food vs. egestion/mood) is what fragmented incumbents can't do.
