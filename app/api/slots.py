import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.api.deps import DbSession, get_current_session, require_roles
from app.models import Role
from app.models.enums import RoundSlotStatus
from app.services.slots import (
    RoundSlotNotFoundError,
    RoundSlotTeamError,
    RoundSlotWindowError,
    get_slot,
    list_admitted_teams,
    list_slots,
    open_slot,
    update_slot,
)
from app.services.tournaments import TournamentNotFoundError, get_tournament

router = APIRouter(tags=["round slots"])

_require_official = Depends(require_roles(Role.TECHNICAL_OFFICIAL))
_require_session = Depends(get_current_session)


class SlotOpen(BaseModel):
    opens_at: AwareDatetime | None = None
    closes_at: AwareDatetime | None = None
    team_ids: list[uuid.UUID] | None = None


class SlotUpdate(BaseModel):
    status: RoundSlotStatus | None = None
    closes_at: AwareDatetime | None = None
    team_ids: list[uuid.UUID] | None = None


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tournament_id: uuid.UUID
    status: RoundSlotStatus
    opens_at: datetime
    closes_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SlotTeamMember(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class SlotTeamsResponse(BaseModel):
    # admits_all is true when no teams are listed: the slot admits every team
    # in its tournament.
    admits_all: bool
    teams: list[SlotTeamMember]


def _slot_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Round slot not found"
    )


def _tournament_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
    )


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail
    )


@router.post(
    "/tournaments/{tournament_id}/slots",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_official],
)
def open_round_slot(
    tournament_id: uuid.UUID, body: SlotOpen, db: DbSession
) -> SlotResponse:
    try:
        get_tournament(db, tournament_id)
    except TournamentNotFoundError as exc:
        raise _tournament_not_found() from exc
    try:
        slot = open_slot(
            db,
            tournament_id=tournament_id,
            opens_at=body.opens_at,
            closes_at=body.closes_at,
            team_ids=body.team_ids,
        )
    except (RoundSlotWindowError, RoundSlotTeamError) as exc:
        raise _unprocessable(str(exc)) from exc
    return SlotResponse.model_validate(slot)


@router.get("/tournaments/{tournament_id}/slots", dependencies=[_require_session])
def list_round_slots(tournament_id: uuid.UUID, db: DbSession) -> list[SlotResponse]:
    try:
        get_tournament(db, tournament_id)
    except TournamentNotFoundError as exc:
        raise _tournament_not_found() from exc
    return [SlotResponse.model_validate(slot) for slot in list_slots(db, tournament_id)]


@router.get("/slots/{slot_id}", dependencies=[_require_session])
def read_round_slot(slot_id: uuid.UUID, db: DbSession) -> SlotResponse:
    try:
        slot = get_slot(db, slot_id)
    except RoundSlotNotFoundError as exc:
        raise _slot_not_found() from exc
    return SlotResponse.model_validate(slot)


@router.get("/slots/{slot_id}/teams", dependencies=[_require_session])
def list_round_slot_teams(slot_id: uuid.UUID, db: DbSession) -> SlotTeamsResponse:
    try:
        teams = list_admitted_teams(db, slot_id)
    except RoundSlotNotFoundError as exc:
        raise _slot_not_found() from exc
    return SlotTeamsResponse(
        admits_all=not teams,
        teams=[SlotTeamMember.model_validate(team) for team in teams],
    )


@router.patch("/slots/{slot_id}", dependencies=[_require_official])
def update_round_slot(
    slot_id: uuid.UUID, body: SlotUpdate, db: DbSession
) -> SlotResponse:
    if body.status is None and body.closes_at is None and body.team_ids is None:
        raise _unprocessable("Provide a status change, a new cut-off, or teams.")
    try:
        slot = update_slot(
            db,
            slot_id,
            status=body.status,
            closes_at=body.closes_at,
            team_ids=body.team_ids,
        )
    except RoundSlotNotFoundError as exc:
        raise _slot_not_found() from exc
    except (RoundSlotWindowError, RoundSlotTeamError) as exc:
        raise _unprocessable(str(exc)) from exc
    return SlotResponse.model_validate(slot)
