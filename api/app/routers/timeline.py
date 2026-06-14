"""Timeline read API — the unified daily view over all domains."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import storage
from ..auth import make_media_token, require_auth
from ..config import settings
from ..db import get_db
from ..models import (
    BristolLog,
    CareRoutineRun,
    FoodLog,
    MoodLog,
    Photo,
    SleepLog,
    TimelineEvent,
    UrineLog,
)
from ..schemas import TimelineDetailOut, TimelineEntryOut

router = APIRouter(prefix="/timeline", tags=["timeline"], dependencies=[Depends(require_auth)])

# Single-user app: fixed owner id until passkey auth lands.
OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# ref_table -> ORM model, so the detail endpoint can hydrate the normalized row.
_TABLE_MODEL = {
    "sleep_logs": SleepLog,
    "food_logs": FoodLog,
    "mood_logs": MoodLog,
    "bristol_logs": BristolLog,
    "urine_logs": UrineLog,
    "care_routine_runs": CareRoutineRun,
    "photos": Photo,
}


@router.get("", response_model=list[TimelineEntryOut])
async def timeline(limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[TimelineEntryOut]:
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.user_id == OWNER_ID)
        .order_by(TimelineEvent.occurred_at.desc())
        .limit(min(limit, 500))
    )
    out: list[TimelineEntryOut] = []
    for e in result.scalars().all():
        entry = TimelineEntryOut.model_validate(e)
        if e.ref_table == "photos" and e.ref_id:
            entry.media_token = make_media_token(e.ref_id)  # short-lived <img> token
        out.append(entry)
    return out


@router.get("/{event_id}", response_model=TimelineDetailOut)
async def timeline_detail(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> TimelineDetailOut:
    event = await db.get(TimelineEvent, event_id)
    if not event or event.user_id != OWNER_ID:
        raise HTTPException(404, "event not found")
    domain_row = None
    model = _TABLE_MODEL.get(event.ref_table or "")
    if model and event.ref_id:
        row = await db.get(model, event.ref_id)
        if row is not None:
            # FastAPI's jsonable_encoder serializes datetime/uuid values in the dict.
            domain_row = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    detail = TimelineDetailOut.model_validate(event)
    detail.domain_row = domain_row
    if event.ref_table == "photos" and event.ref_id:
        detail.media_token = make_media_token(event.ref_id)
    return detail


@router.delete("/{event_id}")
async def delete_event(
    event_id: uuid.UUID,
    _: uuid.UUID = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Delete an event + its normalized domain row (and the R2 object for photos)."""
    event = await db.get(TimelineEvent, event_id)
    if not event or event.user_id != OWNER_ID:
        raise HTTPException(404, "event not found")
    model = _TABLE_MODEL.get(event.ref_table or "")
    if model and event.ref_id:
        row = await db.get(model, event.ref_id)
        if row is not None:
            if event.ref_table == "photos" and getattr(row, "bucket_key", None):
                try:
                    await run_in_threadpool(
                        storage._s3.delete_object, Bucket=settings.s3_bucket, Key=row.bucket_key
                    )
                except Exception:  # noqa: BLE001 — orphaned object is acceptable; still delete the row
                    pass
            await db.delete(row)
    await db.delete(event)
    await db.commit()
    return {"deleted": True}
