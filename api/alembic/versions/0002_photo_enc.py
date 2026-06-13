"""photos: encryption nonce + content type for AES-at-rest sensitive media

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Sensitive media is AES-256-GCM encrypted app-side; we store the 12-byte nonce (base64)
    # and original content-type so the proxy endpoint can decrypt and serve it back.
    op.add_column("photos", sa.Column("enc_nonce", sa.String(32)))
    op.add_column("photos", sa.Column("content_type", sa.String(64)))


def downgrade() -> None:
    op.drop_column("photos", "content_type")
    op.drop_column("photos", "enc_nonce")
