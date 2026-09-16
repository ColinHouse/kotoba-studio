"""mark frequency dictionaries as their own kind

Revision ID: 8086168861c3
Revises: 0f65b6e861c2
Create Date: 2026-09-17 00:23:26.023593
"""

from __future__ import annotations

from alembic import op

revision = "8086168861c3"
down_revision = "0f65b6e861c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rows imported before the kind split: a yomitan dictionary that has
    # frequencies but no entries is a frequency table, not a dictionary.
    op.execute(
        "UPDATE dictionaries SET kind = 'yomitan-freq' "
        "WHERE kind = 'yomitan' "
        "AND id IN (SELECT DISTINCT dict_id FROM term_frequencies) "
        "AND id NOT IN (SELECT DISTINCT dict_id FROM dict_entries)"
    )


def downgrade() -> None:
    op.execute("UPDATE dictionaries SET kind = 'yomitan' WHERE kind = 'yomitan-freq'")
