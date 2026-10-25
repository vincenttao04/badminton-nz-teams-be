import uuid

from sqlalchemy import CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import Base
from app.models.enums import ApprovalStatus, Event, enum_column


class RankedTeamList(Base, table=True):
    """A team's ordered list for a tournament.
    Each submission is a new, immutable row."""

    __table_args__ = (
        UniqueConstraint("team_id", "version", name="uq_ranked_list_version_per_team"),
    )

    team_id: uuid.UUID = Field(foreign_key="team.id", index=True)
    version: int = Field(ge=1)
    approval_status: ApprovalStatus = Field(
        sa_column=Column(enum_column(ApprovalStatus), nullable=False, index=True)
    )

    positions: list["Position"] = Relationship(back_populates="ranked_team_list")


class Position(Base, table=True):
    """One ranked slot in a list: an event, a rank, and the one or two players in it."""

    __table_args__ = (
        UniqueConstraint(
            "ranked_team_list_id",
            "event",
            "rank",
            name="uq_position_per_event_rank_in_list",
        ),
        CheckConstraint(
            """
            CASE
                WHEN event = 'singles' THEN partner_id IS NULL
                ELSE partner_id IS NOT NULL
            END
            """,
            name="partner_required_except_singles",
        ),
        CheckConstraint(
            "partner_id IS NULL OR partner_id <> player_id",
            name="partner_not_self",
        ),
    )

    ranked_team_list_id: uuid.UUID = Field(foreign_key="rankedteamlist.id", index=True)
    event: Event = Field(sa_column=Column(enum_column(Event), nullable=False))
    rank: int = Field(ge=1)

    player_id: uuid.UUID = Field(foreign_key="player.id", index=True)
    partner_id: uuid.UUID | None = Field(
        default=None, foreign_key="player.id", index=True
    )
