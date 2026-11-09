import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import CurrentTeam, DbSession
from app.models.enums import Event, LineupStatus
from app.rules import Entry, Lineup
from app.rules.results import ValidationResult
from app.services.lineups import (
    LineupShapeError,
    NoApprovedListError,
    SlotClosedError,
    TeamNotAdmittedError,
    check_team_lineup,
    list_approved_units,
    submit_lineup,
    tie_format_for_team,
)
from app.services.slots import RoundSlotNotFoundError

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


class LineupSubmitRequest(BaseModel):
    round_slot_id: uuid.UUID
    entries: list[LineupEntryInput] = Field(default_factory=list)


class LineupSubmitResponse(BaseModel):
    id: uuid.UUID
    round_slot_id: uuid.UUID
    team_id: uuid.UUID
    version: int
    status: LineupStatus
    submitted_at: datetime
    result: ValidationResult


def _to_lineup(entries: list[LineupEntryInput]) -> Lineup:
    return Lineup(
        entries=[
            Entry(
                event=entry.event,
                position=entry.position,
                player_id=entry.player_id,
                partner_id=entry.partner_id,
            )
            for entry in entries
        ]
    )


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
    try:
        return check_team_lineup(db, team, _to_lineup(body.entries))
    except NoApprovedListError as exc:
        raise _no_approved_list() from exc


@router.post("/submit", status_code=status.HTTP_201_CREATED)
def submit_lineup_endpoint(
    body: LineupSubmitRequest, team: CurrentTeam, db: DbSession
) -> LineupSubmitResponse:
    try:
        submission, result = submit_lineup(
            db, team, body.round_slot_id, _to_lineup(body.entries)
        )
    except RoundSlotNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round slot not found"
        ) from exc
    except SlotClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The round slot is closed."
        ) from exc
    except TeamNotAdmittedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This team is not admitted to the slot.",
        ) from exc
    except LineupShapeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    except NoApprovedListError as exc:
        raise _no_approved_list() from exc
    assert submission.id is not None
    assert submission.created_at is not None
    return LineupSubmitResponse(
        id=submission.id,
        round_slot_id=submission.round_slot_id,
        team_id=submission.team_id,
        version=submission.version,
        status=submission.status,
        submitted_at=submission.created_at,
        result=result,
    )
