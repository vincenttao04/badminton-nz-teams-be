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
    """A team event: holds the per-event tie format and optional roster limits."""

    __table_args__ = (
        CheckConstraint(
            "min_male IS NULL OR max_male IS NULL OR min_male <= max_male",
            name="roster_min_male_not_above_max",
        ),
        CheckConstraint(
            "min_female IS NULL OR max_female IS NULL OR min_female <= max_female",
            name="roster_min_female_not_above_max",
        ),
    )

    name: str = Field(index=True)
    starts_at: datetime = Field(sa_type=DateTime(timezone=True))

    # Tie format: matches contested per event in one tie, set per tournament.
    mens_singles_matches: int = Field(ge=0)
    womens_singles_matches: int = Field(ge=0)
    mens_doubles_matches: int = Field(ge=0)
    womens_doubles_matches: int = Field(ge=0)
    mixed_doubles_matches: int = Field(ge=0)

    # Optional roster limits per sex.
    min_male: int | None = Field(default=None, ge=0)
    max_male: int | None = Field(default=None, ge=0)
    min_female: int | None = Field(default=None, ge=0)
    max_female: int | None = Field(default=None, ge=0)

    teams: list["Team"] = Relationship(back_populates="tournament")


class Team(Base, table=True):
    """A squad of players an association enters into one tournament.
    Authenticates with its own access details."""

    __table_args__ = (
        UniqueConstraint(
            "tournament_id",
            "association_id",
            "name",
            name="uq_team_name_per_association_per_tournament",
        ),
    )

    name: str = Field(index=True)
    access_details: str | None = Field(default=None)
    association_id: uuid.UUID = Field(foreign_key="association.id", index=True)
    tournament_id: uuid.UUID = Field(foreign_key="tournament.id", index=True)

    association: Association = Relationship(back_populates="teams")
    tournament: Tournament = Relationship(back_populates="teams")
