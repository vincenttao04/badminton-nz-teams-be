import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, UniqueConstraint
from sqlmodel import Field

from app.models.base import Base
from app.models.enums import RoundSlotStatus, enum_column


class RoundSlot(Base, table=True):
    """A submission window an official opens for a wave of ties."""

    ## A slot with no SlotTeam rows admits every team in its tournament;
    ## adding rows narrows it to exactly those teams.

    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", index=True)
    status: RoundSlotStatus = Field(
        sa_column=Column(enum_column(RoundSlotStatus), nullable=False, index=True)
    )
    opens_at: datetime = Field(sa_type=DateTime(timezone=True))
    closes_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))


class SlotTeam(Base, table=True):
    """A team admitted to a round slot (US-41 selective gating).

    Its absence is meaningful: a slot with no rows admits all of its
    tournament's teams, so rows act as an allowlist, not a blocklist.
    """

    __table_args__ = (
        UniqueConstraint("round_slot_id", "team_id", name="uq_team_per_slot"),
    )

    round_slot_id: uuid.UUID = Field(foreign_key="roundslot.id", index=True)
    team_id: uuid.UUID = Field(foreign_key="team.id", index=True)
