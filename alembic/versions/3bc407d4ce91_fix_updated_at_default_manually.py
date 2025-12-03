"""Fix updated_at default manually

Revision ID: 3bc407d4ce91
Revises: 1673c25d1c3b
Create Date: 2025-12-03 05:00:05.238374

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bc407d4ce91'
down_revision: Union[str, Sequence[str], None] = '1673c25d1c3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE matches ALTER COLUMN updated_at SET DEFAULT now()")
    op.execute("ALTER TABLE matches ALTER COLUMN created_at SET DEFAULT now()")


def downgrade() -> None:
    op.execute("ALTER TABLE matches ALTER COLUMN updated_at DROP DEFAULT")
    op.execute("ALTER TABLE matches ALTER COLUMN created_at DROP DEFAULT")
