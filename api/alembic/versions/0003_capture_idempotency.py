"""capture idempotency: client_token + unique (user_id, client_token)

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Client-generated dedup token so the offline capture queue can retry a POST safely.
    # NULLs are allowed and (Postgres) treated as distinct, so existing token-less rows don't clash.
    op.add_column("timeline_events", sa.Column("client_token", sa.String(64)))
    op.create_unique_constraint(
        "uq_timeline_user_token", "timeline_events", ["user_id", "client_token"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_timeline_user_token", "timeline_events", type_="unique")
    op.drop_column("timeline_events", "client_token")
