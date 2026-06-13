# Research — Image Pipeline (Gemini "Nano Banana") + StyleOS

## Nano Banana = `gemini-2.5-flash-image`
Generative image editor. **$0.039/image** (≤1024px = 1290 output tokens @ $30/1M). Siblings: `gemini-3-pro-image-preview` ("Nano Banana Pro", hi-fi/try-on), `gemini-3.1-flash-image`. Call: pass source image + text instruction to `generateContent`; image bytes return inline (`inlineData`/`part.as_image()`). Guard for `None` parts on safety refusal; `config={"response_modalities":["IMAGE","TEXT"]}` for image-only.

**Strengths:** white-studio normalization, mannequin/hanger removal, relighting, contact shadows — in one shot. **Limits:** *generative* → can hallucinate garment detail (buttons/print/trim); **no true alpha channel** (paints white, doesn't cut transparent PNG); non-deterministic; **every output carries non-removable SynthID watermark** → store `has_synthid=true`.

## Model-routing (the key takeaway — don't "Gemini-for-everything")
| Task | Tool | Why |
|---|---|---|
| Background removal / cutout | Segmentation lib (`@imgly/background-removal`/rembg) for fidelity+alpha; **Nano Banana** when you want full normalization | gen model alters detail + no alpha |
| **Dominant color (values)** | **Python `colorthief`/Pillow/extcolors** (NON-AI) | deterministic, free, reproducible |
| Semantic color naming | `gemini-2.5-flash` / Claude vision (JSON) | language task, cheap tokens |
| Garment categorization | `gemini-2.5-flash` vision + `Literal` enum schema | structured, cheap; NOT the gen model |
| Skin/body/nail metrics | **Claude Sonnet** vision (or Gemini Flash) + strict JSON | nuanced; keep human-in-loop, low-reliability, consent-gated |
| Virtual try-on (future) | `gemini-3-pro-image-preview` | fidelity to composite on a body |

## StyleOS (`Princeu3/StyleOSdev`, private, styleos.dev) — "AI Native OS for Fashion"
Stack: Bun + Turborepo; web React18/TS/Vite/Tailwind/shadcn/TanStack/Supabase-js; backend Python/FastAPI/Pydantic/**DSPy3**/google-genai/firecrawl/LangGraph/mem0/Neo4j/Phoenix; data Supabase(PG+RLS+pgvector)+Neo4j+Mem0; deploy Vercel+Railway+Supabase.

**Reusable patterns (lift, don't copy):** (1) **detect-then-generate gating** — classify bg first, only call Nano Banana if `needs_cleanup` (saves $/img); (2) DSPy `Signature` w/ `dspy.Image` + `Literal` enum outputs; (3) **enum lockstep** SQL CHECK ↔ DSPy Literal ↔ TS union; (4) SSRF-hardened server-side download+re-upload (dodges CORS); (5) content-addressed result cache; (6) per-user storage path `{user_id}/{item_id}/{file}` + signed URLs. **Diverge:** StyleOS uses AI for dominant color → replace with a library; StyleOS uses Supabase → we use Railway PG+buckets (privacy decision).

## Wardrobe data model (trimmed from StyleOS)
```sql
clothing_items(id, user_id, name,
  category CHECK in ('tops','bottoms','dresses','outerwear','shoes','accessories'),
  subcategory, brand,
  color_primary_hex, color_secondary_hex,   -- from colorthief (deterministic)
  color_names text[],                        -- from vision model (semantic)
  pattern, material, season text[], occasions text[], style_tags text[], size,
  original_image_url, cutout_image_url, has_synthid bool,
  ai_attributes jsonb, ai_model, ai_confidence real,
  wear_count int, last_worn date, favorite bool, purchase_price numeric, currency, notes,
  created_at, updated_at)
outfits(id, user_id, name, occasion, season text[], weather_temp_range int[2],
  rating 1-5, times_worn, notes, tryon_image_url, created_at)
outfit_items(outfit_id fk cascade, item_id fk cascade, primary key(outfit_id,item_id))
user_body_photos(id, user_id, image_url, photo_type CHECK('full_body','upper_body'),
  is_primary, body_metrics jsonb /*minimal, consent-gated*/, created_at)
```
Deltas: store BOTH `color_primary_hex` (library) and `color_names[]` (vision); keep `original`/`cutout` URLs separate; stamp `ai_model`/`ai_confidence` so analysis is swappable from generation. Extend categories to watches/socks as first-class.

Sources: ai.google.dev image-generation + pricing; Google "Introducing Gemini 2.5 Flash Image"; `@google/genai` via Context7.
