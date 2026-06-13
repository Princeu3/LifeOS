"""LifeOS worker — Procrastinate (Postgres-backed, NO Redis).

Setup:  procrastinate --app=worker.app schema --apply
Run:    procrastinate --app=worker.app worker

Resilience (per architecture review): jobs are IDEMPOTENT; polling is the source of truth
(LISTEN/NOTIFY is only a latency hint); a watchdog should alert when a job sits in `doing`
past a threshold; Railway restart policy recovers the worker on DB-blip crashes
(Procrastinate #1518/#1523). Jobs are enqueued transactionally from the API.
"""

from __future__ import annotations

import os

from procrastinate import App, PsycopgConnector

app = App(connector=PsycopgConnector(conninfo=os.environ.get("PROCRASTINATE_DSN", "")))


@app.task(queue="withings")
async def withings_sync(last_update: int | None = None) -> int:
    # TODO(Phase 2): rotate+persist refresh token, then getmeas meastype=1,5,6,8,11,76,77,88.
    # Idempotent upsert keyed on (measured_at, type). See docs/research/withings-api.md.
    return 0


@app.task(queue="vision")
async def analyze_photo(photo_id: str) -> None:
    # TODO(Phase 4): WARDROBE -> detect-then-generate cutout (nano-banana, with rembg fallback) + tag.
    # SENSITIVE body/medical -> Claude vision via OpenRouter ZDR only; honor exclude_from_cloud_ai.
    # Store outputs as observations (model id + confidence + prompt version) — never absolute metrics.
    ...


@app.task(queue="insights", queueing_lock="nightly_insights")
async def nightly_insights() -> None:
    # TODO(Phase 4): lagged cross-domain stats (BH-FDR, min sample) -> Claude confidence-scored cards.
    ...


@app.periodic(cron="0 3 * * *")
@app.task(queueing_lock="nightly_insights_cron")
async def scheduled_nightly(timestamp: int) -> None:
    await nightly_insights.defer_async()
