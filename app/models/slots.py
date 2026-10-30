import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field

from app.models.base import Base
from app.models.enums import RoundSlotStatus, enum_column


class RoundSlot(Base, table=True):
    """A submission window an official opens for a wave of ties."""

    ## First release: a slot is open to all the tournament's teams.

    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", index=True)
    status: RoundSlotStatus = Field(
        sa_column=Column(enum_column(RoundSlotStatus), nullable=False, index=True)
    )
    opens_at: datetime = Field(sa_type=DateTime(timezone=True))
    closes_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
