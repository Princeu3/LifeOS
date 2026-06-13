"""init: pgvector + timeline spine + first-domain tables

Revision ID: 0001
Revises:
Create Date: 2026-06-13
"""

import pgvector.sqlalchemy as pgv
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

DOMAINS = (
    "sleep", "nutrition", "hydration", "care", "photo", "body_metric", "work", "book",
    "wardrobe", "egestion", "gym", "mood", "symptom", "supplement", "media", "location",
)
SOURCES = ("manual", "voice", "photo", "withings", "auto")

UUID_PK = dict(server_default=sa.text("gen_random_uuid()"))
JSONB = postgresql.JSONB
UUID = postgresql.UUID


def _id() -> sa.Column:
    return sa.Column("id", UUID(as_uuid=True), primary_key=True, **UUID_PK)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    postgresql.ENUM(*DOMAINS, name="domain").create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(*SOURCES, name="source").create(op.get_bind(), checkfirst=True)
    domain = postgresql.ENUM(*DOMAINS, name="domain", create_type=False)
    source = postgresql.ENUM(*SOURCES, name="source", create_type=False)

    op.create_table(
        "timeline_events",
        _id(),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("domain", domain, nullable=False),
        sa.Column("ref_table", sa.String(64)),
        sa.Column("ref_id", UUID(as_uuid=True)),
        sa.Column("source", source, nullable=False),
        sa.Column("raw_input", sa.Text),
        sa.Column("summary", sa.Text),
        sa.Column("structured", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("embedding", pgv.Vector(1024)),
        sa.Column("media", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("confidence", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_timeline_user_time", "timeline_events", ["user_id", "occurred_at"])
    op.create_index("ix_timeline_domain", "timeline_events", ["domain", "occurred_at"])

    op.create_table(
        "sleep_logs", _id(),
        sa.Column("bed_at", sa.DateTime(timezone=True)),
        sa.Column("wake_at", sa.DateTime(timezone=True)),
        sa.Column("quality", sa.Integer),
        sa.Column("awakenings", sa.Integer),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "food_logs", _id(),
        sa.Column("meal_type", sa.String(16)),
        sa.Column("dish_text", sa.Text),
        sa.Column("ingredients", JSONB),
        sa.Column("macros", JSONB),
        sa.Column("caffeine_mg", sa.Float),
        sa.Column("alcohol_units", sa.Float),
        sa.Column("photo_key", sa.String(256)),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "body_metrics", _id(),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weight_kg", sa.Float),
        sa.Column("fat_pct", sa.Float),
        sa.Column("fat_mass_kg", sa.Float),
        sa.Column("lean_mass_kg", sa.Float),
        sa.Column("muscle_mass_kg", sa.Float),
        sa.Column("body_water_kg", sa.Float),
        sa.Column("bone_mass_kg", sa.Float),
        sa.Column("heart_rate", sa.Integer),
        sa.Column("source", sa.String(16), server_default="withings"),
    )
    op.create_index("ix_body_metrics_time", "body_metrics", ["measured_at"])
    op.create_table(
        "photos", _id(),
        sa.Column("photo_type", sa.String(16), nullable=False),
        sa.Column("bucket_key", sa.String(256), nullable=False),
        sa.Column("prev_photo_id", UUID(as_uuid=True)),
        sa.Column("analysis", JSONB),
        sa.Column("ai_model", sa.String(64)),
        sa.Column("ai_confidence", sa.Float),
        sa.Column("sensitive", sa.Boolean, server_default=sa.text("false")),
        sa.Column("exclude_from_cloud_ai", sa.Boolean, server_default=sa.text("false")),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "mood_logs", _id(),
        sa.Column("mood", sa.Integer),
        sa.Column("energy", sa.Integer),
        sa.Column("stress", sa.Integer),
        sa.Column("journal", sa.Text),
    )
    op.create_table(
        "bristol_logs", _id(),
        sa.Column("bristol_type", sa.Integer),
        sa.Column("color", sa.String(32)),
        sa.Column("straining", sa.Boolean),
        sa.Column("blood", sa.Boolean),
        sa.Column("pain", sa.Boolean),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "urine_logs", _id(),
        sa.Column("color_scale", sa.Integer),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "products", _id(),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("brand", sa.String(128)),
        sa.Column("category", sa.String(32)),
        sa.Column("role", sa.String(64)),
        sa.Column("inci", JSONB),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "care_routines", _id(),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("time_of_day", sa.String(16)),
        sa.Column("steps", JSONB),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "care_routine_runs", _id(),
        sa.Column("routine_id", UUID(as_uuid=True)),
        sa.Column("completed", sa.Boolean, server_default=sa.text("true")),
        sa.Column("exceptions", JSONB),
        sa.Column("notes", sa.Text),
    )


def downgrade() -> None:
    for t in (
        "care_routine_runs", "care_routines", "products", "urine_logs", "bristol_logs",
        "mood_logs", "photos", "body_metrics", "food_logs", "sleep_logs", "timeline_events",
    ):
        op.drop_table(t)
    op.execute("DROP TYPE IF EXISTS source")
    op.execute("DROP TYPE IF EXISTS domain")
