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


def _entries() -> list[dict[str, object]]:
    return [
        {
            "event": "mens_singles",
            "position": 1,
            "player": {"member_id": "M1", "full_name": "M One"},
        },
        {
            "event": "womens_singles",
            "position": 1,
            "player": {"member_id": "F1", "full_name": "F One"},
        },
        {
            "event": "mens_doubles",
            "position": 1,
            "player": {"member_id": "M2", "full_name": "M Two"},
            "partner": {"member_id": "M3", "full_name": "M Three"},
        },
        {
            "event": "womens_doubles",
            "position": 1,
            "player": {"member_id": "F2", "full_name": "F Two"},
            "partner": {"member_id": "F3", "full_name": "F Three"},
        },
        {
            "event": "mixed_doubles",
            "position": 1,
            "player": {"member_id": "M1", "full_name": "M One"},
            "partner": {"member_id": "F1", "full_name": "F One"},
        },
    ]


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


def test_record_approved_list_creates_an_approved_version(
    client: TestClient, db_session: Session
) -> None:
    team = _create_team(db_session)
    _login_official(client, db_session)
    response = client.post(
        f"/v1/teams/{team.id}/approved-list", json={"entries": _entries()}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["approval_status"] == "approved"
    assert body["entry_count"] == 5


def test_second_approved_list_increments_the_version(
    client: TestClient, db_session: Session
) -> None:
    team = _create_team(db_session)
    _login_official(client, db_session)
    first = client.post(
        f"/v1/teams/{team.id}/approved-list", json={"entries": _entries()}
    )
    second = client.post(
        f"/v1/teams/{team.id}/approved-list", json={"entries": _entries()}
    )
    assert first.json()["version"] == 1
    assert second.json()["version"] == 2


def test_approved_list_rejects_a_singles_entry_with_a_partner(
    client: TestClient, db_session: Session
) -> None:
    team = _create_team(db_session)
    _login_official(client, db_session)
    bad = [
        {
            "event": "mens_singles",
            "position": 1,
            "player": {"member_id": "M1", "full_name": "M One"},
            "partner": {"member_id": "M2", "full_name": "M Two"},
        }
    ]
    response = client.post(f"/v1/teams/{team.id}/approved-list", json={"entries": bad})
    assert response.status_code == 422


def test_approved_list_rejects_duplicate_slots(
    client: TestClient, db_session: Session
) -> None:
    team = _create_team(db_session)
    _login_official(client, db_session)
    duplicate = [
        {
            "event": "mens_singles",
            "position": 1,
            "player": {"member_id": "M1", "full_name": "M One"},
        },
        {
            "event": "mens_singles",
            "position": 1,
            "player": {"member_id": "M2", "full_name": "M Two"},
        },
    ]
    response = client.post(
        f"/v1/teams/{team.id}/approved-list", json={"entries": duplicate}
    )
    assert response.status_code == 422
