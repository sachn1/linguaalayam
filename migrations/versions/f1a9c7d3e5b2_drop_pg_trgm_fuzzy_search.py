"""drop pg_trgm extension and headword gin index, unused since edit distance replaced it

Revision ID: f1a9c7d3e5b2
Revises: e4f8b2a1c9d6
Create Date: 2026-10-13

"""

from typing import Sequence, Union

from alembic import op

revision: str = "f1a9c7d3e5b2"
down_revision: Union[str, None] = "e4f8b2a1c9d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_dictionary_entries_headword_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dictionary_entries_headword_trgm "
        "ON dictionary_entries USING GIN (headword gin_trgm_ops)"
    )
