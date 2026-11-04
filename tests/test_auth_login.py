from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.auth.sessions import load_session
from app.config import get_settings
from app.models import User


def _user(db_session: Session, password: str = "s3cret", active: bool = True) -> User:
    user = User(
        email="official@example.com",
        full_name="Official",
        hashed_password=hash_secret(password),
        is_active=active,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_login_succeeds_and_sets_a_session_cookie(
    client: TestClient, db_session: Session
) -> None:
    _user(db_session)
    response = client.post(
        "/v1/auth/login",
        json={"email": "official@example.com", "password": "s3cret"},
    )
    assert response.status_code == 204
    token = response.cookies.get(get_settings().session_cookie_name)
    assert token is not None
    assert load_session(db_session, token) is not None


def test_login_with_wrong_password_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    _user(db_session)
    response = client.post(
        "/v1/auth/login",
        json={"email": "official@example.com", "password": "wrong"},
    )
    assert response.status_code == 401


def test_login_with_unknown_email_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        "/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_login_for_an_inactive_user_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    _user(db_session, active=False)
    response = client.post(
        "/v1/auth/login",
        json={"email": "official@example.com", "password": "s3cret"},
    )
    assert response.status_code == 401


def test_logout_revokes_the_session(client: TestClient, db_session: Session) -> None:
    _user(db_session)
    login = client.post(
        "/v1/auth/login",
        json={"email": "official@example.com", "password": "s3cret"},
    )
    token = login.cookies.get(get_settings().session_cookie_name)
    assert token is not None
    assert load_session(db_session, token) is not None

    logout = client.post("/v1/auth/logout")
    assert logout.status_code == 204
    assert load_session(db_session, token) is None
