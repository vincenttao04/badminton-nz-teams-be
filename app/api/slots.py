import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import AwareDatetime, BaseModel, ConfigDict

from app.api.deps import DbSession, get_current_session, require_roles
from app.models import Role
from app.models.enums import RoundSlotStatus
from app.services.slots import (
    RoundSlotNotFoundError,
    RoundSlotWindowError,
    get_slot,
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


class SlotUpdate(BaseModel):
    status: RoundSlotStatus | None = None
    closes_at: AwareDatetime | None = None


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tournament_id: uuid.UUID
    status: RoundSlotStatus
    opens_at: datetime
    closes_at: datetime | None
    created_at: datetime
    updated_at: datetime


def _slot_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Round slot not found"
    )


def _tournament_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
    )


def _window_error(exc: RoundSlotWindowError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
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
        )
    except RoundSlotWindowError as exc:
        raise _window_error(exc) from exc
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


@router.patch("/slots/{slot_id}", dependencies=[_require_official])
def update_round_slot(
    slot_id: uuid.UUID, body: SlotUpdate, db: DbSession
) -> SlotResponse:
    if body.status is None and body.closes_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide a status change or a new cut-off.",
        )
    try:
        slot = update_slot(db, slot_id, status=body.status, closes_at=body.closes_at)
    except RoundSlotNotFoundError as exc:
        raise _slot_not_found() from exc
    except RoundSlotWindowError as exc:
        raise _window_error(exc) from exc
    return SlotResponse.model_validate(slot)
