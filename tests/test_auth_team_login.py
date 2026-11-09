import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.auth.sessions import load_session
from app.config import get_settings
from app.models import Association, Team, Tournament


def _team(db_session: Session, access_code: str = "team-access-code") -> Team:
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
        access_details=hash_secret(access_code),
    )
    db_session.add(team)
    db_session.commit()
    return team


def test_team_login_succeeds(client: TestClient, db_session: Session) -> None:
    team = _team(db_session)
    response = client.post(
        "/v1/auth/team-login",
        json={"team_id": str(team.id), "access_code": "team-access-code"},
    )
    assert response.status_code == 204
    token = response.cookies.get(get_settings().session_cookie_name)
    assert token is not None
    session = load_session(db_session, token)
    assert session is not None
    assert session.team_id == team.id


def test_team_login_with_wrong_code_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    team = _team(db_session)
    response = client.post(
        "/v1/auth/team-login",
        json={"team_id": str(team.id), "access_code": "wrong"},
    )
    assert response.status_code == 401


def test_team_login_with_unknown_team_is_rejected(
    client: TestClient, db_session: Session
) -> None:
    response = client.post(
        "/v1/auth/team-login",
        json={"team_id": str(uuid.uuid4()), "access_code": "whatever"},
    )
    assert response.status_code == 401
