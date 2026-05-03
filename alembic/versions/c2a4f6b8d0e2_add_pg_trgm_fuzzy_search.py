"""add pg_trgm extension and headword gin index for fuzzy search

Revision ID: c2a4f6b8d0e2
Revises: fa3eefb53b00
Create Date: 2026-05-03

"""
from typing import Sequence, Union

from alembic import op

revision: str = "c2a4f6b8d0e2"
down_revision: Union[str, None] = "fa3eefb53b00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dictionary_entries_headword_trgm "
        "ON dictionary_entries USING GIN (headword gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_dictionary_entries_headword_trgm")
