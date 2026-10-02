"""add city and region columns to request_log

Revision ID: d7e1a9c3f6b4
Revises: b1d9e4f7a3c5
Create Date: 2026-10-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7e1a9c3f6b4"
down_revision: Union[str, None] = "b1d9e4f7a3c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("request_log", sa.Column("city", sa.Text(), nullable=True))
    op.add_column("request_log", sa.Column("region", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("request_log", "region")
    op.drop_column("request_log", "city")
