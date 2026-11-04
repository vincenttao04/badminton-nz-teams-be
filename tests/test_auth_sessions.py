from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session

from app.auth.sessions import _hash_token, create_session, load_session, revoke_session
from app.models import User


def _user(db_session: Session) -> User:
    user = User(email="o@example.com", full_name="Official", hashed_password="x")
    db_session.add(user)
    db_session.commit()
    return user


def test_create_session_returns_a_token_and_stores_its_hash(
    db_session: Session,
) -> None:
    user = _user(db_session)
    session, token = create_session(db_session, user_id=user.id)
    assert session.id is not None
    assert session.token_hash == _hash_token(token)
    assert session.token_hash != token


def test_load_session_finds_a_live_session(db_session: Session) -> None:
    user = _user(db_session)
    _, token = create_session(db_session, user_id=user.id)
    loaded = load_session(db_session, token)
    assert loaded is not None
    assert loaded.user_id == user.id


def test_load_session_rejects_an_unknown_token(db_session: Session) -> None:
    assert load_session(db_session, "not-a-real-token") is None


def test_load_session_rejects_an_expired_session(db_session: Session) -> None:
    user = _user(db_session)
    session, token = create_session(db_session, user_id=user.id)
    session.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db_session.add(session)
    db_session.commit()
    assert load_session(db_session, token) is None


def test_revoke_session_removes_it(db_session: Session) -> None:
    user = _user(db_session)
    _, token = create_session(db_session, user_id=user.id)
    revoke_session(db_session, token)
    assert load_session(db_session, token) is None


def test_create_session_requires_exactly_one_principal(db_session: Session) -> None:
    with pytest.raises(ValueError):
        create_session(db_session)
