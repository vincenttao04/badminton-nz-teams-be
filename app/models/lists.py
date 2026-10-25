import uuid

from sqlalchemy import CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import Base
from app.models.enums import Event, ListStatus, enum_column


class RankedTeamList(Base, table=True):
    """A team's ordered list. In the first release it is seeded, and the latest
    approved list is the reference the Tie Lineup check runs against."""

    __table_args__ = (
        UniqueConstraint("team_id", "version", name="uq_list_version_per_team"),
    )

    team_id: uuid.UUID = Field(foreign_key="team.id", index=True)
    version: int = Field(ge=1)
    approval_status: ListStatus = Field(
        sa_column=Column(enum_column(ListStatus), nullable=False, index=True)
    )

    entries: list["ListEntry"] = Relationship(back_populates="ranked_team_list")


class ListEntry(Base, table=True):
    """One ranked slot in a list: an event, a position, and the player/pair."""

    __table_args__ = (
        UniqueConstraint(
            "ranked_team_list_id",
            "event",
            "position",
            name="uq_entry_per_event_position_in_list",
        ),
        CheckConstraint(
            """
            CASE
                WHEN event IN ('mens_singles', 'womens_singles')
                    THEN partner_id IS NULL
                ELSE partner_id IS NOT NULL
            END
            """,
            name="list_partner_required_except_singles",
        ),
        CheckConstraint(
            "partner_id IS NULL OR partner_id <> player_id",
            name="list_partner_not_self",
        ),
    )

    ranked_team_list_id: uuid.UUID = Field(foreign_key="rankedteamlist.id", index=True)
    event: Event = Field(sa_column=Column(enum_column(Event), nullable=False))
    position: int = Field(ge=1)

    player_id: uuid.UUID = Field(foreign_key="player.id", index=True)
    partner_id: uuid.UUID | None = Field(
        default=None, foreign_key="player.id", index=True
    )

    justification: str | None = Field(
        default=None
    )  ## (Phase A) Justification records a Doubles or Mixed deviation.

    ranked_team_list: RankedTeamList = Relationship(back_populates="entries")
