# LifeOS

**An open-source, self-hosted, AI-native operating system for your body and day.**

LifeOS records the things most apps scatter across a dozen silos — sleep, food, skincare & haircare, body/face/nail progress photos, gym, wardrobe, books, mood, supplements, egestion, and more — onto **one unified timeline**, then uses AI to surface the cross-domain cause-and-effect that fragmented trackers can't.

> **Why another tracker?** Because no app connects *what you eat / how you sleep / which products you use* to *how your skin, gut, body, and mood actually respond.* LifeOS is built around that missing link — and it's **yours**: self-hosted, your data, your keys.

![status](https://img.shields.io/badge/status-building%20in%20public-orange)
![license](https://img.shields.io/badge/license-MIT-blue)
![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)
![PWA](https://img.shields.io/badge/PWA-React%2019-61dafb)
![backend](https://img.shields.io/badge/backend-FastAPI%20%2B%20DSPy-009688)

> ⚠️ **Early & building in public.** The architecture, decisions, and scaffold are in place; the domains are being built out. ⭐ Star/watch to follow along.
>
> 🔴 **Live API:** [`api-production-507b.up.railway.app/docs`](https://api-production-507b.up.railway.app/docs) — try `/health`, `/timeline`, and the interactive docs.

## ✨ What it tracks
- 😴 **Sleep** · 🍳 **Nutrition & hydration** (+ caffeine/alcohol) · 🚿 **Skincare / hair / body care** with product + routine tracking and ingredient-conflict awareness
- 📸 **Face / skin / hair / nail** progress photos (alignment overlays) · ✋ nail-biting & habit tracking
- 🚽 **Egestion** (Bristol + urine scales) with doctor-shareable reports · 🏋️ **Gym** · 👕 **Wardrobe & outfits** · 📚 **Books** (in-browser EPUB reader)
- 🧠 **Mood / energy / stress** · 💊 **Supplements & meds** · 🌦️ auto **weather + location** context
- 📈 a daily **timeline** + cross-domain **insights** — built to be honest: confidence-scored, never overclaiming, never medical advice

## 🧱 Architecture at a glance
- **Timeline-spine data model** — an append-only event log over normalized per-domain tables, so every domain shares one searchable, embeddable history.
- **Web-first PWA** — React 19 + Vite + Tailwind v4 with an offline-first capture queue (log anywhere, sync later).
- **Python backend** — FastAPI + **DSPy**, async SQLAlchemy on **PostgreSQL + pgvector** (one datastore), **Procrastinate** for background jobs (no Redis).
- **AI-native, model-routed** — all LLMs via **OpenRouter** (Claude + Gemini), **Voyage** embeddings, **ElevenLabs** voice; image cutouts via Gemini "nano banana"; deterministic libraries for color.
- **Private by construction** — self-hosted on Railway + Cloudflare R2, **app-side AES-256** on sensitive media, zero-retention AI routing, one-click full export.

📖 Full design in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), the decision log in [`docs/DECISIONS.md`](docs/DECISIONS.md), and the grounded research behind every choice in [`docs/research/`](docs/research).

## 🚀 Getting started (dev)
```bash
# backend (needs PostgreSQL with the `vector` extension)
cd api && cp .env.example .env      # fill in your keys
uv sync && uv run alembic upgrade head && uv run fastapi dev app/main.py

# frontend
cd web && pnpm install && pnpm dev
```
Integration setup guides: [Cloudflare R2](docs/research/cloudflare-r2-setup.md) · [Withings](docs/research/withings-api.md).

## 🗺️ Roadmap
Phased build — see [`docs/PHASES.md`](docs/PHASES.md). **Now:** foundation + first domains (sleep · nutrition · mood · egestion · care) + the timeline. **Next:** books, wardrobe, gym, the photo + insight pipelines.

## 🤝 Contributing
Early days — issues, ideas, and PRs are welcome. Start with [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`CLAUDE.md`](CLAUDE.md).

## 🔐 Privacy
Single-user and self-hosted: your data lives in *your* Postgres and *your* object storage. Sensitive media is encrypted with a key only you hold. No analytics, no third-party data sale.

## 📄 License
[MIT](LICENSE) © 2026 Prince Upadhyay
