"""LifeOS worker — Procrastinate (Postgres-backed, NO Redis).

Setup:  procrastinate --app=worker.app schema --apply   (errors if already applied -> guard with `|| true`)
Run:    procrastinate --app=worker.app worker

Resilience (per architecture review): jobs are IDEMPOTENT; polling is the source of truth
(LISTEN/NOTIFY is only a latency hint); Railway restart policy recovers the worker on DB-blip
crashes. Jobs are deferred from the API (app/procrastinate_app.py) by name.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import psycopg
from procrastinate import App, PsycopgConnector

import withings as wi

OWNER_ID = "00000000-0000-0000-0000-000000000001"


def _dsn() -> str:
    dsn = os.environ.get("PROCRASTINATE_DSN") or os.environ.get("DATABASE_URL", "")
    return dsn.replace("postgresql+psycopg://", "postgresql://")  # libpq form for raw psycopg


app = App(connector=PsycopgConnector(conninfo=_dsn()))

_UPSERT = """
INSERT INTO body_metrics
  (id, grpid, measured_at, weight_kg, fat_pct, fat_mass_kg, lean_mass_kg,
   muscle_mass_kg, body_water_kg, bone_mass_kg, heart_rate, source)
VALUES (gen_random_uuid(), %(grpid)s, %(measured_at)s, %(weight_kg)s, %(fat_pct)s, %(fat_mass_kg)s,
        %(lean_mass_kg)s, %(muscle_mass_kg)s, %(body_water_kg)s, %(bone_mass_kg)s, %(heart_rate)s, 'withings')
ON CONFLICT (grpid) DO UPDATE SET
  measured_at=EXCLUDED.measured_at, weight_kg=EXCLUDED.weight_kg, fat_pct=EXCLUDED.fat_pct,
  fat_mass_kg=EXCLUDED.fat_mass_kg, lean_mass_kg=EXCLUDED.lean_mass_kg,
  muscle_mass_kg=EXCLUDED.muscle_mass_kg, body_water_kg=EXCLUDED.body_water_kg,
  bone_mass_kg=EXCLUDED.bone_mass_kg, heart_rate=EXCLUDED.heart_rate
RETURNING id, (xmax = 0) AS inserted
"""

_TIMELINE = """
INSERT INTO timeline_events
  (id, user_id, occurred_at, domain, ref_table, ref_id, source, summary, structured)
VALUES (gen_random_uuid(), %(user_id)s, %(occurred_at)s, 'body_metric', 'body_metrics', %(ref_id)s,
        'withings', %(summary)s, %(structured)s::jsonb)
"""

_COLS = (
    "weight_kg", "fat_pct", "fat_mass_kg", "lean_mass_kg",
    "muscle_mass_kg", "body_water_kg", "bone_mass_kg", "heart_rate",
)


def _summary(vals: dict) -> str:
    bits = []
    if "weight_kg" in vals:
        bits.append(f"{vals['weight_kg']} kg")
    if "fat_pct" in vals:
        bits.append(f"{vals['fat_pct']}% fat")
    if "muscle_mass_kg" in vals:
        bits.append(f"{vals['muscle_mass_kg']} kg muscle")
    return "Body · " + " · ".join(bits) if bits else "Body metrics"


@app.task(queue="withings", name="withings_sync")
async def withings_sync(startdate: int | None = None, enddate: int | None = None) -> int:
    """Refresh token if needed, getmeas since last sync, idempotently upsert body_metrics + events."""
    async with await psycopg.AsyncConnection.connect(_dsn()) as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id, access_token, refresh_token, expires_at, last_sync_at "
                "FROM withings_account LIMIT 1"
            )
            acct = await cur.fetchone()
            if not acct:
                return 0  # not connected
            acct_id, access_token, refresh_token, expires_at, last_sync_at = acct

            # Refresh if the access token is expired (or within 60s of it); persist rotated tokens.
            if expires_at <= datetime.now(timezone.utc) + timedelta(seconds=60):
                body = await wi.refresh(refresh_token)
                access_token = body["access_token"]
                new_expiry = datetime.now(timezone.utc) + timedelta(
                    seconds=int(body.get("expires_in", 10800))
                )
                await cur.execute(
                    "UPDATE withings_account SET access_token=%s, refresh_token=%s, expires_at=%s, "
                    "updated_at=now() WHERE id=%s",
                    (access_token, body["refresh_token"], new_expiry, acct_id),
                )

            # Always backfill via lastupdate (missed notifications are not redelivered).
            lastupdate = (
                int(last_sync_at.timestamp())
                if last_sync_at
                else int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp())
            )
            groups = await wi.getmeas(access_token, lastupdate)

            new_count, max_ts = 0, last_sync_at
            for grp in groups:
                vals = wi.parse_group(grp)
                if not vals:
                    continue
                measured_at = datetime.fromtimestamp(grp["date"], tz=timezone.utc)
                params = {"grpid": grp["grpid"], "measured_at": measured_at,
                          **{c: None for c in _COLS}, **vals}
                await cur.execute(_UPSERT, params)
                row_id, inserted = await cur.fetchone()
                if inserted:
                    new_count += 1
                    await cur.execute(_TIMELINE, {
                        "user_id": OWNER_ID, "occurred_at": measured_at, "ref_id": row_id,
                        "summary": _summary(vals), "structured": json.dumps(vals),
                    })
                if max_ts is None or measured_at > max_ts:
                    max_ts = measured_at

            if max_ts:
                await cur.execute(
                    "UPDATE withings_account SET last_sync_at=%s, updated_at=now() WHERE id=%s",
                    (max_ts, acct_id),
                )
        await conn.commit()
    return new_count


@app.task(queue="vision", name="analyze_photo")
async def analyze_photo(photo_id: str) -> None:
    # TODO(Phase 4): WARDROBE -> nano-banana cutout (rembg fallback); SENSITIVE -> ZDR Claude vision.
    ...


@app.task(queue="insights", name="nightly_insights", queueing_lock="nightly_insights")
async def nightly_insights() -> None:
    # TODO(Phase 4): lagged cross-domain stats (BH-FDR, min sample) -> Claude confidence-scored cards.
    ...


@app.periodic(cron="0 3 * * *")
@app.task(queueing_lock="nightly_insights_cron", name="scheduled_nightly")
async def scheduled_nightly(timestamp: int) -> None:
    await nightly_insights.defer_async()
