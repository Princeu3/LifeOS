"""withings: oauth account (tokens) + body_metrics dedupe key (grpid)

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

UUID = postgresql.UUID


def _id() -> sa.Column:
    return sa.Column(
        "id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")
    )


def upgrade() -> None:
    # Single Withings account (one owner). Tokens rotate — persist atomically on every refresh.
    op.create_table(
        "withings_account",
        _id(),
        sa.Column("userid", sa.String(64), nullable=False),
        sa.Column("access_token", sa.Text, nullable=False),
        sa.Column("refresh_token", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.String(256)),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint("uq_withings_userid", "withings_account", ["userid"])

    # Withings measure-group id — dedupe so re-delivered/overlapping notifications don't double-insert.
    op.add_column("body_metrics", sa.Column("grpid", sa.BigInteger))
    op.create_unique_constraint("uq_body_metrics_grpid", "body_metrics", ["grpid"])


def downgrade() -> None:
    op.drop_constraint("uq_body_metrics_grpid", "body_metrics", type_="unique")
    op.drop_column("body_metrics", "grpid")
    op.drop_table("withings_account")
