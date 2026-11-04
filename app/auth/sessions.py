import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.config import get_settings
from app.models import AuthSession

_TOKEN_BYTES = 32


def _hash_token(token: str) -> str:
    """One-way hash of a session token, for storage and lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
) -> tuple[AuthSession, str]:
    """Create a session for exactly one of a user or a team. Returns the row and
    the raw token; the token goes in the cookie, only its hash is stored."""
    if (user_id is None) == (team_id is None):
        raise ValueError("Provide exactly one of user_id or team_id")

    token = secrets.token_urlsafe(_TOKEN_BYTES)
    lifetime = timedelta(hours=get_settings().session_lifetime_hours)
    session = AuthSession(
        token_hash=_hash_token(token),
        user_id=user_id,
        team_id=team_id,
        expires_at=datetime.now(UTC) + lifetime,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session, token


def load_session(db: Session, token: str) -> AuthSession | None:
    """Resolve a token to its live session, or None if unknown or expired."""
    session = db.exec(
        select(AuthSession).where(AuthSession.token_hash == _hash_token(token))
    ).one_or_none()
    if session is None:
        return None
    if session.expires_at <= datetime.now(UTC):
        return None
    return session


def revoke_session(db: Session, token: str) -> None:
    """Delete the session for a token, if any. Safe to call when none exists."""
    session = db.exec(
        select(AuthSession).where(AuthSession.token_hash == _hash_token(token))
    ).one_or_none()
    if session is not None:
        db.delete(session)
        db.commit()
