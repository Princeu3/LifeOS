"""auth: passkey credentials + owner auth config

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-13
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

UUID = postgresql.UUID
JSONB = postgresql.JSONB


def _id() -> sa.Column:
    return sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def upgrade() -> None:
    op.create_table(
        "credentials",
        _id(),
        sa.Column("credential_id", sa.String(512), nullable=False),
        sa.Column("public_key", sa.Text, nullable=False),
        sa.Column("sign_count", sa.Integer, server_default="0"),
        sa.Column("transports", JSONB),
        sa.Column("name", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
    )
    op.create_unique_constraint("uq_credentials_credential_id", "credentials", ["credential_id"])
    op.create_table(
        "auth_config",
        _id(),
        sa.Column("webauthn_user_id", sa.String(128), nullable=False),
        sa.Column("recovery_code_hash", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("auth_config")
    op.drop_table("credentials")
