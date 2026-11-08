import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import DbSession, get_current_session, require_roles
from app.models import Role, Tournament
from app.services.tournaments import (
    TournamentConfigError,
    TournamentNotFoundError,
    create_tournament,
    get_tournament,
    list_tournaments,
    update_tournament,
)

router = APIRouter(prefix="/tournaments", tags=["tournaments"])

_require_official = Depends(require_roles(Role.TECHNICAL_OFFICIAL))
_require_session = Depends(get_current_session)


class TournamentCreate(BaseModel):
    name: str = Field(min_length=1)
    starts_at: datetime
    mens_singles_matches: int = Field(ge=0)
    womens_singles_matches: int = Field(ge=0)
    mens_doubles_matches: int = Field(ge=0)
    womens_doubles_matches: int = Field(ge=0)
    mixed_doubles_matches: int = Field(ge=0)
    min_male: int | None = Field(default=None, ge=0)
    max_male: int | None = Field(default=None, ge=0)
    min_female: int | None = Field(default=None, ge=0)
    max_female: int | None = Field(default=None, ge=0)


class TournamentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    starts_at: datetime | None = None
    mens_singles_matches: int | None = Field(default=None, ge=0)
    womens_singles_matches: int | None = Field(default=None, ge=0)
    mens_doubles_matches: int | None = Field(default=None, ge=0)
    womens_doubles_matches: int | None = Field(default=None, ge=0)
    mixed_doubles_matches: int | None = Field(default=None, ge=0)
    min_male: int | None = Field(default=None, ge=0)
    max_male: int | None = Field(default=None, ge=0)
    min_female: int | None = Field(default=None, ge=0)
    max_female: int | None = Field(default=None, ge=0)


class TournamentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    starts_at: datetime
    mens_singles_matches: int
    womens_singles_matches: int
    mens_doubles_matches: int
    womens_doubles_matches: int
    mixed_doubles_matches: int
    min_male: int | None
    max_male: int | None
    min_female: int | None
    max_female: int | None
    created_at: datetime
    updated_at: datetime


def _config_error(exc: TournamentConfigError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=exc.result.model_dump(mode="json"),
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Tournament not found"
    )


@router.get("", dependencies=[_require_session])
def list_all(db: DbSession) -> list[TournamentResponse]:
    return [
        TournamentResponse.model_validate(tournament)
        for tournament in list_tournaments(db)
    ]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[_require_official])
def create(body: TournamentCreate, db: DbSession) -> TournamentResponse:
    tournament = Tournament(**body.model_dump())
    try:
        created = create_tournament(db, tournament)
    except TournamentConfigError as exc:
        raise _config_error(exc) from exc
    return TournamentResponse.model_validate(created)


@router.get("/{tournament_id}", dependencies=[_require_session])
def read(tournament_id: uuid.UUID, db: DbSession) -> TournamentResponse:
    try:
        tournament = get_tournament(db, tournament_id)
    except TournamentNotFoundError as exc:
        raise _not_found() from exc
    return TournamentResponse.model_validate(tournament)


@router.patch("/{tournament_id}", dependencies=[_require_official])
def update(
    tournament_id: uuid.UUID, body: TournamentUpdate, db: DbSession
) -> TournamentResponse:
    changes = body.model_dump(exclude_unset=True)
    try:
        updated = update_tournament(db, tournament_id, changes)
    except TournamentNotFoundError as exc:
        raise _not_found() from exc
    except TournamentConfigError as exc:
        raise _config_error(exc) from exc
    return TournamentResponse.model_validate(updated)
