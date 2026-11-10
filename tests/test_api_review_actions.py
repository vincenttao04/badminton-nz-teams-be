import uuid
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.auth.hashing import hash_secret
from app.models import (
    Association,
    LineupEntry,
    LineupStatus,
    Player,
    Role,
    RoleAssignment,
    RoundSlot,
    RoundSlotStatus,
    Team,
    TieLineup,
    Tournament,
    User,
)
from app.models.enums import Event
from app.services.approved_lists import (
    ApprovedListEntryInput,
    PlayerInput,
    create_approved_list,
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


def _make_team(db_session: Session) -> Team:
    association = Association(name="Waikato")
    tournament = Tournament(
        name="Nationals",
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
        name="Team A",
        association_id=association.id,
        tournament_id=tournament.id,
        access_details=hash_secret("x"),
    )
    db_session.add(team)
    db_session.commit()
    assert team.id is not None
    return team


def _seed_list(db_session: Session, team_id: uuid.UUID) -> dict[str, uuid.UUID]:
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
    players: dict[str, uuid.UUID] = {}
    for player in db_session.exec(select(Player)).all():
        assert player.id is not None
        players[player.member_id] = player.id
    return players


def _slot(
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


def _lineup(
    db_session: Session,
    slot_id: uuid.UUID,
    team_id: uuid.UUID,
    players: dict[str, uuid.UUID],
    *,
    valid: bool = True,
    status: LineupStatus = LineupStatus.SUBMITTED,
    version: int = 1,
) -> uuid.UUID:
    lineup = TieLineup(
        round_slot_id=slot_id, team_id=team_id, version=version, status=status
    )
    db_session.add(lineup)
    db_session.commit()
    assert lineup.id is not None
    entries = [
        LineupEntry(
            tie_lineup_id=lineup.id,
            event=Event.MENS_SINGLES,
            position=1,
            player_id=players["M1"],
        ),
        LineupEntry(
            tie_lineup_id=lineup.id,
            event=Event.MENS_SINGLES,
            position=2,
            player_id=players["M2"],
        ),
    ]
    if valid:
        entries.append(
            LineupEntry(
                tie_lineup_id=lineup.id,
                event=Event.MENS_DOUBLES,
                position=1,
                player_id=players["M3"],
                partner_id=players["M4"],
            )
        )
    for entry in entries:
        db_session.add(entry)
    db_session.commit()
    return lineup.id


def test_lineup_detail_shows_entries_and_passes(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(db_session, slot_id, team.id, players)

    response = client.get(f"/v1/lineups/{lineup_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["team_name"] == "Team A"
    assert body["status"] == "submitted"
    assert len(body["entries"]) == 3
    assert body["entries"][0]["player"]["full_name"] == "Ana"
    assert body["result"]["ok"] is True


def test_lineup_detail_shows_flags(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(
        db_session, slot_id, team.id, players, valid=False, status=LineupStatus.FLAGGED
    )

    response = client.get(f"/v1/lineups/{lineup_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["ok"] is False
    assert len(body["result"]["findings"]) >= 1


def test_lineup_detail_missing_is_404(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    response = client.get(f"/v1/lineups/{uuid.uuid4()}")
    assert response.status_code == 404


def test_approve_a_lineup(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(db_session, slot_id, team.id, players)

    response = client.post(f"/v1/lineups/{lineup_id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_flag_a_lineup(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(db_session, slot_id, team.id, players)

    response = client.post(f"/v1/lineups/{lineup_id}/flag")
    assert response.status_code == 200
    assert response.json()["status"] == "flagged"


def test_approve_a_superseded_lineup_is_409(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(
        db_session, slot_id, team.id, players, status=LineupStatus.SUPERSEDED
    )

    response = client.post(f"/v1/lineups/{lineup_id}/approve")
    assert response.status_code == 409


def test_mark_copied_requires_approval(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(db_session, slot_id, team.id, players)

    response = client.post(f"/v1/lineups/{lineup_id}/copied")
    assert response.status_code == 409


def test_mark_copied_after_approval(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(db_session, slot_id, team.id, players)

    client.post(f"/v1/lineups/{lineup_id}/approve")
    response = client.post(f"/v1/lineups/{lineup_id}/copied")
    assert response.status_code == 200
    assert response.json()["copied_at"] is not None


def test_review_requires_the_official_role(
    client: TestClient, db_session: Session
) -> None:
    _login_plain(client, db_session)
    response = client.get(f"/v1/lineups/{uuid.uuid4()}")
    assert response.status_code == 403


def test_closing_a_slot_finalizes_the_latest_lineup(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    # Stored as flagged, but the entries are actually valid.
    lineup_id = _lineup(
        db_session, slot_id, team.id, players, status=LineupStatus.FLAGGED
    )

    close = client.patch(f"/v1/slots/{slot_id}", json={"status": "closed"})
    assert close.status_code == 200
    detail = client.get(f"/v1/lineups/{lineup_id}")
    assert detail.json()["status"] == "submitted"


def test_closing_a_slot_preserves_an_approved_lineup(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    team = _make_team(db_session)
    assert team.id is not None
    players = _seed_list(db_session, team.id)
    slot_id = _slot(db_session, team.tournament_id)
    lineup_id = _lineup(
        db_session, slot_id, team.id, players, status=LineupStatus.APPROVED
    )

    client.patch(f"/v1/slots/{slot_id}", json={"status": "closed"})
    detail = client.get(f"/v1/lineups/{lineup_id}")
    assert detail.json()["status"] == "approved"
