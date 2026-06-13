import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .models import Domain, Source


class CaptureRequest(BaseModel):
    text: str | None = None  # freeform text / voice transcript
    occurred_at: datetime | None = None
    domain_hint: Domain | None = None  # optional; AI infers when absent
    source: Source = Source.manual
    media_keys: list[str] = []
    # Idempotency token travels in the `Idempotency-Key` HTTP header (Stripe/IETF style), not here.


class ParsedEntry(BaseModel):
    domain: Domain
    structured: dict  # filled only where confident
    summary: str
    confidence: float
    needs_confirmation: bool = False


class CaptureResponse(BaseModel):
    event_id: uuid.UUID
    parsed: ParsedEntry
    deduplicated: bool = False  # True when this client_token was already captured (replay)


class TimelineEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    occurred_at: datetime
    domain: Domain
    source: Source
    summary: str | None = None
    confidence: float | None = None
    structured: dict | None = None
    raw_input: str | None = None
    ref_table: str | None = None
    ref_id: uuid.UUID | None = None  # e.g. photos.id -> client builds /photos/{ref_id}/image
    media: list = []
    media_token: str | None = None  # short-lived per-photo token for the <img> src (?t=)


# --- auth (passkeys) ---


class RegisterOptionsIn(BaseModel):
    name: str | None = None


class RegisterVerifyIn(BaseModel):
    response: dict  # @simplewebauthn/browser RegistrationResponseJSON
    state: str
    name: str | None = None


class LoginVerifyIn(BaseModel):
    response: dict  # AuthenticationResponseJSON
    state: str


class RecoveryIn(BaseModel):
    code: str


class TimelineDetailOut(TimelineEntryOut):
    """A single event plus its normalized domain-table row (typed projection), if any."""

    logged_at: datetime | None = None
    domain_row: dict | None = None


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    photo_type: str
    sensitive: bool
    exclude_from_cloud_ai: bool
    analysis: dict | None = None
    ai_model: str | None = None
    ai_confidence: float | None = None
    notes: str | None = None
    event_id: uuid.UUID | None = None  # set on create
