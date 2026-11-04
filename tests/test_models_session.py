from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models import AuthSession, User


def _future() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def test_session_for_a_user_is_allowed(db_session: Session) -> None:
    user = User(email="o@example.com", full_name="Official", hashed_password="x")
    db_session.add(user)
    db_session.commit()

    session = AuthSession(
        token_hash="token-hash", user_id=user.id, expires_at=_future()
    )
    db_session.add(session)
    db_session.commit()
    assert session.id is not None


def test_session_with_no_principal_is_rejected(db_session: Session) -> None:
    db_session.add(AuthSession(token_hash="orphan", expires_at=_future()))
    with pytest.raises(IntegrityError):
        db_session.commit()
