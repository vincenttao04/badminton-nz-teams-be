import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.hashing import hash_secret
from app.models import (
    Association,
    Player,
    RoundSlot,
    RoundSlotStatus,
    SlotTeam,
    Team,
    TieLineup,
    Tournament,
)
from app.models.enums import Event
from app.services.approved_lists import (
    ApprovedListEntryInput,
    PlayerInput,
    create_approved_list,
)

_ACCESS_CODE = "team-access-code"


def _make_team(db_session: Session, name: str = "Team A") -> Team:
    association = Association(name=f"Assoc {name}")
    tournament = Tournament(
        name=f"Nationals {name}",
        starts_at=datetime.now(UTC),
        ends_at=datetime(2030, 1, 1, tzinfo=UTC),
        mens_singles_matches=2,
        womens_singles_matches=0,
        mens_doubles_matches=1,
        womens_doubles_matches=0,
        mixed_doubles_matches=0,
    )
    db_session.add(association)
    db_session.add(tournament)
    db_session.commit()
    assert association.id is not None
    assert tournament.id is not None
    team = Team(
        name=name,
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
                event=Event.MENS_DOUBLES,
                position=1,
                player=PlayerInput("M3", "Dan"),
                partner=PlayerInput("M4", "Eve"),
            ),
        ],
    )


def _open_slot(
    db_session: Session,
    tournament_id: uuid.UUID,
    status: RoundSlotStatus = RoundSlotStatus.OPEN,
) -> uuid.UUID:
    slot = RoundSlot(
        tournament_id=tournament_id,
        status=status,
        opens_at=datetime.now(UTC),
    )
    db_session.add(slot)
    db_session.commit()
    assert slot.id is not None
    return slot.id


def _login_team(client: TestClient, team: Team) -> None:
    response = client.post(
        "/v1/auth/team-login",
        json={"team_id": str(team.id), "access_code": _ACCESS_CODE},
    )
    assert response.status_code == 204


def _valid_entries(client: TestClient) -> list[dict[str, object]]:
    response = client.get("/v1/lineup/context")
    assert response.status_code == 200, response.text
    units: list[dict[str, Any]] = response.json()["approved_list"]

    def player_id(event: str, position: int) -> str:
        for unit in units:
            if unit["event"] == event and unit["position"] == position:
                found: str = unit["player"]["id"]
                return found
        raise AssertionError(f"no {event} unit at position {position}")

    def partner_id(event: str, position: int) -> str:
        for unit in units:
            if unit["event"] == event and unit["position"] == position:
                found: str = unit["partner"]["id"]
                return found
        raise AssertionError(f"no {event} unit at position {position}")

    return [
        {
            "event": "mens_singles",
            "position": 1,
            "player_id": player_id("mens_singles", 1),
        },
        {
            "event": "mens_singles",
            "position": 2,
            "player_id": player_id("mens_singles", 2),
        },
        {
            "event": "mens_doubles",
            "position": 1,
            "player_id": player_id("mens_doubles", 1),
            "partner_id": partner_id("mens_doubles", 1),
        },
    ]


def _submit(
    client: TestClient, slot_id: uuid.UUID, entries: list[dict[str, object]]
) -> Any:
    return client.post(
        "/v1/lineup/submit",
        json={"round_slot_id": str(slot_id), "entries": entries},
    )


def test_submit_records_a_valid_lineup(client: TestClient, db_session: Session) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    slot_id = _open_slot(db_session, team.tournament_id)
    _login_team(client, team)
    response = _submit(client, slot_id, _valid_entries(client))
    assert response.status_code == 201
    body = response.json()
    assert body["version"] == 1
    assert body["status"] == "submitted"
    assert body["submitted_at"] is not None
    assert body["result"]["ok"] is True


def test_submit_flags_a_lineup_that_fails_the_check(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    slot_id = _open_slot(db_session, team.tournament_id)
    stranger = Player(member_id="X9", full_name="Stranger")
    db_session.add(stranger)
    db_session.commit()
    assert stranger.id is not None
    _login_team(client, team)
    entries = _valid_entries(client)
    entries[1]["player_id"] = str(stranger.id)  # a real player, off the list
    response = _submit(client, slot_id, entries)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "flagged"
    assert body["result"]["ok"] is False


def test_submit_with_an_unknown_player_is_422(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    slot_id = _open_slot(db_session, team.tournament_id)
    _login_team(client, team)
    entries = _valid_entries(client)
    entries[1]["player_id"] = str(uuid.uuid4())  # not a real player
    response = _submit(client, slot_id, entries)
    assert response.status_code == 422


def test_resubmit_supersedes_the_previous_version(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    slot_id = _open_slot(db_session, team.tournament_id)
    _login_team(client, team)
    entries = _valid_entries(client)
    _submit(client, slot_id, entries)
    second = _submit(client, slot_id, entries)
    assert second.status_code == 201
    assert second.json()["version"] == 2

    rows = db_session.exec(
        select(TieLineup).where(
            TieLineup.round_slot_id == slot_id,
            TieLineup.team_id == team.id,
        )
    ).all()
    by_version = {row.version: row.status.value for row in rows}
    assert by_version[1] == "superseded"
    assert by_version[2] == "submitted"


def test_submit_to_a_closed_slot_is_409(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    slot_id = _open_slot(db_session, team.tournament_id, RoundSlotStatus.CLOSED)
    _login_team(client, team)
    response = _submit(client, slot_id, _valid_entries(client))
    assert response.status_code == 409


def test_submit_when_not_admitted_is_403(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    slot_id = _open_slot(db_session, team.tournament_id)
    other = _make_team(db_session, name="Team B")
    assert other.id is not None
    # An allowlist that admits another team excludes ours.
    db_session.add(SlotTeam(round_slot_id=slot_id, team_id=other.id))
    db_session.commit()
    _login_team(client, team)
    response = _submit(client, slot_id, _valid_entries(client))
    assert response.status_code == 403


def test_submit_with_a_wrong_shaped_entry_is_422(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    slot_id = _open_slot(db_session, team.tournament_id)
    _login_team(client, team)
    entries = _valid_entries(client)
    entries[0]["partner_id"] = str(uuid.uuid4())  # a singles entry with a partner
    response = _submit(client, slot_id, entries)
    assert response.status_code == 422


def test_submit_without_an_approved_list_is_422(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    slot_id = _open_slot(db_session, team.tournament_id)
    _login_team(client, team)
    response = _submit(client, slot_id, [])
    assert response.status_code == 422


def test_submit_into_another_tournaments_slot_is_404(
    client: TestClient, db_session: Session
) -> None:
    team = _make_team(db_session)
    assert team.id is not None
    _seed_list(db_session, team.id)
    other = _make_team(db_session, name="Team B")
    other_slot_id = _open_slot(db_session, other.tournament_id)
    _login_team(client, team)
    response = _submit(client, other_slot_id, _valid_entries(client))
    assert response.status_code == 404


def test_submit_requires_a_team_session(client: TestClient) -> None:
    response = client.post(
        "/v1/lineup/submit",
        json={"round_slot_id": str(uuid.uuid4()), "entries": []},
    )
    assert response.status_code == 401
