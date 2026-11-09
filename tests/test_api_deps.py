from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.deps import require_roles
from app.auth.hashing import hash_secret
from app.db import get_session
from app.main import create_app
from app.models import Association, Role, RoleAssignment, Team, Tournament, User


def _official(db_session: Session) -> User:
    user = User(
        email="o@example.com", full_name="Official", hashed_password=hash_secret("pw")
    )
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    db_session.add(RoleAssignment(user_id=user.id, role=Role.TECHNICAL_OFFICIAL))
    db_session.commit()
    return user


def _team(db_session: Session, code: str = "code") -> Team:
    association = Association(name="Waikato")
    tournament = Tournament(
        name="Nationals",
        starts_at=datetime.now(UTC),
        ends_at=datetime(2030, 1, 1, tzinfo=UTC),
        mens_singles_matches=1,
        womens_singles_matches=1,
        mens_doubles_matches=0,
        womens_doubles_matches=0,
        mixed_doubles_matches=1,
    )
    db_session.add(association)
    db_session.add(tournament)
    db_session.commit()
    assert association.id is not None
    assert tournament.id is not None
    team = Team(
        name="Team A",
        association_id=association.id,
        tournament_id=tournament.id,
        access_details=hash_secret(code),
    )
    db_session.add(team)
    db_session.commit()
    return team


def test_me_returns_the_current_user(client: TestClient, db_session: Session) -> None:
    user = _official(db_session)
    client.post("/v1/auth/login", json={"email": "o@example.com", "password": "pw"})
    response = client.get("/v1/auth/me")
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "user"
    assert body["id"] == str(user.id)
    assert "technical_official" in body["roles"]


def test_me_returns_the_current_team(client: TestClient, db_session: Session) -> None:
    team = _team(db_session)
    client.post(
        "/v1/auth/team-login",
        json={"team_id": str(team.id), "access_code": "code"},
    )
    response = client.get("/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["kind"] == "team"


def test_me_without_a_session_is_unauthorised(client: TestClient) -> None:
    assert client.get("/v1/auth/me").status_code == 401


def test_require_roles_allows_and_blocks(db_session: Session) -> None:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session

    @app.get("/official-only")
    def official_only(
        user: Annotated[User, Depends(require_roles(Role.TECHNICAL_OFFICIAL))],
    ) -> dict[str, str]:
        return {"id": str(user.id)}

    client = TestClient(app, base_url="https://testserver")
    user = User(email="x@example.com", full_name="X", hashed_password=hash_secret("pw"))
    db_session.add(user)
    db_session.commit()
    client.post("/v1/auth/login", json={"email": "x@example.com", "password": "pw"})

    assert client.get("/official-only").status_code == 403

    assert user.id is not None
    db_session.add(RoleAssignment(user_id=user.id, role=Role.TECHNICAL_OFFICIAL))
    db_session.commit()
    assert client.get("/official-only").status_code == 200

    app.dependency_overrides.clear()
