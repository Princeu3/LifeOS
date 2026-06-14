"""Capture vertical slice: freeform in -> timeline event (+ normalized domain row) out.

Raw input is always persisted. An optional `client_token` makes capture idempotent: the offline
PWA queue generates one token per queued log and reuses it on every sync retry, so a POST that
succeeds server-side but times out before the client marks it synced won't create a duplicate.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai import parse_capture
from ..auth import require_auth
from ..db import get_db
from ..models import TimelineEvent
from ..normalize import flatten, normalize
from ..schemas import CaptureRequest, CaptureResponse, ParsedEntry

router = APIRouter(prefix="/capture", tags=["capture"], dependencies=[Depends(require_auth)])

# Single-user app: fixed owner id until passkey auth lands.
OWNER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _parsed_from_event(ev: TimelineEvent) -> ParsedEntry:
    """Reconstruct the parse from a stored event (for idempotent replays — no re-parse)."""
    conf = ev.confidence if ev.confidence is not None else 0.0
    return ParsedEntry(
        domain=ev.domain,
        structured=ev.structured or {},
        summary=ev.summary or "",
        confidence=conf,
        needs_confirmation=conf < 0.6,
    )


async def _find_by_token(db: AsyncSession, token: str) -> TimelineEvent | None:
    return (
        await db.execute(
            select(TimelineEvent).where(
                TimelineEvent.user_id == OWNER_ID,
                TimelineEvent.client_token == token,
            )
        )
    ).scalar_one_or_none()


@router.post("", response_model=CaptureResponse)
async def capture(
    req: CaptureRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
) -> CaptureResponse:
    # Fast path: this token was already captured -> return the existing event, skip the LLM.
    if idempotency_key:
        existing = await _find_by_token(db, idempotency_key)
        if existing:
            return CaptureResponse(
                event_id=existing.id, parsed=_parsed_from_event(existing), deduplicated=True
            )

    parsed = parse_capture(req.text or "", req.domain_hint)
    # Flatten any LLM domain-wrapper nesting before storing, so the event's structured is clean for
    # the UI and future search (the raw text is always retained in raw_input).
    structured = flatten(parsed.domain, parsed.structured)
    event = TimelineEvent(
        user_id=OWNER_ID,
        client_token=idempotency_key,
        occurred_at=req.occurred_at or datetime.now(timezone.utc),
        domain=parsed.domain,
        source=req.source,
        raw_input=req.text,  # ALWAYS retained
        summary=parsed.summary,
        structured=structured,  # flattened parse kept on the event
        media=[{"bucket_key": k} for k in req.media_keys],
        confidence=parsed.confidence,
    )
    try:
        db.add(event)
        # Project the parse into a typed domain row and back-link it (timeline-spine ref_table/ref_id).
        norm = normalize(parsed.domain, structured)
        if norm:
            ref_table, row = norm
            db.add(row)
            await db.flush()  # assign row.id + event.id (also surfaces a token clash here)
            event.ref_table = ref_table
            event.ref_id = row.id
        await db.commit()
    except IntegrityError:
        # A concurrent retry with the same token won the race — return the stored event.
        await db.rollback()
        if idempotency_key and (existing := await _find_by_token(db, idempotency_key)):
            return CaptureResponse(
                event_id=existing.id, parsed=_parsed_from_event(existing), deduplicated=True
            )
        raise

    await db.refresh(event)
    return CaptureResponse(event_id=event.id, parsed=parsed, deduplicated=False)
