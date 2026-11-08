import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.models import Association, Role, RoleAssignment, Team, Tournament, User


def _login_official(client: TestClient, db_session: Session) -> None:
    user = User(
        email="official@example.com",
        full_name="Official",
        hashed_password=hash_secret("pw"),
    )
    db_session.add(user)
    db_session.commit()
    assert user.id is not None
    db_session.add(RoleAssignment(user_id=user.id, role=Role.TECHNICAL_OFFICIAL))
    db_session.commit()
    client.post(
        "/v1/auth/login",
        json={"email": "official@example.com", "password": "pw"},
    )


def _create_team(db_session: Session) -> Team:
    association = Association(name="Auckland")
    tournament = Tournament(
        name="Nationals",
        starts_at=datetime.now(UTC),
        mens_singles_matches=1,
        womens_singles_matches=1,
        mens_doubles_matches=1,
        womens_doubles_matches=1,
        mixed_doubles_matches=1,
    )
    db_session.add(association)
    db_session.add(tournament)
    db_session.commit()
    assert association.id is not None
    assert tournament.id is not None
    team = Team(
        name="Team A", association_id=association.id, tournament_id=tournament.id
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def test_issue_access_requires_the_official_role(
    client: TestClient, db_session: Session
) -> None:
    team = _create_team(db_session)
    assert client.post(f"/v1/teams/{team.id}/access-details").status_code == 401


def test_issued_access_code_lets_the_team_log_in(
    client: TestClient, db_session: Session
) -> None:
    team = _create_team(db_session)
    _login_official(client, db_session)
    issued = client.post(f"/v1/teams/{team.id}/access-details")
    assert issued.status_code == 201
    access_code = issued.json()["access_code"]

    client.post("/v1/auth/logout")
    login = client.post(
        "/v1/auth/team-login",
        json={"team_id": str(team.id), "access_code": access_code},
    )
    assert login.status_code == 204


def test_issue_access_for_unknown_team_is_404(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.post(f"/v1/teams/{uuid.uuid4()}/access-details")
    assert response.status_code == 404
