import uuid
from datetime import datetime

from sqlalchemy import DateTime, func, text
from sqlmodel import Field, SQLModel


class Base(SQLModel):
    """Columns shared by every table: a UUIDv7 primary key and audit timestamps."""

    id: uuid.UUID | None = Field(
        default=None,
        primary_key=True,
        sa_column_kwargs={"server_default": text("uuidv7()")},
    )
    created_at: datetime | None = Field(
        default=None,
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now()},
    )
    updated_at: datetime | None = Field(
        default=None,
        nullable=False,
        sa_type=DateTime(timezone=True),
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )
