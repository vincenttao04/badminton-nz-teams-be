import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.models import Role, RoleAssignment, User


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


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "name": "Nationals",
        "starts_at": datetime.now(UTC).isoformat(),
        "ends_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "mens_singles_matches": 1,
        "womens_singles_matches": 1,
        "mens_doubles_matches": 1,
        "womens_doubles_matches": 1,
        "mixed_doubles_matches": 1,
    }
    payload.update(overrides)
    return payload


def test_create_requires_authentication(client: TestClient) -> None:
    response = client.post("/v1/tournaments", json=_payload())
    assert response.status_code == 401


def test_create_without_the_official_role_is_forbidden(
    client: TestClient, db_session: Session
) -> None:
    user = User(
        email="plain@example.com",
        full_name="Plain",
        hashed_password=hash_secret("pw"),
    )
    db_session.add(user)
    db_session.commit()
    client.post("/v1/auth/login", json={"email": "plain@example.com", "password": "pw"})
    response = client.post("/v1/tournaments", json=_payload())
    assert response.status_code == 403


def test_create_and_read_a_tournament(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    created = client.post("/v1/tournaments", json=_payload(max_male=2, max_female=2))
    assert created.status_code == 201
    tournament_id = created.json()["id"]

    fetched = client.get(f"/v1/tournaments/{tournament_id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Nationals"


def test_create_rejects_inconsistent_roster_limits(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    # A 1/1/1/1/1 tie needs two males; a maximum of one cannot field it (R-31).
    response = client.post("/v1/tournaments", json=_payload(max_male=1))
    assert response.status_code == 422
    assert response.json()["detail"]["ok"] is False


def test_create_rejects_an_empty_tie_format(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    empty = _payload(
        mens_singles_matches=0,
        womens_singles_matches=0,
        mens_doubles_matches=0,
        womens_doubles_matches=0,
        mixed_doubles_matches=0,
    )
    response = client.post("/v1/tournaments", json=empty)
    assert response.status_code == 422


def test_list_returns_created_tournaments(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    client.post("/v1/tournaments", json=_payload())
    response = client.get("/v1/tournaments")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_patch_updates_the_tie_format(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    created = client.post("/v1/tournaments", json=_payload())
    tournament_id = created.json()["id"]

    updated = client.patch(
        f"/v1/tournaments/{tournament_id}",
        json={"mens_singles_matches": 3},
    )
    assert updated.status_code == 200
    assert updated.json()["mens_singles_matches"] == 3


def test_patch_rejects_an_inconsistent_change(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    created = client.post("/v1/tournaments", json=_payload(max_male=2))
    tournament_id = created.json()["id"]
    # Raising singles to three needs three males, above the max of two.
    response = client.patch(
        f"/v1/tournaments/{tournament_id}",
        json={"mens_singles_matches": 3},
    )
    assert response.status_code == 422


def test_read_missing_tournament_is_404(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    response = client.get(f"/v1/tournaments/{uuid.uuid4()}")
    assert response.status_code == 404


def test_create_requires_an_end_date(client: TestClient, db_session: Session) -> None:
    _login_official(client, db_session)
    payload = _payload()
    del payload["ends_at"]
    response = client.post("/v1/tournaments", json=payload)
    assert response.status_code == 422


def test_create_rejects_an_end_before_the_start(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    starts = datetime.now(UTC)
    ends = starts - timedelta(days=1)
    response = client.post(
        "/v1/tournaments",
        json=_payload(starts_at=starts.isoformat(), ends_at=ends.isoformat()),
    )
    assert response.status_code == 422


def test_patch_rejects_an_end_before_the_start(
    client: TestClient, db_session: Session
) -> None:
    _login_official(client, db_session)
    created = client.post("/v1/tournaments", json=_payload())
    tournament_id = created.json()["id"]
    starts = datetime.fromisoformat(created.json()["starts_at"])
    response = client.patch(
        f"/v1/tournaments/{tournament_id}",
        json={"ends_at": (starts - timedelta(days=1)).isoformat()},
    )
    assert response.status_code == 422
