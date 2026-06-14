"""SQLAlchemy 2.0 models.

The `timeline_events` table is the append-only spine that unifies every domain for the timeline,
semantic search, and embeddings. Each event keeps the parsed `structured` payload (JSONB) and the
raw input; normalized per-domain tables hold richer structured data and are referenced via
(ref_table, ref_id). Every domain table keeps a freeform `notes` field — "structured default,
freeform fallback". Enums must stay in lockstep with the generated TS types.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Enum, Float, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Domain(str, enum.Enum):
    sleep = "sleep"
    nutrition = "nutrition"
    hydration = "hydration"
    care = "care"
    photo = "photo"
    body_metric = "body_metric"
    work = "work"
    book = "book"
    wardrobe = "wardrobe"
    egestion = "egestion"
    gym = "gym"
    mood = "mood"
    symptom = "symptom"
    supplement = "supplement"
    media = "media"
    location = "location"


class Source(str, enum.Enum):
    manual = "manual"
    voice = "voice"
    photo = "photo"
    withings = "withings"
    auto = "auto"


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    # Idempotency: a capture may carry a client-generated token so offline-queue retries dedupe.
    __table_args__ = (UniqueConstraint("user_id", "client_token", name="uq_timeline_user_token"),)

    id: Mapped[uuid.UUID] = _pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    client_token: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    domain: Mapped[Domain] = mapped_column(Enum(Domain, name="domain"), index=True)
    ref_table: Mapped[str | None] = mapped_column(String(64))
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source: Mapped[Source] = mapped_column(Enum(Source, name="source"))
    raw_input: Mapped[str | None] = mapped_column(Text)  # original text/transcript — ALWAYS kept
    summary: Mapped[str | None] = mapped_column(Text)  # human + embeddable one-liner
    structured: Mapped[dict] = mapped_column(JSONB, default=dict)  # parsed fields (pre-normalization)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))  # LAZY: populated at chat phase
    media: Mapped[list] = mapped_column(JSONB, default=list)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- domain tables (structured columns + freeform notes) ---


class SleepLog(Base):
    __tablename__ = "sleep_logs"
    id: Mapped[uuid.UUID] = _pk()
    bed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wake_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality: Mapped[int | None] = mapped_column(Integer)  # 1-5
    awakenings: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class FoodLog(Base):
    __tablename__ = "food_logs"
    id: Mapped[uuid.UUID] = _pk()
    meal_type: Mapped[str | None] = mapped_column(String(16))
    dish_text: Mapped[str | None] = mapped_column(Text)
    ingredients: Mapped[list | None] = mapped_column(JSONB)  # AI-derived, no manual pantry
    macros: Mapped[dict | None] = mapped_column(JSONB)  # estimate, non-authoritative
    caffeine_mg: Mapped[float | None] = mapped_column(Float)
    alcohol_units: Mapped[float | None] = mapped_column(Float)
    photo_key: Mapped[str | None] = mapped_column(String(256))
    notes: Mapped[str | None] = mapped_column(Text)


class BodyMetric(Base):
    """Synced from Withings (see docs/research/withings-api.md)."""

    __tablename__ = "body_metrics"
    __table_args__ = (UniqueConstraint("grpid", name="uq_body_metrics_grpid"),)
    id: Mapped[uuid.UUID] = _pk()
    grpid: Mapped[int | None] = mapped_column(BigInteger)  # Withings measure-group id (dedupe)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    fat_pct: Mapped[float | None] = mapped_column(Float)
    fat_mass_kg: Mapped[float | None] = mapped_column(Float)
    lean_mass_kg: Mapped[float | None] = mapped_column(Float)
    muscle_mass_kg: Mapped[float | None] = mapped_column(Float)
    body_water_kg: Mapped[float | None] = mapped_column(Float)
    bone_mass_kg: Mapped[float | None] = mapped_column(Float)
    heart_rate: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(16), default="withings")


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[uuid.UUID] = _pk()
    photo_type: Mapped[str] = mapped_column(String(16))  # face|skin|body|hair|nails
    bucket_key: Mapped[str] = mapped_column(String(256))
    prev_photo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # ghost-overlay
    analysis: Mapped[dict | None] = mapped_column(JSONB)
    ai_model: Mapped[str | None] = mapped_column(String(64))
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    sensitive: Mapped[bool] = mapped_column(default=False)
    exclude_from_cloud_ai: Mapped[bool] = mapped_column(default=False)
    enc_nonce: Mapped[str | None] = mapped_column(String(32))  # base64 of 12-byte AES-GCM nonce (sensitive only)
    content_type: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    notes: Mapped[str | None] = mapped_column(Text)


class MoodLog(Base):
    __tablename__ = "mood_logs"
    id: Mapped[uuid.UUID] = _pk()
    mood: Mapped[int | None] = mapped_column(Integer)  # 1-5
    energy: Mapped[int | None] = mapped_column(Integer)  # 1-5
    stress: Mapped[int | None] = mapped_column(Integer)  # 1-5
    journal: Mapped[str | None] = mapped_column(Text)


class BristolLog(Base):
    """Egestion — bowel. True 7-type Bristol scale + flags."""

    __tablename__ = "bristol_logs"
    id: Mapped[uuid.UUID] = _pk()
    bristol_type: Mapped[int | None] = mapped_column(Integer)  # 1-7
    color: Mapped[str | None] = mapped_column(String(32))
    straining: Mapped[bool | None] = mapped_column()
    blood: Mapped[bool | None] = mapped_column()
    pain: Mapped[bool | None] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text)


class UrineLog(Base):
    """Egestion — urination. 8-level urine color (hydration) scale."""

    __tablename__ = "urine_logs"
    id: Mapped[uuid.UUID] = _pk()
    color_scale: Mapped[int | None] = mapped_column(Integer)  # 1-8
    notes: Mapped[str | None] = mapped_column(Text)


class Product(Base):
    """Care inventory (seeded from RevampPrince). INCI for skin-correlation; no depletion tracking."""

    __tablename__ = "products"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(128))
    brand: Mapped[str | None] = mapped_column(String(128))
    category: Mapped[str | None] = mapped_column(String(32))  # face|hair|body
    role: Mapped[str | None] = mapped_column(String(64))  # cleanser|moisturizer|spf|retinoid|...
    inci: Mapped[list | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)


class CareRoutine(Base):
    """A 1-tap routine template; phase-versioned over time."""

    __tablename__ = "care_routines"
    id: Mapped[uuid.UUID] = _pk()
    name: Mapped[str] = mapped_column(String(64))  # AM / PM / shower / hair / body
    time_of_day: Mapped[str | None] = mapped_column(String(16))
    steps: Mapped[list | None] = mapped_column(JSONB)  # [{step, product_id?}]
    notes: Mapped[str | None] = mapped_column(Text)


class CareRoutineRun(Base):
    __tablename__ = "care_routine_runs"
    id: Mapped[uuid.UUID] = _pk()
    routine_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    completed: Mapped[bool] = mapped_column(default=True)
    exceptions: Mapped[list | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)


# --- auth (passkeys / WebAuthn) ---


class Credential(Base):
    """A registered passkey (WebAuthn credential). Single-user owns up to 2."""

    __tablename__ = "credentials"
    id: Mapped[uuid.UUID] = _pk()
    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)  # base64url
    public_key: Mapped[str] = mapped_column(Text)  # base64url COSE public key
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[list | None] = mapped_column(JSONB)
    name: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthConfig(Base):
    """Owner-level auth config — single row (stable WebAuthn user handle + recovery hash)."""

    __tablename__ = "auth_config"
    id: Mapped[uuid.UUID] = _pk()
    webauthn_user_id: Mapped[str] = mapped_column(String(128))  # base64url 64-byte user handle
    recovery_code_hash: Mapped[str | None] = mapped_column(String(128))  # sha256 of high-entropy code
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WithingsAccount(Base):
    """Single Withings OAuth account (one owner). Tokens rotate — persist atomically on refresh."""

    __tablename__ = "withings_account"
    id: Mapped[uuid.UUID] = _pk()
    userid: Mapped[str] = mapped_column(String(64), unique=True)
    access_token: Mapped[str] = mapped_column(Text)
    refresh_token: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scope: Mapped[str | None] = mapped_column(String(256))
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
