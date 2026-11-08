import secrets
import uuid

from sqlmodel import Session

from app.auth.hashing import hash_secret
from app.models import Team

_ACCESS_CODE_BYTES = 12


class TeamNotFoundError(Exception):
    """Raised when no team exists for the given id."""


def get_team(db: Session, team_id: uuid.UUID) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise TeamNotFoundError
    return team


def set_access_details(db: Session, team: Team, access_code: str) -> None:
    """Store the Argon2 hash of an access code on the team."""
    team.access_details = hash_secret(access_code)
    db.add(team)
    db.commit()


def issue_access_details(db: Session, team_id: uuid.UUID) -> str:
    """Generate a new access code for a team, store its hash, and return it once."""
    team = get_team(db, team_id)
    access_code = secrets.token_urlsafe(_ACCESS_CODE_BYTES)
    set_access_details(db, team, access_code)
    return access_code
