import uuid

from sqlalchemy import CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import Base
from app.models.enums import ApprovalStatus, Event, enum_column


class Tie(Base, table=True):
    """A contest between two teams within a tournament."""

    __table_args__ = (
        CheckConstraint("team_a_id <> team_b_id", name="tie_teams_distinct"),
    )

    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", index=True)
    team_a_id: uuid.UUID = Field(foreign_key="team.id", index=True)
    team_b_id: uuid.UUID = Field(foreign_key="team.id", index=True)

    lineups: list["TieLineup"] = Relationship(back_populates="tie")
    substitutions: list["Substitution"] = Relationship(back_populates="tie")
    tie_sheet: "TieSheet" = Relationship(
        back_populates="tie", sa_relationship_kwargs={"uselist": False}
    )


class TieLineup(Base, table=True):
    """A team's selection for one tie. Each submission is a new, immutable row."""

    __table_args__ = (
        UniqueConstraint(
            "tie_id", "team_id", "version", name="uq_lineup_version_per_team_per_tie"
        ),
    )

    tie_id: uuid.UUID = Field(foreign_key="tie.id", index=True)
    team_id: uuid.UUID = Field(foreign_key="team.id", index=True)
    version: int = Field(ge=1)
    approval_status: ApprovalStatus = Field(
        sa_column=Column(enum_column(ApprovalStatus), nullable=False, index=True)
    )
    is_late: bool = Field(default=False)

    tie: Tie = Relationship(back_populates="lineups")
    slots: list["LineupSlot"] = Relationship(back_populates="lineup")


class LineupSlot(Base, table=True):
    """One match slot in a lineup:an event, a rank, and the player/players in it."""

    __table_args__ = (
        UniqueConstraint(
            "lineup_id", "event", "rank", name="uq_slot_per_event_rank_in_lineup"
        ),
        CheckConstraint(
            """
            CASE
                WHEN event = 'singles' THEN partner_id IS NULL
                ELSE partner_id IS NOT NULL
            END
            """,
            name="slot_partner_required_except_singles",
        ),
        CheckConstraint(
            "partner_id IS NULL OR partner_id <> player_id",
            name="slot_partner_not_self",
        ),
    )

    lineup_id: uuid.UUID = Field(foreign_key="tielineup.id", index=True)
    event: Event = Field(sa_column=Column(enum_column(Event), nullable=False))
    rank: int = Field(ge=1)

    player_id: uuid.UUID = Field(foreign_key="player.id", index=True)
    partner_id: uuid.UUID | None = Field(
        default=None, foreign_key="player.id", index=True
    )

    lineup: TieLineup = Relationship(back_populates="slots")


class TieSheet(Base, table=True):
    """The official matchup sheet generated for a tie, one per tie."""

    tie_id: uuid.UUID = Field(foreign_key="tie.id", unique=True, index=True)

    tie: Tie = Relationship(back_populates="tie_sheet")


class Substitution(Base, table=True):
    """A player swap within a tie, between matches, approved by the referee."""

    __table_args__ = (
        CheckConstraint(
            "out_player_id <> in_player_id", name="substitution_players_distinct"
        ),
    )

    tie_id: uuid.UUID = Field(foreign_key="tie.id", index=True)
    event: Event = Field(sa_column=Column(enum_column(Event), nullable=False))
    out_player_id: uuid.UUID = Field(foreign_key="player.id", index=True)
    in_player_id: uuid.UUID = Field(foreign_key="player.id", index=True)
    status: ApprovalStatus = Field(
        sa_column=Column(enum_column(ApprovalStatus), nullable=False, index=True)
    )
    reason: str

    tie: Tie = Relationship(back_populates="substitutions")
