"""Capture vertical slice: freeform in -> timeline event out. Raw input is always persisted.

AI structuring is stubbed (see app/ai.py). Phase 2/4 will persist parsed.structured into the domain
table (ref_table/ref_id), enqueue the embedding job (LAZY — deferred to the chat phase), and run the
vision pipeline for photo entries.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai import parse_capture
from ..db import get_db
from ..models import TimelineEvent
from ..schemas import CaptureRequest, CaptureResponse

router = APIRouter(prefix="/capture", tags=["capture"])

# Single-user app: fixed owner id until passkey auth lands.
OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post("", response_model=CaptureResponse)
async def capture(req: CaptureRequest, db: AsyncSession = Depends(get_db)) -> CaptureResponse:
    parsed = parse_capture(req.text or "", req.domain_hint)
    event = TimelineEvent(
        user_id=OWNER_ID,
        occurred_at=req.occurred_at or datetime.now(timezone.utc),
        domain=parsed.domain,
        source=req.source,
        raw_input=req.text,  # ALWAYS retained
        summary=parsed.summary,
        media=[{"bucket_key": k} for k in req.media_keys],
        confidence=parsed.confidence,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return CaptureResponse(event_id=event.id, parsed=parsed)
