"""add client_id to review_logs

Revision ID: c1a4f2e83d90
Revises: 57834980b704
Create Date: 2026-09-17 13:05:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "c1a4f2e83d90"
down_revision = "57834980b704"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("review_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("client_id", sa.String(length=36), nullable=True))
        batch_op.create_index(batch_op.f("ix_review_logs_client_id"), ["client_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("review_logs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_review_logs_client_id"))
        batch_op.drop_column("client_id")
