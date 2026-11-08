import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import DbSession, require_roles
from app.models import Role
from app.services.teams import TeamNotFoundError, issue_access_details

router = APIRouter(prefix="/teams", tags=["teams"])

_require_official = Depends(require_roles(Role.TECHNICAL_OFFICIAL))


class AccessDetailsResponse(BaseModel):
    team_id: uuid.UUID
    access_code: str


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
