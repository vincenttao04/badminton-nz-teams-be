import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.models import Association, Role, RoleAssignment, Team, Tournament, User
from app.models.enums import Event
from app.rules.lineup import (
    RULE_FROM_APPROVED_LIST,
    RULE_MATCH_COUNTS,
    RULE_ONE_MATCH_PER_EVENT,
    RULE_RELATIVE_ORDER,
)
from app.services.approved_lists import (
    ApprovedListEntryInput,
    PlayerInput,
    create_approved_list,
)

_ACCESS_CODE = "team-access-code"


def _make_team(db_session: Session, *, singles: int = 2, doubles: int = 1) -> Team:
    association = Association(name="Waikato")
    tournament = Tournament(
        name="Nationals",
        starts_at=datetime.now(UTC),
        mens_singles_matches=singles,
        womens_singles_matches=0,
        mens_doubles_matches=doubles,
        womens_doubles_matches=0,
        mixed_doubles_matches=0,
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
        access_details=hash_secret(_ACCESS_CODE),
    )
    db_session.add(team)
    db_session.commit()
    assert team.id is not None
    return team


def _seed_list(db_session: Session, team_id: uuid.UUID) -> None:
    create_approved_list(
        db_session,
        team_id,
        [
            ApprovedListEntryInput(
                event=Event.MENS_SINGLES,
                position=1,
                player=PlayerInput("M1", "Ana"),
                partner=None,
            ),
            ApprovedListEntryInput(
                event=Event.MENS_SINGLES,
                position=2,
                player=PlayerInput("M2", "Bea"),
                partner=None,
            ),
            ApprovedListEntryInput(
                event=Event.MENS_SINGLES,
                position=3,
                player=PlayerInput("M3", "Cat"),
                partner=None,
            ),
            ApprovedListEntryInput(
                event=Event.MENS_DOUBLES,
                position=1,
                player=PlayerInput("M4", "Dan"),
                partner=PlayerInput("M5", "Eve"),
            ),
        ],
    )


def _login_team(client: TestClient, team: Team) -> None:
    response = client.post(
        "/v1/auth/team-login",
        json={"team_id": str(team.id), "access_code": _ACCESS_CODE},
    )
    assert response.status_code == 204


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


def _units(client: TestClient) -> list[dict[str, Any]]:
    response = client.get("/v1/lineup/context")
    assert response.status_code == 200, response.text
    approved_list: list[dict[str, Any]] = response.json()["approved_list"]
    return approved_list


def _player_id(units: list[dict[str, Any]], event: str, position: int) -> str:
    for unit in units:
        if unit["event"] == event and unit["position"] == position:
            player_id: str = unit["player"]["id"]
            return player_id
    raise AssertionError(f"no {event} unit at position {position}")


def _partner_id(units: list[dict[str, Any]], event: str, position: int) -> str:
    for unit in units:
        if unit["event"] == event and unit["position"] == position:
            partner_id: str = unit["partner"]["id"]
            return partner_id
    raise AssertionError(f"no {event} unit at position {position}")


def _valid_entries(units: list[dict[str, Any]]) -> list[dict[str, object]]:
    return [
        {
            "event": "mens_singles",
            "position": 1,
            "player_id": _player_id(units, "mens_singles", 1),
        },
        {
            "event": "mens_singles",
            "position": 2,
            "player_id": _player_id(units, "mens_singles", 2),
        },
        {
            "event": "mens_doubles",
            "position": 1,
            "player_id": _player_id(units, "mens_doubles", 1),
            "partner_id": _partner_id(units, "mens_doubles", 1),
        },
    ]


def _check(client: TestClient, entries: list[dict[str, object]]) -> dict[str, Any]:
    response = client.post("/v1/lineup/check", json={"entries": entries})
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()
    return result


def _rules(result: dict[str, Any]) -> set[str]:
    return {finding["rule"] for finding in result["findings"]}


def test_context_returns_tie_format_and_approved_list(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    _login_team(client, team)
    response = client.get("/v1/lineup/context")
    assert response.status_code == 200
    body = response.json()
    assert body["tie_format"]["mens_singles"] == 2
    assert body["tie_format"]["mens_doubles"] == 1
    assert len(body["approved_list"]) == 4


def test_check_passes_a_valid_lineup(client: TestClient, db_session: Session) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    _login_team(client, team)
    result = _check(client, _valid_entries(_units(client)))
    assert result["ok"] is True
    assert result["findings"] == []


def test_check_flags_an_off_list_player(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    _login_team(client, team)
    entries = _valid_entries(_units(client))
    entries[1]["player_id"] = str(uuid.uuid4())
    result = _check(client, entries)
    assert result["ok"] is False
    assert RULE_FROM_APPROVED_LIST in _rules(result)


def test_check_flags_a_player_twice_in_one_event(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    _login_team(client, team)
    entries = _valid_entries(_units(client))
    entries[1]["player_id"] = entries[0]["player_id"]
    result = _check(client, entries)
    assert result["ok"] is False
    assert RULE_ONE_MATCH_PER_EVENT in _rules(result)


def test_check_flags_an_out_of_order_lineup(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    _login_team(client, team)
    entries = _valid_entries(_units(client))
    entries[0]["player_id"], entries[1]["player_id"] = (
        entries[1]["player_id"],
        entries[0]["player_id"],
    )
    result = _check(client, entries)
    assert result["ok"] is False
    assert RULE_RELATIVE_ORDER in _rules(result)


def test_check_flags_wrong_match_counts(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    _login_team(client, team)
    entries = _valid_entries(_units(client))[:2]  # drops the doubles match
    result = _check(client, entries)
    assert result["ok"] is False
    assert RULE_MATCH_COUNTS in _rules(result)


def test_context_without_an_approved_list_is_422(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    _login_team(client, team)
    response = client.get("/v1/lineup/context")
    assert response.status_code == 422


def test_check_without_an_approved_list_is_422(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    _login_team(client, team)
    response = client.post("/v1/lineup/check", json={"entries": []})
    assert response.status_code == 422


def test_context_requires_a_team_session(client: TestClient) -> None:
    response = client.get("/v1/lineup/context")
    assert response.status_code == 401


def test_an_official_cannot_use_the_lineup_endpoints(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.get("/v1/lineup/context")
    assert response.status_code == 403
