"""body_metrics: dedupe by measured_at (merge Withings groups per weigh-in), reset withings backfill

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-14
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clear the (auto-synced, re-fetchable) Withings backfill so we can re-sync into the merged model,
    # and reset last_sync so the next run backfills from scratch. No user-entered data is touched.
    op.execute("DELETE FROM timeline_events WHERE source = 'withings'")
    op.execute("DELETE FROM body_metrics WHERE source = 'withings'")
    op.execute("UPDATE withings_account SET last_sync_at = NULL")
    op.drop_constraint("uq_body_metrics_grpid", "body_metrics", type_="unique")
    op.create_unique_constraint("uq_body_metrics_measured_at", "body_metrics", ["measured_at"])


def downgrade() -> None:
    op.drop_constraint("uq_body_metrics_measured_at", "body_metrics", type_="unique")
    op.create_unique_constraint("uq_body_metrics_grpid", "body_metrics", ["grpid"])
