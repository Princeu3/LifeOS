# Research — Life-Tracking App Landscape

> Method: 14 Firecrawl searches + 7 full Reddit deep-reads (r/QuantifiedSelf, r/SkincareAddiction, r/capsulewardrobe, r/nailbiting, r/books, r/Hevy) + app-doc scrapes, 2026-06-13.

## Per-domain: standout + the one pattern to copy
- **Sleep** — AutoSleep/Oura. Passive capture; trust total-time + consistency, treat *stages* as soft (cross-device stage disagreement destroys trust).
- **Nutrition** — MacroFactor/Cronometer. **AI photo → editable ingredient breakdown** (not a static estimate); logging-speed obsession; DB accuracy is the universal complaint.
- **Skincare** — SkinSort/FeelinMySkin. **INCI ingredient lists + PAO/opened-date + "last used [active] N days ago" + conflict warnings + overlay product-usage vs breakout timeline.** No incumbent combines these → our wedge.
- **Body/progress photos** — TroveSkin/NailKeeper. **Fixed-pose ghost-overlay + auto-timeline + stitched compare**; tie each photo to that day's data.
- **Nails** — NailKeeper/LYFA. **Relapse-tolerant streaks + trigger logging** beat zero-reset counters; LYFA does real-time webcam bite-alerts (future).
- **Egestion** — Cara Care/Balloon. **True 7-type Bristol** (generic 1–5 is clinically useless) + **shareable PDF report**.
- **Gym** — Hevy. Reusable routines + rest timer + **PR celebration** + web entry + export/API. (Our PWA gets web-parity free.)
- **Wardrobe** — Whering/Acloset/OpenWardrobe. Bulk upload + AI bg-removal/categorize; **movable capsules**; **cost-per-wear + wear-count**; accessories first-class; **don't over-granulate color** ("15 greens" anti-pattern). #1 user fear = data lock-in → **one-click export**.
- **Color analysis** — Dressika. Lighting makes app results unreliable → standardize capture, present as confidence-scored suggestion, **link palette to wardrobe**.
- **Books** — StoryGraph. Granular rating + mood/pace tags + DNF + annual wrap-up + **filter-by-format**.
- **All-in-one/insights** — Exist.io/Bearable/Daylio. **Automatic cross-source correlations**; Bearable's custom factors; Daylio's 2-tap speed; **clean summary over deep data** (avoid Gyroscope clutter).

## Top gaps to win on
1. **Causal** (not Pearson-only) insight engine + NL query over own data — the most-wanted QS feature.
2. Radically low-friction logging (passive pull + AI photo→ingredients + 1-tap).
3. Skincare ingredient intelligence (conflicts + active-schedule + usage↔breakout overlay).
4. One-click full export (kills lock-in fear).
5. Shared fixed-pose photo engine across body/skin/nails.
6. Doctor-shareable PDF reports.
7. Relapse-tolerant habit streaks + trigger logging.

## Missing domains a thorough PO adds
Supplements/meds (timing), symptom/illness log, distinct stress/energy/focus, caffeine & alcohol fields, auto weather+location context, spend/cost-per-use across inventories, a single "today" capture surface.

## Cross-cutting truths
Logging friction = #1 churn. Trust is fragile (bad DBs, wrong stages, data loss → abandonment). **Cause-and-effect across domains is the dream nobody delivers** → unified schema + insight layer is the defensible wedge.
