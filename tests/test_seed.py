from sqlmodel import Session, select

from app.auth.hashing import verify_secret
from app.config import get_settings
from app.models import Association, Player, RankedTeamList, Team, Tournament
from app.seed import seed


def test_seed_is_idempotent(db_session: Session) -> None:
    first = seed(db_session)
    second = seed(db_session)

    assert first.id == second.id
    assert len(db_session.exec(select(Association)).all()) == 1
    assert len(db_session.exec(select(Tournament)).all()) == 1
    assert len(db_session.exec(select(Team)).all()) == 1
    assert len(db_session.exec(select(RankedTeamList)).all()) == 1
    assert len(db_session.exec(select(Player)).all()) == 6


def test_seed_sets_a_working_demo_access_code(db_session: Session) -> None:
    team = seed(db_session)
    assert team.access_details is not None
    assert verify_secret(get_settings().seed_team_access_code, team.access_details)
