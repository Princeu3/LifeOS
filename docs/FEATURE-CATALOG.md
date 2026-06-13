# LifeOS — Feature Catalog

> Living doc. Domains + what's logged (structured-default / freeform), AI behavior, and research-backed refinements. ❓ = open/deferred.

## 1. Sleep
Bed/wake (→ duration), quality 1–5, awakenings, naps; freeform dreams/notes. Trusted primary = total time + consistency (sleep *stages* secondary — research: stage data is least reliable). Manual; optional Withings.

## 2. Nutrition & Hydration
Freeform "what I made" + optional photo → AI estimates macros (secondary, editable, not gospel — MacroFactor pattern). Meal type auto-by-time. **Caffeine & alcohol** tracked explicitly. Hydration quick-add. **No pantry inventory.** Supplements/meds fold in here.

## 3. Hygiene & Care
1-tap routine templates (AM/PM/shower/hair/body), each step → a product. **Phase-versioned routines** (actives ramp "low and slow"). **Product-interaction/conflict warnings** (skincare's top wishlist gap — e.g. minoxidil off face, watch active-stacking). Seeded from RevampPrince. No depletion tracking.

## 4. Body / Face / Hair / Nails (photos)
Standardized capture + **ghost-overlay alignment** (kills the "scroll camera roll to compare" pain). AI per type: skin (redness/blemish/oiliness/texture), hair (hairline/density), body (visual progress), nails. Body *numbers* from Withings. **Nail-biting:** relapse-tolerant streak (no zero-reset) + **trigger/context logging** (stress/boredom/time-of-day). Encrypted + app-locked albums. Baseline photos imported from RevampPrince.

## 5. Work Hours
WFH 9–5 M–F preset; Sat/Sun freeform; mid-day OOO toggle; scheduled vs actual.

## 6. Books & Reading
Library (Book → physical/ebook/audio editions); EPUB upload + epub.js reader; sessions w/ CFI+%/page; highlights + tags. **StoryGraph-grade:** granular rating, mood/pace tags, DNF, annual wrap-up, **filter-by-format**. ❓ AI book-chat deferred (reader3 pattern ready).

## 7. Wardrobe & Outfits
Items (clothes + **watches/shoes/accessories/socks first-class**): photo → Nano Banana cutout/normalize, library color extraction, vision-model categorization. Outfit builder; **cost-per-wear + wear-count headline stats**; **movable capsules** (Declutter/Packing); **color-palette ↔ wardrobe linkage** (% of closet in season; sane taxonomy, not "15 greens"). One-click export. ❓ Virtual try-on later (Gemini 3 Pro Image).

## 8. Medical — Egestion
**Bowel:** true 7-type Bristol + flags (color/straining/blood/pain). **Urination:** 8-level urine color scale + notes. One-tap link to what was eaten. **Doctor-shareable PDF report.**

## 9. Gym
Manual logging on a Program→Block→Week→Day→Exercise model (Nippard sheet): warm-up/working sets, rep range, per-set load+reps, early/last-set RPE, rest, 2 substitutions, demo link, coaching notes. Reusable routines, rest timer, **PR detection/celebration**, export.

## 10. Media (anytime)
Quick photo/video/voice capture → timeline. **Every photo auto-classified & routed** (face→skin, food→nutrition…). Voice memo → transcript → structured entry.

## 11. Mood / Energy / Stress  *(added — correlation glue)*
2-tap mood + energy + stress (1–5) + freeform journal. Distinct stress/energy axes (the trigger context for nail-biting & sleep insights).

## 12. Insights / Analysis  *(the payoff)*
Daily timeline; per-domain trends; nightly AI summary; **cross-domain, causal-leaning, confidence-scored insight cards**; clean executive summary over a deep hidden data layer; weekly/annual reports; doctor PDFs. **Natural-language query** over your own data = the headline once the (deferred) chat layer ships — substrate (embeddings) built now.

## Cross-cutting additions (validated by research)
Supplements & medication (timing/adherence) · symptom/illness log · auto **weather + daily location changelog** · caffeine/alcohol as dedicated fields · **one-click full export** (first-class) · generalized **habit/streak** engine.

## Sources
Grounded by: life-tracking landscape study (`research/landscape.md`), reader3/EPUB (`research/reader3-epub.md`), image pipeline + StyleOS (`research/gemini-image-pipeline.md`), Withings (`research/withings-api.md`).
