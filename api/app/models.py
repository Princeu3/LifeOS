"""SQLAlchemy 2.0 models.

The `timeline_events` table is the append-only spine that unifies every domain for
the timeline, semantic search, and embeddings. Normalized per-domain tables hold the
structured data and are referenced via (ref_table, ref_id). Every domain table keeps a
freeform `notes` field — "structured default, freeform fallback".

Only representative domains are scaffolded here; add the rest per the CLAUDE.md
"new tracking domain" checklist. Enums must stay in lockstep with the generated TS types.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    domain: Mapped[Domain] = mapped_column(Enum(Domain, name="domain"), index=True)
    ref_table: Mapped[str | None] = mapped_column(String(64))
    ref_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source: Mapped[Source] = mapped_column(Enum(Source, name="source"))
    raw_input: Mapped[str | None] = mapped_column(Text)  # original text/transcript — ALWAYS kept
    summary: Mapped[str | None] = mapped_column(Text)  # human + embeddable one-liner
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024))
    media: Mapped[list] = mapped_column(JSONB, default=list)
    confidence: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --- representative domain tables (structured columns + freeform notes) ---


class SleepLog(Base):
    __tablename__ = "sleep_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wake_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality: Mapped[int | None] = mapped_column(Integer)  # 1-5
    awakenings: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)


class FoodLog(Base):
    __tablename__ = "food_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    photo_type: Mapped[str] = mapped_column(String(16))  # face|skin|body|hair|nails
    bucket_key: Mapped[str] = mapped_column(String(256))
    prev_photo_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))  # ghost-overlay
    analysis: Mapped[dict | None] = mapped_column(JSONB)
    ai_model: Mapped[str | None] = mapped_column(String(64))
    ai_confidence: Mapped[float | None] = mapped_column(Float)
    sensitive: Mapped[bool] = mapped_column(default=False)
    exclude_from_cloud_ai: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text)


class MoodLog(Base):
    __tablename__ = "mood_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mood: Mapped[int | None] = mapped_column(Integer)  # 1-5
    energy: Mapped[int | None] = mapped_column(Integer)  # 1-5
    stress: Mapped[int | None] = mapped_column(Integer)  # 1-5
    journal: Mapped[str | None] = mapped_column(Text)
