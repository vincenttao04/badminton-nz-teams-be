import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.api.deps import DbSession, require_roles
from app.models import Role, TieLineup
from app.models.enums import Event, LineupStatus, RoundSlotStatus
from app.rules.results import ValidationResult
from app.services.lineups import NoApprovedListError
from app.services.review import (
    LineupActionError,
    LineupDetail,
    LineupNotFoundError,
    TeamSubmission,
    approve_lineup,
    flag_lineup,
    lineup_detail,
    mark_copied,
    slot_submissions,
    tournament_slots,
)
from app.services.slots import RoundSlotNotFoundError, get_slot
from app.services.tournaments import TournamentNotFoundError

router = APIRouter(tags=["official review"])

_require_official = Depends(require_roles(Role.TECHNICAL_OFFICIAL))


class PlayerRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    member_id: str
    full_name: str


class SubmissionSummary(BaseModel):
    team_id: uuid.UUID
    team_name: str
    submitted: bool
    lineup_id: uuid.UUID | None
    version: int | None
    lineup_status: LineupStatus | None
    submitted_at: datetime | None


class SlotSubmissionsResponse(BaseModel):
    slot_id: uuid.UUID
    status: RoundSlotStatus
    submissions: list[SubmissionSummary]


class DashboardSlot(BaseModel):
    id: uuid.UUID
    status: RoundSlotStatus
    opens_at: datetime
    closes_at: datetime | None
    submissions: list[SubmissionSummary]


class DashboardResponse(BaseModel):
    tournament_id: uuid.UUID
    slots: list[DashboardSlot]


class LineupEntryDetailResponse(BaseModel):
    event: Event
    position: int
    player: PlayerRef
    partner: PlayerRef | None


class LineupDetailResponse(BaseModel):
    id: uuid.UUID
    round_slot_id: uuid.UUID
    team_id: uuid.UUID
    team_name: str
    version: int
    status: LineupStatus
    copied_at: datetime | None
    submitted_at: datetime
    entries: list[LineupEntryDetailResponse]
    result: ValidationResult


class LineupStateResponse(BaseModel):
    id: uuid.UUID
    version: int
    status: LineupStatus
    copied_at: datetime | None


def _summaries(items: list[TeamSubmission]) -> list[SubmissionSummary]:
    summaries: list[SubmissionSummary] = []
    for item in items:
        assert item.team.id is not None
        lineup = item.lineup
        summaries.append(
            SubmissionSummary(
                team_id=item.team.id,
                team_name=item.team.name,
                submitted=lineup is not None,
                lineup_id=lineup.id if lineup is not None else None,
                version=lineup.version if lineup is not None else None,
                lineup_status=lineup.status if lineup is not None else None,
                submitted_at=lineup.created_at if lineup is not None else None,
            )
        )
    return summaries


def _detail_response(detail: LineupDetail) -> LineupDetailResponse:
    lineup = detail.lineup
    assert lineup.id is not None
    assert lineup.created_at is not None
    assert detail.team.id is not None
    return LineupDetailResponse(
        id=lineup.id,
        round_slot_id=lineup.round_slot_id,
        team_id=detail.team.id,
        team_name=detail.team.name,
        version=lineup.version,
        status=lineup.status,
        copied_at=lineup.copied_at,
        submitted_at=lineup.created_at,
        entries=[
            LineupEntryDetailResponse(
                event=entry.event,
                position=entry.position,
                player=PlayerRef.model_validate(entry.player),
                partner=(
                    PlayerRef.model_validate(entry.partner)
                    if entry.partner is not None
                    else None
                ),
            )
            for entry in detail.entries
        ],
        result=detail.result,
    )


def _state_response(lineup: TieLineup) -> LineupStateResponse:
    assert lineup.id is not None
    return LineupStateResponse(
        id=lineup.id,
        version=lineup.version,
        status=lineup.status,
        copied_at=lineup.copied_at,
    )


def _lineup_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Tie lineup not found"
    )


def _conflict(exc: LineupActionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/slots/{slot_id}/submissions", dependencies=[_require_official])
def read_slot_submissions(slot_id: uuid.UUID, db: DbSession) -> SlotSubmissionsResponse:
    try:
        slot = get_slot(db, slot_id)
    except RoundSlotNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Round slot not found"
        ) from exc
    return SlotSubmissionsResponse(
        slot_id=slot_id,
        status=slot.status,
        submissions=_summaries(slot_submissions(db, slot)),
    )


@router.get("/tournaments/{tournament_id}/dashboard", dependencies=[_require_official])
def read_tournament_dashboard(
    tournament_id: uuid.UUID, db: DbSession
) -> DashboardResponse:
    try:
        slots = tournament_slots(db, tournament_id)
    except TournamentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
        ) from exc
    dashboard_slots: list[DashboardSlot] = []
    for slot in slots:
        assert slot.id is not None
        dashboard_slots.append(
            DashboardSlot(
                id=slot.id,
                status=slot.status,
                opens_at=slot.opens_at,
                closes_at=slot.closes_at,
                submissions=_summaries(slot_submissions(db, slot)),
            )
        )
    return DashboardResponse(tournament_id=tournament_id, slots=dashboard_slots)


@router.get("/lineups/{lineup_id}", dependencies=[_require_official])
def read_lineup(lineup_id: uuid.UUID, db: DbSession) -> LineupDetailResponse:
    try:
        detail = lineup_detail(db, lineup_id)
    except LineupNotFoundError as exc:
        raise _lineup_not_found() from exc
    except NoApprovedListError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="This team has no approved list to check against.",
        ) from exc
    return _detail_response(detail)


@router.post("/lineups/{lineup_id}/approve", dependencies=[_require_official])
def approve(lineup_id: uuid.UUID, db: DbSession) -> LineupStateResponse:
    try:
        return _state_response(approve_lineup(db, lineup_id))
    except LineupNotFoundError as exc:
        raise _lineup_not_found() from exc
    except LineupActionError as exc:
        raise _conflict(exc) from exc


@router.post("/lineups/{lineup_id}/flag", dependencies=[_require_official])
def flag(lineup_id: uuid.UUID, db: DbSession) -> LineupStateResponse:
    try:
        return _state_response(flag_lineup(db, lineup_id))
    except LineupNotFoundError as exc:
        raise _lineup_not_found() from exc
    except LineupActionError as exc:
        raise _conflict(exc) from exc


@router.post("/lineups/{lineup_id}/copied", dependencies=[_require_official])
def copied(lineup_id: uuid.UUID, db: DbSession) -> LineupStateResponse:
    try:
        return _state_response(mark_copied(db, lineup_id))
    except LineupNotFoundError as exc:
        raise _lineup_not_found() from exc
    except LineupActionError as exc:
        raise _conflict(exc) from exc
