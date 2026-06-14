"""photos: created_at (for ghost-overlay "latest of type" ordering)

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "photos",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_column("photos", "created_at")
