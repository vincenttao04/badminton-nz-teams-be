import uuid
from decimal import Decimal

from sqlalchemy import Column, Numeric, UniqueConstraint
from sqlmodel import Field, Relationship

from app.models.base import Base
from app.models.enums import Event, enum_column


class Player(Base, table=True):
    """A badminton player, identified by their Tournament Software Member ID."""

    member_id: str = Field(unique=True, index=True)
    full_name: str = Field(index=True)

    player_points: list["PlayerPoints"] = Relationship(back_populates="player")


class PlayerPointsSnapshot(Base, table=True):
    """One frozen import of player points.
    The in-force snapshot is the highest version."""

    version: int = Field(unique=True, index=True)

    player_points: list["PlayerPoints"] = Relationship(back_populates="snapshot")


class PlayerPoints(Base, table=True):
    """A player's ranking points for one event, within one snapshot."""

    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "player_id",
            "event",
            name="uq_points_per_player_event_per_snapshot",
        ),
    )

    snapshot_id: uuid.UUID = Field(foreign_key="playerpointssnapshot.id", index=True)
    player_id: uuid.UUID = Field(foreign_key="player.id", index=True)
    event: Event = Field(sa_column=Column(enum_column(Event), nullable=False))
    points: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    snapshot: PlayerPointsSnapshot = Relationship(back_populates="player_points")
    player: Player = Relationship(back_populates="player_points")
