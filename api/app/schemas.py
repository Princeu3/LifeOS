import uuid
from datetime import datetime

from pydantic import BaseModel

from .models import Domain, Source


class CaptureRequest(BaseModel):
    text: str | None = None  # freeform text / voice transcript
    occurred_at: datetime | None = None
    domain_hint: Domain | None = None  # optional; AI infers when absent
    source: Source = Source.manual
    media_keys: list[str] = []


class ParsedEntry(BaseModel):
    domain: Domain
    structured: dict  # filled only where confident
    summary: str
    confidence: float
    needs_confirmation: bool = False


class CaptureResponse(BaseModel):
    event_id: uuid.UUID
    parsed: ParsedEntry
