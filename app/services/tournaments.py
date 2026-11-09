import uuid
from datetime import datetime
from typing import Any

from sqlmodel import Session, col, select

from app.models import Tournament
from app.models.enums import Event
from app.rules.inputs import TieFormat
from app.rules.results import ValidationResult
from app.rules.tournament import validate_tournament_config


class TournamentNotFoundError(Exception):
    """Raised when no tournament exists for the given id."""


class TournamentConfigError(Exception):
    """Raised when a tie format and its roster limits are inconsistent.
    Carries the validation result so the API can return its findings.
    """

    def __init__(self, result: ValidationResult) -> None:
        super().__init__("Tournament configuration is invalid")
        self.result = result


def tie_format_of(tournament: Tournament) -> TieFormat:
    """The tie format (matches per event) for a tournament."""
    return TieFormat(
        matches_per_event={
            Event.MENS_SINGLES: tournament.mens_singles_matches,
            Event.WOMENS_SINGLES: tournament.womens_singles_matches,
            Event.MENS_DOUBLES: tournament.mens_doubles_matches,
            Event.WOMENS_DOUBLES: tournament.womens_doubles_matches,
            Event.MIXED_DOUBLES: tournament.mixed_doubles_matches,
        }
    )


def _enforce_config(tournament: Tournament) -> None:
    result = validate_tournament_config(
        tie_format_of(tournament),
        min_male=tournament.min_male,
        max_male=tournament.max_male,
        min_female=tournament.min_female,
        max_female=tournament.max_female,
    )
    if not result.ok:
        raise TournamentConfigError(result)


def create_tournament(db: Session, tournament: Tournament) -> Tournament:
    """Validate and persist a new tournament."""
    _enforce_config(tournament)
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament


def get_or_create_tournament(
    db: Session,
    *,
    name: str,
    starts_at: datetime,
    mens_singles_matches: int,
    womens_singles_matches: int,
    mens_doubles_matches: int,
    womens_doubles_matches: int,
    mixed_doubles_matches: int,
) -> Tournament:
    """Find a tournament by name, or create it (used by the seed)."""
    existing = db.exec(select(Tournament).where(Tournament.name == name)).first()
    if existing is not None:
        return existing
    tournament = Tournament(
        name=name,
        starts_at=starts_at,
        mens_singles_matches=mens_singles_matches,
        womens_singles_matches=womens_singles_matches,
        mens_doubles_matches=mens_doubles_matches,
        womens_doubles_matches=womens_doubles_matches,
        mixed_doubles_matches=mixed_doubles_matches,
    )
    return create_tournament(db, tournament)


def list_tournaments(db: Session) -> list[Tournament]:
    """Every tournament, earliest start first."""
    statement = select(Tournament).order_by(col(Tournament.starts_at))
    return list(db.exec(statement).all())


def get_tournament(db: Session, tournament_id: uuid.UUID) -> Tournament:
    """One tournament, or raise TournamentNotFoundError."""
    tournament = db.get(Tournament, tournament_id)
    if tournament is None:
        raise TournamentNotFoundError
    return tournament


def update_tournament(
    db: Session, tournament_id: uuid.UUID, changes: dict[str, Any]
) -> Tournament:
    """Apply a partial update, re-validate, and persist."""
    tournament = get_tournament(db, tournament_id)
    for field, value in changes.items():
        setattr(tournament, field, value)
    _enforce_config(tournament)
    db.add(tournament)
    db.commit()
    db.refresh(tournament)
    return tournament
