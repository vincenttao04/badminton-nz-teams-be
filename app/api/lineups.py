import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentTeam, DbSession
from app.models.enums import Event
from app.rules import Entry, Lineup
from app.rules.results import ValidationResult
from app.services.lineups import (
    NoApprovedListError,
    check_team_lineup,
    list_approved_units,
    tie_format_for_team,
)

router = APIRouter(prefix="/lineup", tags=["tie lineup"])


class PlayerRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: str
    full_name: str


class ApprovedEntryResponse(BaseModel):
    event: Event
    position: int
    player: PlayerRef
    partner: PlayerRef | None


class LineupContextResponse(BaseModel):
    tie_format: dict[Event, int]
    approved_list: list[ApprovedEntryResponse]


class LineupEntryInput(BaseModel):
    event: Event
    position: int
    player_id: uuid.UUID
    partner_id: uuid.UUID | None = None


class LineupCheckRequest(BaseModel):
    entries: list[LineupEntryInput] = Field(default_factory=list)


def _no_approved_list() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="This team has no approved list to build from.",
    )


@router.get("/context")
def read_lineup_context(team: CurrentTeam, db: DbSession) -> LineupContextResponse:
    assert team.id is not None
    tie_format = tie_format_for_team(db, team)
    try:
        units = list_approved_units(db, team.id)
    except NoApprovedListError as exc:
        raise _no_approved_list() from exc
    return LineupContextResponse(
        tie_format=tie_format.matches_per_event,
        approved_list=[
            ApprovedEntryResponse(
                event=unit.event,
                position=unit.position,
                player=PlayerRef.model_validate(unit.player),
                partner=(
                    PlayerRef.model_validate(unit.partner)
                    if unit.partner is not None
                    else None
                ),
            )
            for unit in units
        ],
    )


@router.post("/check")
def check_lineup(
    body: LineupCheckRequest, team: CurrentTeam, db: DbSession
) -> ValidationResult:
    lineup = Lineup(
        entries=[
            Entry(
                event=entry.event,
                position=entry.position,
                player_id=entry.player_id,
                partner_id=entry.partner_id,
            )
            for entry in body.entries
        ]
    )
    try:
        return check_team_lineup(db, team, lineup)
    except NoApprovedListError as exc:
        raise _no_approved_list() from exc
