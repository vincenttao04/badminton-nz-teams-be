import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.models import Association, Role, RoleAssignment, Team, User

_OPENS_AT = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
_CLOSES_AT = _OPENS_AT + timedelta(hours=2)


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


def _create_tournament(client: TestClient) -> str:
    response = client.post(
        "/v1/tournaments",
        json={
            "name": "Nationals",
            "starts_at": _OPENS_AT.isoformat(),
            "ends_at": _CLOSES_AT.isoformat(),
            "mens_singles_matches": 1,
            "womens_singles_matches": 1,
            "mens_doubles_matches": 1,
            "womens_doubles_matches": 1,
            "mixed_doubles_matches": 1,
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def _open_slot(
    client: TestClient, tournament_id: str, **body: object
) -> dict[str, object]:
    response = client.post(f"/v1/tournaments/{tournament_id}/slots", json=body)
    assert response.status_code == 201, response.text
    slot: dict[str, object] = response.json()
    return slot


def _create_team(db_session: Session, tournament_id: str, name: str) -> str:
    association = Association(name=f"Assoc for {name}")
    db_session.add(association)
    db_session.commit()
    assert association.id is not None
    team = Team(
        name=name,
        association_id=association.id,
        tournament_id=uuid.UUID(tournament_id),
    )
    db_session.add(team)
    db_session.commit()
    assert team.id is not None
    return str(team.id)


def test_open_requires_authentication(client: TestClient) -> None:
    response = client.post(f"/v1/tournaments/{uuid.uuid4()}/slots", json={})
    assert response.status_code == 401


def test_open_without_the_official_role_is_forbidden(
    client: TestClient, db_session: Session
) -> None:
    _login_plain(client, db_session)
    response = client.post(f"/v1/tournaments/{uuid.uuid4()}/slots", json={})
    assert response.status_code == 403


def test_open_a_slot_defaults_to_open_now(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(client, tournament_id)
    assert slot["status"] == "open"
    assert slot["tournament_id"] == tournament_id
    assert slot["opens_at"] is not None
    assert slot["closes_at"] is None


def test_open_a_slot_with_a_cut_off(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(
        client,
        tournament_id,
        opens_at=_OPENS_AT.isoformat(),
        closes_at=_CLOSES_AT.isoformat(),
    )
    assert slot["closes_at"] is not None


def test_open_rejects_a_cut_off_before_it_opens(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    response = client.post(
        f"/v1/tournaments/{tournament_id}/slots",
        json={
            "opens_at": _OPENS_AT.isoformat(),
            "closes_at": (_OPENS_AT - timedelta(minutes=1)).isoformat(),
        },
    )
    assert response.status_code == 422


def test_open_on_a_missing_tournament_is_404(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.post(f"/v1/tournaments/{uuid.uuid4()}/slots", json={})
    assert response.status_code == 404


def test_list_returns_a_tournaments_slots(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    _open_slot(client, tournament_id)
    _open_slot(client, tournament_id)
    response = client.get(f"/v1/tournaments/{tournament_id}/slots")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_on_a_missing_tournament_is_404(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.get(f"/v1/tournaments/{uuid.uuid4()}/slots")
    assert response.status_code == 404


def test_read_a_slot(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(client, tournament_id)
    response = client.get(f"/v1/slots/{slot['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == slot["id"]


def test_read_a_missing_slot_is_404(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    response = client.get(f"/v1/slots/{uuid.uuid4()}")
    assert response.status_code == 404


def test_close_a_slot(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(client, tournament_id)
    response = client.patch(f"/v1/slots/{slot['id']}", json={"status": "closed"})
    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_reopen_a_closed_slot(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(client, tournament_id)
    client.patch(f"/v1/slots/{slot['id']}", json={"status": "closed"})
    response = client.patch(f"/v1/slots/{slot['id']}", json={"status": "open"})
    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_extend_a_cut_off(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(
        client,
        tournament_id,
        opens_at=_OPENS_AT.isoformat(),
        closes_at=_CLOSES_AT.isoformat(),
    )
    later = (_CLOSES_AT + timedelta(hours=1)).isoformat()
    response = client.patch(f"/v1/slots/{slot['id']}", json={"closes_at": later})
    assert response.status_code == 200
    assert datetime.fromisoformat(
        response.json()["closes_at"]
    ) == datetime.fromisoformat(later)


def test_reopen_and_extend_in_one_step(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(
        client,
        tournament_id,
        opens_at=_OPENS_AT.isoformat(),
        closes_at=_CLOSES_AT.isoformat(),
    )
    client.patch(f"/v1/slots/{slot['id']}", json={"status": "closed"})
    later = (_CLOSES_AT + timedelta(hours=3)).isoformat()
    response = client.patch(
        f"/v1/slots/{slot['id']}", json={"status": "open", "closes_at": later}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "open"
    assert datetime.fromisoformat(body["closes_at"]) == datetime.fromisoformat(later)


def test_extend_rejects_a_cut_off_before_it_opens(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(client, tournament_id, opens_at=_OPENS_AT.isoformat())
    response = client.patch(
        f"/v1/slots/{slot['id']}",
        json={"closes_at": (_OPENS_AT - timedelta(minutes=1)).isoformat()},
    )
    assert response.status_code == 422


def test_an_empty_patch_is_rejected(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(client, tournament_id)
    response = client.patch(f"/v1/slots/{slot['id']}", json={})
    assert response.status_code == 422


def test_patch_without_the_official_role_is_forbidden(
    client: TestClient, db_session: Session
) -> None:
    _login_plain(client, db_session)
    response = client.patch(f"/v1/slots/{uuid.uuid4()}", json={"status": "closed"})
    assert response.status_code == 403


def test_patch_a_missing_slot_is_404(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    response = client.patch(f"/v1/slots/{uuid.uuid4()}", json={"status": "closed"})
    assert response.status_code == 404


def test_a_slot_admits_all_teams_by_default(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    slot = _open_slot(client, tournament_id)
    response = client.get(f"/v1/slots/{slot['id']}/teams")
    assert response.status_code == 200
    body = response.json()
    assert body["admits_all"] is True
    assert body["teams"] == []


def test_open_a_slot_for_selected_teams(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    team_id = _create_team(db_session, tournament_id, "Northern")
    slot = _open_slot(client, tournament_id, team_ids=[team_id])
    response = client.get(f"/v1/slots/{slot['id']}/teams")
    assert response.status_code == 200
    body = response.json()
    assert body["admits_all"] is False
    assert [team["id"] for team in body["teams"]] == [team_id]


def test_open_rejects_a_team_from_another_tournament(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    other_tournament_id = _create_tournament(client)
    other_team_id = _create_team(db_session, other_tournament_id, "Outsider")
    response = client.post(
        f"/v1/tournaments/{tournament_id}/slots",
        json={"team_ids": [other_team_id]},
    )
    assert response.status_code == 422


def test_open_rejects_an_unknown_team(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    response = client.post(
        f"/v1/tournaments/{tournament_id}/slots",
        json={"team_ids": [str(uuid.uuid4())]},
    )
    assert response.status_code == 422


def test_set_the_admitted_teams_on_a_slot(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    team_id = _create_team(db_session, tournament_id, "Central")
    slot = _open_slot(client, tournament_id)
    response = client.patch(f"/v1/slots/{slot['id']}", json={"team_ids": [team_id]})
    assert response.status_code == 200
    teams = client.get(f"/v1/slots/{slot['id']}/teams").json()
    assert teams["admits_all"] is False
    assert [team["id"] for team in teams["teams"]] == [team_id]


def test_clearing_the_teams_admits_all_again(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    team_id = _create_team(db_session, tournament_id, "Southern")
    slot = _open_slot(client, tournament_id, team_ids=[team_id])
    response = client.patch(f"/v1/slots/{slot['id']}", json={"team_ids": []})
    assert response.status_code == 200
    teams = client.get(f"/v1/slots/{slot['id']}/teams").json()
    assert teams["admits_all"] is True
    assert teams["teams"] == []


def test_reopen_for_specific_teams_in_one_step(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    team_id = _create_team(db_session, tournament_id, "Eastern")
    slot = _open_slot(client, tournament_id)
    client.patch(f"/v1/slots/{slot['id']}", json={"status": "closed"})
    response = client.patch(
        f"/v1/slots/{slot['id']}",
        json={"status": "open", "team_ids": [team_id]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "open"
    teams = client.get(f"/v1/slots/{slot['id']}/teams").json()
    assert [team["id"] for team in teams["teams"]] == [team_id]


def test_patch_rejects_a_team_from_another_tournament(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    tournament_id = _create_tournament(client)
    other_tournament_id = _create_tournament(client)
    other_team_id = _create_team(db_session, other_tournament_id, "Stranger")
    slot = _open_slot(client, tournament_id)
    response = client.patch(
        f"/v1/slots/{slot['id']}", json={"team_ids": [other_team_id]}
    )
    assert response.status_code == 422


def test_teams_on_a_missing_slot_is_404(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.get(f"/v1/slots/{uuid.uuid4()}/teams")
    assert response.status_code == 404
