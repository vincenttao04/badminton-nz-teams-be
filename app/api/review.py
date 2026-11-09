import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import DbSession, require_roles
from app.models import Role
from app.models.enums import LineupStatus, RoundSlotStatus
from app.services.review import TeamSubmission, slot_submissions, tournament_slots
from app.services.slots import RoundSlotNotFoundError, get_slot
from app.services.tournaments import TournamentNotFoundError

router = APIRouter(tags=["official review"])

_require_official = Depends(require_roles(Role.TECHNICAL_OFFICIAL))


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
