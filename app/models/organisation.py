import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import Base


class Association(Base, table=True):
    """A regional body that enters teams into tournaments."""

    name: str = Field(unique=True, index=True)

    teams: list["Team"] = Relationship(back_populates="association")


class Tournament(Base, table=True):
    """A team event, holding the tie format and the key deadlines."""

    __table_args__ = (
        CheckConstraint(
            "protest_deadline < starts_at",
            name="protest_deadline_before_start",
        ),
    )

    name: str = Field(index=True)
    starts_at: datetime = Field(sa_type=DateTime(timezone=True))
    protest_deadline: datetime = Field(sa_type=DateTime(timezone=True))

    # Tie format: matches contested per event in one tie, set per tournament.
    singles_matches: int = Field(ge=0)
    doubles_matches: int = Field(ge=0)
    mixed_matches: int = Field(ge=0)

    teams: list["Team"] = Relationship(back_populates="tournament")


class Team(Base, table=True):
    """A squad an association enters into one tournament."""

    __table_args__ = (
        UniqueConstraint(
            "tournament_id",
            "association_id",
            "name",
            name="uq_team_name_per_association_per_tournament",
        ),
    )

    name: str = Field(index=True)
    association_id: uuid.UUID = Field(foreign_key="association.id", index=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", index=True)

    association: Association = Relationship(back_populates="teams")
    tournament: Tournament = Relationship(back_populates="teams")
