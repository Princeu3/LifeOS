"""Timeline read API — the unified daily view over all domains."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

router = APIRouter(prefix="/timeline", tags=["timeline"])

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
async def timeline(limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[TimelineEvent]:
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.user_id == OWNER_ID)
        .order_by(TimelineEvent.occurred_at.desc())
        .limit(min(limit, 500))
    )
    return list(result.scalars().all())


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
    return detail
