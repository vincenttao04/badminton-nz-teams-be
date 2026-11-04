from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.auth.sessions import load_session
from app.config import get_settings
from app.db import get_session
from app.models import AuthSession, Role, RoleAssignment, Team, User

DbSession = Annotated[Session, Depends(get_session)]


def get_current_session(request: Request, db: DbSession) -> AuthSession:
    token = request.cookies.get(get_settings().session_cookie_name)
    session = load_session(db, token) if token else None
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return session


CurrentSession = Annotated[AuthSession, Depends(get_current_session)]


def get_current_user(session: CurrentSession, db: DbSession) -> User:
    if session.user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account access required"
        )
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_team(session: CurrentSession, db: DbSession) -> Team:
    if session.team_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Team access required"
        )
    team = db.get(Team, session.team_id)
    if team is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return team


CurrentTeam = Annotated[Team, Depends(get_current_team)]


def roles_of(db: Session, user: User) -> list[Role]:
    assignments = db.exec(
        select(RoleAssignment).where(RoleAssignment.user_id == user.id)
    ).all()
    return [assignment.role for assignment in assignments]


def require_roles(*roles: Role) -> Callable[..., User]:
    def dependency(user: CurrentUser, db: DbSession) -> User:
        if not any(role in roles_of(db, user) for role in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role"
            )
        return user

    return dependency
