import uuid
from typing import Self

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from app.api.deps import DbSession, require_roles
from app.models import Event, ListStatus, Role
from app.services.approved_lists import (
    ApprovedListEntryInput,
    PlayerInput,
    create_approved_list,
)
from app.services.teams import TeamNotFoundError, issue_access_details

router = APIRouter(prefix="/teams", tags=["teams"])

_require_official = Depends(require_roles(Role.TECHNICAL_OFFICIAL))
_DOUBLES = (Event.MENS_DOUBLES, Event.WOMENS_DOUBLES, Event.MIXED_DOUBLES)


class AccessDetailsResponse(BaseModel):
    team_id: uuid.UUID
    access_code: str


class PlayerRef(BaseModel):
    member_id: str = Field(min_length=1)
    full_name: str = Field(min_length=1)


class ApprovedListEntry(BaseModel):
    event: Event
    position: int = Field(ge=1)
    player: PlayerRef
    partner: PlayerRef | None = None

    @model_validator(mode="after")
    def _partner_matches_event(self) -> Self:
        needs_partner = self.event in _DOUBLES
        if needs_partner and self.partner is None:
            raise ValueError(f"{self.event.value} needs a partner")
        if not needs_partner and self.partner is not None:
            raise ValueError(f"{self.event.value} must not have a partner")
        if self.partner is not None and self.partner.member_id == self.player.member_id:
            raise ValueError("A player cannot partner themselves")
        return self


class ApprovedListCreate(BaseModel):
    entries: list[ApprovedListEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_duplicate_slots(self) -> Self:
        seen: set[tuple[Event, int]] = set()
        for entry in self.entries:
            slot = (entry.event, entry.position)
            if slot in seen:
                raise ValueError(
                    f"Duplicate entry for {entry.event.value} position {entry.position}"
                )
            seen.add(slot)
        return self


class ApprovedListResponse(BaseModel):
    id: uuid.UUID
    team_id: uuid.UUID
    version: int
    approval_status: ListStatus
    entry_count: int


def _team_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")


@router.post(
    "/{team_id}/access-details",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_official],
)
def issue_access(team_id: uuid.UUID, db: DbSession) -> AccessDetailsResponse:
    try:
        access_code = issue_access_details(db, team_id)
    except TeamNotFoundError as exc:
        raise _team_not_found() from exc
    return AccessDetailsResponse(team_id=team_id, access_code=access_code)


@router.post(
    "/{team_id}/approved-list",
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_official],
)
def record_approved_list(
    team_id: uuid.UUID, body: ApprovedListCreate, db: DbSession
) -> ApprovedListResponse:
    inputs = [_to_entry_input(entry) for entry in body.entries]
    try:
        ranked_list = create_approved_list(db, team_id, inputs)
    except TeamNotFoundError as exc:
        raise _team_not_found() from exc
    assert ranked_list.id is not None
    return ApprovedListResponse(
        id=ranked_list.id,
        team_id=team_id,
        version=ranked_list.version,
        approval_status=ranked_list.approval_status,
        entry_count=len(inputs),
    )


def _to_entry_input(entry: ApprovedListEntry) -> ApprovedListEntryInput:
    return ApprovedListEntryInput(
        event=entry.event,
        position=entry.position,
        player=PlayerInput(entry.player.member_id, entry.player.full_name),
        partner=(
            PlayerInput(entry.partner.member_id, entry.partner.full_name)
            if entry.partner is not None
            else None
        ),
    )
