from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlmodel import Session, select

from app.auth.hashing import hash_secret, verify_secret
from app.auth.sessions import create_session, revoke_session
from app.config import get_settings
from app.db import get_session
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

# A fixed hash to verify against when no account matches, so a missing account and
# a wrong password take the same time and cannot be told apart (no enumeration).
_DUMMY_HASH = hash_secret("november-2026-dummy")

DbSession = Annotated[Session, Depends(get_session)]


class LoginRequest(BaseModel):
    email: str
    password: str


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
