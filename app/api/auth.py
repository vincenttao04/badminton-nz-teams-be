import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.api.deps import CurrentSession, roles_of
from app.auth.hashing import hash_secret, verify_secret
from app.auth.sessions import create_session, revoke_session
from app.config import get_settings
from app.db import get_session
from app.models import Role, Team, User

router = APIRouter(prefix="/auth", tags=["auth"])

# A fixed hash to verify against when no account matches, so a missing account and
# a wrong password take the same time and cannot be told apart (no enumeration).
_DUMMY_HASH = hash_secret("november-2026-dummy")

DbSession = Annotated[Session, Depends(get_session)]


class LoginRequest(BaseModel):
    email: str
    password: str


class TeamLoginRequest(BaseModel):
    team_id: uuid.UUID
    access_code: str


class MeResponse(BaseModel):
    kind: Literal["user", "team"]
    id: uuid.UUID
    name: str
    roles: list[Role]


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_lifetime_hours * 3600,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


@router.post("/login", status_code=status.HTTP_204_NO_CONTENT)
def login(body: LoginRequest, response: Response, db: DbSession) -> None:
    user = db.exec(select(User).where(User.email == body.email)).one_or_none()
    if user is None or not user.is_active:
        verify_secret(body.password, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_secret(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _, token = create_session(db, user_id=user.id)
    _set_session_cookie(response, token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> None:
    cookie_name = get_settings().session_cookie_name
    token = request.cookies.get(cookie_name)
    if token:
        revoke_session(db, token)
    response.delete_cookie(cookie_name)


@router.post("/team-login", status_code=status.HTTP_204_NO_CONTENT)
def team_login(body: TeamLoginRequest, response: Response, db: DbSession) -> None:
    team = db.get(Team, body.team_id)
    if team is None or team.access_details is None:
        verify_secret(body.access_code, _DUMMY_HASH)
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not verify_secret(body.access_code, team.access_details):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _, token = create_session(db, team_id=team.id)
    _set_session_cookie(response, token)


@router.get("/me")
def me(session: CurrentSession, db: DbSession) -> MeResponse:
    if session.user_id is not None:
        user = db.get(User, session.user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return MeResponse(
            kind="user",
            id=session.user_id,
            name=user.full_name,
            roles=roles_of(db, user),
        )
    if session.team_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    team = db.get(Team, session.team_id)
    if team is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return MeResponse(kind="team", id=session.team_id, name=team.name, roles=[])
