import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import Base
from app.models.enums import Event, LineupStatus, enum_column


class TieLineup(Base, table=True):
    """A team's lineup submitted into a round slot.
    Each submission is a new, immutable row; the latest is in effect."""

    __table_args__ = (
        UniqueConstraint(
            "round_slot_id",
            "team_id",
            "version",
            name="uq_lineup_version_per_team_per_slot",
        ),
    )

    round_slot_id: uuid.UUID = Field(foreign_key="roundslot.id", index=True)
    team_id: uuid.UUID = Field(foreign_key="team.id", index=True)
    version: int = Field(ge=1)
    status: LineupStatus = Field(
        sa_column=Column(enum_column(LineupStatus), nullable=False, index=True)
    )
    copied_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    entries: list["LineupEntry"] = Relationship(back_populates="lineup")


class LineupEntry(Base, table=True):
    """One filled slot in a lineup: an event, a position, and the player/pair."""

    __table_args__ = (
        UniqueConstraint(
            "tie_lineup_id",
            "event",
            "position",
            name="uq_entry_per_event_position_in_lineup",
        ),
        CheckConstraint(
            """
            CASE
                WHEN event IN ('mens_singles', 'womens_singles')
                    THEN partner_id IS NULL
                ELSE partner_id IS NOT NULL
            END
            """,
            name="lineup_partner_required_except_singles",
        ),
        CheckConstraint(
            "partner_id IS NULL OR partner_id <> player_id",
            name="lineup_partner_not_self",
        ),
    )

    tie_lineup_id: uuid.UUID = Field(foreign_key="tielineup.id", index=True)
    event: Event = Field(sa_column=Column(enum_column(Event), nullable=False))
    position: int = Field(ge=1)

    player_id: uuid.UUID = Field(foreign_key="player.id", index=True)
    partner_id: uuid.UUID | None = Field(
        default=None, foreign_key="player.id", index=True
    )

    lineup: TieLineup = Relationship(back_populates="entries")
