import uuid

from pydantic import BaseModel, Field

from app.models.enums import Event


class Entry(BaseModel):
    """One (event, position) slot: a player/pair via partner_id."""

    event: Event
    position: int
    player_id: uuid.UUID
    partner_id: uuid.UUID | None = None


class Lineup(BaseModel):
    """A proposed Tie Lineup to check."""

    entries: list[Entry] = Field(default_factory=list)


class ApprovedList(BaseModel):
    """The team's Approved Team List, the reference a lineup is checked against."""

    entries: list[Entry] = Field(default_factory=list)


class TieFormat(BaseModel):
    """How many matches each event has in a tie."""

    matches_per_event: dict[Event, int] = Field(default_factory=dict)

    def count_for(self, event: Event) -> int:
        """The number of matches an event has, defaulting to zero."""
        return self.matches_per_event.get(event, 0)
