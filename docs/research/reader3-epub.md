# Research — Books Module / EPUB Reader

## reader3 (owner's repo)
`Princeu3/reader3` = fork of **karpathy/reader3**: tiny FastAPI + `ebooklib` + BeautifulSoup app, "EPUB reader with AI chat." **Reusable:** the EPUB ingestion recipe (DC metadata, spine ordering, robust TOC parse w/ fallback, image extraction + `<img>` rewrite, HTML sanitization, plain-text extraction for AI/search) + upload-then-process endpoint pattern. **Don't carry over:** pickle storage, chapter-at-a-time scroll, and its total lack of position tracking/highlights — exactly the gaps we fill.

## Reader engine — recommended: **epub.js via react-reader**
Mature reflowable rendering + built-in **CFI + locations + annotations** + a maintained React wrapper. (foliate-js is technically superior for multi-format MOBI/PDF but unstable/no-release — only if multi-format becomes a hard requirement; epub.ts is a TS drop-in to watch.)

## Position tracking (reflowable EPUBs have no fixed pages)
1. **CFI = source of truth** — store `location.start.cfi` on each `relocated`; restore via `rendition.display(cfi)`.
2. **% progress** — `book.locations.generate()` once (cache the JSON in `editions.locations_json`), then `percentageFromCfi()`.
3. **Page numbers** — only honest if the EPUB ships a `page-list` (print-page map); else show per-chapter pages or %-derived. Set expectations to %-progress.
4. **Physical books** — separate edition `format='physical'` with `total_pages`; manual page entry; same `reading_sessions`.

## Data model
`books` (work-level: title, authors[], isbn, cover, subjects) → `editions` (format ebook_epub|physical|audio; epub_file_key, locations_json, page_list_json, total_pages) → `reading_sessions` (start/end cfi or page, %, duration) · `highlights` (cfi_range, text, color, note) · `tags` (book-level, m2m). Whole-book progress = latest session %. One Book can hold both physical + ebook editions → clean **hardcopy→softcopy migration**.

## Risks
epub.js stale *release* tag (pin + wrap via react-reader); CFI fragile across engine versions (keep % + chapterIndex as durable backups); **EPUBs can carry JS → mandatory strict CSP** + sanitize on ingest; `locations.generate()` is CPU-heavy → cache; pickle/disk won't scale → use DB + bucket.
