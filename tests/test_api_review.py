import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.models import (
    Association,
    LineupStatus,
    Role,
    RoleAssignment,
    RoundSlot,
    RoundSlotStatus,
    SlotTeam,
    Team,
    TieLineup,
    Tournament,
    User,
)


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


def _login_plain(client: TestClient, db_session: Session) -> None:
    user = User(
        email="plain@example.com",
        full_name="Plain",
        hashed_password=hash_secret("pw"),
    )
    db_session.add(user)
    db_session.commit()
    client.post("/v1/auth/login", json={"email": "plain@example.com", "password": "pw"})


def _make_tournament(db_session: Session) -> uuid.UUID:
    tournament = Tournament(
        name="Nationals",
        starts_at=datetime.now(UTC),
        ends_at=datetime(2030, 1, 1, tzinfo=UTC),
        mens_singles_matches=1,
        womens_singles_matches=0,
        mens_doubles_matches=0,
        womens_doubles_matches=0,
        mixed_doubles_matches=0,
    )
    db_session.add(tournament)
    db_session.commit()
    assert tournament.id is not None
    return tournament.id


def _make_team(db_session: Session, tournament_id: uuid.UUID, name: str) -> uuid.UUID:
    association = Association(name=f"Assoc {name}")
    db_session.add(association)
    db_session.commit()
    assert association.id is not None
    team = Team(
        name=name,
        association_id=association.id,
        tournament_id=tournament_id,
        access_details=hash_secret("x"),
    )
    db_session.add(team)
    db_session.commit()
    assert team.id is not None
    return team.id


def _open_slot(db_session: Session, tournament_id: uuid.UUID) -> uuid.UUID:
    slot = RoundSlot(
        tournament_id=tournament_id,
        status=RoundSlotStatus.OPEN,
        opens_at=datetime.now(UTC),
    )
    db_session.add(slot)
    db_session.commit()
    assert slot.id is not None
    return slot.id


def _submit(
    db_session: Session,
    slot_id: uuid.UUID,
    team_id: uuid.UUID,
    status: LineupStatus = LineupStatus.SUBMITTED,
) -> None:
    db_session.add(
        TieLineup(
            round_slot_id=slot_id,
            team_id=team_id,
            version=1,
            status=status,
        )
    )
    db_session.commit()


def _find(submissions: list[dict[str, Any]], team_id: uuid.UUID) -> dict[str, Any]:
    for submission in submissions:
        if submission["team_id"] == str(team_id):
            return submission
    raise AssertionError(f"no submission for team {team_id}")


def test_slot_submissions_shows_submitted_and_outstanding(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _make_tournament(db_session)
    team_a = _make_team(db_session, tournament_id, "Alpha")
    team_b = _make_team(db_session, tournament_id, "Bravo")
    slot_id = _open_slot(db_session, tournament_id)
    _submit(db_session, slot_id, team_a)

    response = client.get(f"/v1/slots/{slot_id}/submissions")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "open"
    assert len(body["submissions"]) == 2

    submitted = _find(body["submissions"], team_a)
    assert submitted["submitted"] is True
    assert submitted["version"] == 1
    assert submitted["lineup_status"] == "submitted"
    assert submitted["submitted_at"] is not None

    outstanding = _find(body["submissions"], team_b)
    assert outstanding["submitted"] is False
    assert outstanding["lineup_id"] is None


def test_slot_submissions_respects_the_allowlist(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _make_tournament(db_session)
    team_a = _make_team(db_session, tournament_id, "Alpha")
    _make_team(db_session, tournament_id, "Bravo")
    slot_id = _open_slot(db_session, tournament_id)
    db_session.add(SlotTeam(round_slot_id=slot_id, team_id=team_a))
    db_session.commit()

    response = client.get(f"/v1/slots/{slot_id}/submissions")
    assert response.status_code == 200
    submissions = response.json()["submissions"]
    assert len(submissions) == 1
    assert submissions[0]["team_id"] == str(team_a)


def test_dashboard_lists_slots_with_submissions(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _make_tournament(db_session)
    team_a = _make_team(db_session, tournament_id, "Alpha")
    slot_one = _open_slot(db_session, tournament_id)
    slot_two = _open_slot(db_session, tournament_id)
    _submit(db_session, slot_one, team_a)

    response = client.get(f"/v1/tournaments/{tournament_id}/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert len(body["slots"]) == 2
    slots_by_id = {slot["id"]: slot for slot in body["slots"]}
    assert slots_by_id[str(slot_one)]["submissions"][0]["submitted"] is True
    assert slots_by_id[str(slot_two)]["submissions"][0]["submitted"] is False


def test_slot_submissions_requires_authentication(client: TestClient) -> None:
    response = client.get(f"/v1/slots/{uuid.uuid4()}/submissions")
    assert response.status_code == 401


def test_slot_submissions_requires_the_official_role(
    client: TestClient, db_session: Session
) -> None:
    _login_plain(client, db_session)
    response = client.get(f"/v1/slots/{uuid.uuid4()}/submissions")
    assert response.status_code == 403


def test_slot_submissions_missing_slot_is_404(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.get(f"/v1/slots/{uuid.uuid4()}/submissions")
    assert response.status_code == 404


def test_dashboard_missing_tournament_is_404(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.get(f"/v1/tournaments/{uuid.uuid4()}/dashboard")
    assert response.status_code == 404
