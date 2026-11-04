"""rename user table to app_user

Revision ID: 1be8251c9573
Revises: 5a5c9b7cedc9
Create Date: 2026-11-04 16:58:19.215330

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '1be8251c9573'
down_revision: Union[str, Sequence[str], None] = '5a5c9b7cedc9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.rename_table("user", "app_user")
    op.execute("ALTER TABLE app_user RENAME CONSTRAINT user_pkey TO app_user_pkey")
    op.execute("ALTER INDEX ix_user_email RENAME TO ix_app_user_email")


def downgrade() -> None:
    op.execute("ALTER TABLE app_user RENAME CONSTRAINT app_user_pkey TO user_pkey")
    op.execute("ALTER INDEX ix_app_user_email RENAME TO ix_user_email")
    op.rename_table("app_user", "user")