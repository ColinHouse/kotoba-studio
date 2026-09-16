"""add the bound game window to sources

Revision ID: 5f7a9d2c41b8
Revises: 2ba1d1f1e6e1
Create Date: 2026-09-17 01:40:43.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "5f7a9d2c41b8"
down_revision = "2ba1d1f1e6e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("sources", schema=None) as batch_op:
        batch_op.add_column(sa.Column("window_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("sources", schema=None) as batch_op:
        batch_op.drop_column("window_json")
