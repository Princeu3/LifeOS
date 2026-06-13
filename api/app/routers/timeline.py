"""Timeline read API — the unified daily view over all domains."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import TimelineEvent
from ..schemas import TimelineEntryOut

router = APIRouter(prefix="/timeline", tags=["timeline"])

# Single-user app: fixed owner id until passkey auth lands.
OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.get("", response_model=list[TimelineEntryOut])
async def timeline(limit: int = 100, db: AsyncSession = Depends(get_db)) -> list[TimelineEvent]:
    result = await db.execute(
        select(TimelineEvent)
        .where(TimelineEvent.user_id == OWNER_ID)
        .order_by(TimelineEvent.occurred_at.desc())
        .limit(min(limit, 500))
    )
    return list(result.scalars().all())
