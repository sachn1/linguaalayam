"""add fuzzystrmatch extension for edit-distance fuzzy search

Revision ID: e4f8b2a1c9d6
Revises: d7e1a9c3f6b4
Create Date: 2026-10-12

"""
from typing import Sequence, Union

from alembic import op

revision: str = "e4f8b2a1c9d6"
down_revision: Union[str, None] = "d7e1a9c3f6b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS fuzzystrmatch")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS fuzzystrmatch")
