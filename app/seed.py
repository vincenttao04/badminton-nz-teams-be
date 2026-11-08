from datetime import UTC, datetime

from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine
from app.models import Event, Team
from app.services.approved_lists import (
    ApprovedListEntryInput,
    PlayerInput,
    create_approved_list,
    team_has_approved_list,
)
from app.services.associations import get_or_create_association
from app.services.teams import get_or_create_team, set_access_details
from app.services.tournaments import get_or_create_tournament

"""Idempotent first-release seed (US-44, TSK-17).

Stands up one tournament with a team that can log in and has an approved list,
standing in for what Phase A will later produce.

Safe to run repeatedly: uv run python -m app.seed
"""


def _demo_entries() -> list[ApprovedListEntryInput]:
    m1 = PlayerInput("DEMO-M1", "Demo Man One")
    m2 = PlayerInput("DEMO-M2", "Demo Man Two")
    m3 = PlayerInput("DEMO-M3", "Demo Man Three")
    f1 = PlayerInput("DEMO-F1", "Demo Woman One")
    f2 = PlayerInput("DEMO-F2", "Demo Woman Two")
    f3 = PlayerInput("DEMO-F3", "Demo Woman Three")
    return [
        ApprovedListEntryInput(Event.MENS_SINGLES, 1, m1, None),
        ApprovedListEntryInput(Event.WOMENS_SINGLES, 1, f1, None),
        ApprovedListEntryInput(Event.MENS_DOUBLES, 1, m2, m3),
        ApprovedListEntryInput(Event.WOMENS_DOUBLES, 1, f2, f3),
        ApprovedListEntryInput(Event.MIXED_DOUBLES, 1, m1, f1),
    ]


def seed(db: Session) -> Team:
    """Create, or reuse, the demo tournament, team, access code, and list."""
    association = get_or_create_association(db, "Demo Association")
    assert association.id is not None
    tournament = get_or_create_tournament(
        db,
        name="Demo Open",
        starts_at=datetime(2026, 12, 1, tzinfo=UTC),
        mens_singles_matches=1,
        womens_singles_matches=1,
        mens_doubles_matches=1,
        womens_doubles_matches=1,
        mixed_doubles_matches=1,
    )
    assert tournament.id is not None
    team = get_or_create_team(
        db,
        name="Demo Team",
        association_id=association.id,
        tournament_id=tournament.id,
    )
    assert team.id is not None
    if team.access_details is None:
        set_access_details(db, team, get_settings().seed_team_access_code)
    if not team_has_approved_list(db, team.id):
        create_approved_list(db, team.id, _demo_entries())
    return team


def main() -> None:
    with Session(get_engine()) as db:
        team = seed(db)
    settings = get_settings()
    print("Seed complete.")
    print(f"  Team:        {team.name} ({team.id})")
    print(f"  Access code: {settings.seed_team_access_code}")
    print("  Log in via POST /v1/auth/team-login with that team_id and access_code.")


if __name__ == "__main__":
    main()
