import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models import (
    LineupEntry,
    LineupStatus,
    Player,
    RoundSlot,
    Team,
    TieLineup,
)
from app.models.enums import Event
from app.rules import Entry, Lineup
from app.rules.results import ValidationResult
from app.services.lineups import check_team_lineup
from app.services.slots import list_admitted_teams
from app.services.tournaments import get_tournament

# Canonical event order (as a tie is laid out), not the stored string order.
_EVENT_ORDER = {event: index for index, event in enumerate(Event)}


class LineupNotFoundError(Exception):
    """Raised when no tie lineup exists for the given id."""


class LineupActionError(Exception):
    """Raised when an action does not apply to a lineup's current state."""


@dataclass(frozen=True)
class TeamSubmission:
    """An admitted team and its latest submission, or none if outstanding."""

    team: Team
    lineup: TieLineup | None


@dataclass(frozen=True)
class LineupEntryDetail:
    event: Event
    position: int
    player: Player
    partner: Player | None


@dataclass(frozen=True)
class LineupDetail:
    lineup: TieLineup
    team: Team
    entries: list[LineupEntryDetail]
    result: ValidationResult


def _latest_lineup(
    db: Session, slot_id: uuid.UUID, team_id: uuid.UUID
) -> TieLineup | None:
    """The team's current (non-superseded) lineup in a slot, if any."""
    statement = (
        select(TieLineup)
        .where(
            TieLineup.round_slot_id == slot_id,
            TieLineup.team_id == team_id,
            TieLineup.status != LineupStatus.SUPERSEDED,
        )
        .order_by(col(TieLineup.version).desc())
    )
    return db.exec(statement).first()


def _effective_teams(db: Session, slot: RoundSlot) -> list[Team]:
    """The teams a slot admits: its allowlist, or every team in the tournament
    when the slot admits all."""
    assert slot.id is not None
    admitted = list_admitted_teams(db, slot.id)
    if admitted:
        return admitted
    statement = (
        select(Team)
        .where(Team.tournament_id == slot.tournament_id)
        .order_by(col(Team.name))
    )
    return list(db.exec(statement).all())


def _entries(db: Session, lineup: TieLineup) -> list[LineupEntry]:
    assert lineup.id is not None
    rows = db.exec(
        select(LineupEntry).where(LineupEntry.tie_lineup_id == lineup.id)
    ).all()
    return sorted(rows, key=lambda entry: (_EVENT_ORDER[entry.event], entry.position))


def _recheck(db: Session, team: Team, entries: list[LineupEntry]) -> ValidationResult:
    """Run the rules engine over a stored lineup's entries."""
    lineup = Lineup(
        entries=[
            Entry(
                event=entry.event,
                position=entry.position,
                player_id=entry.player_id,
                partner_id=entry.partner_id,
            )
            for entry in entries
        ]
    )
    return check_team_lineup(db, team, lineup)


def slot_submissions(db: Session, slot: RoundSlot) -> list[TeamSubmission]:
    """Each admitted team with its latest submission, outstanding if none."""
    assert slot.id is not None
    submissions: list[TeamSubmission] = []
    for team in _effective_teams(db, slot):
        assert team.id is not None
        submissions.append(
            TeamSubmission(team=team, lineup=_latest_lineup(db, slot.id, team.id))
        )
    return submissions


def tournament_slots(db: Session, tournament_id: uuid.UUID) -> list[RoundSlot]:
    """Every slot in a tournament, earliest opened first. Validates the id."""
    get_tournament(db, tournament_id)
    statement = (
        select(RoundSlot)
        .where(RoundSlot.tournament_id == tournament_id)
        .order_by(col(RoundSlot.opens_at))
    )
    return list(db.exec(statement).all())


def get_lineup(db: Session, lineup_id: uuid.UUID) -> TieLineup:
    """One tie lineup, or raise LineupNotFoundError."""
    lineup = db.get(TieLineup, lineup_id)
    if lineup is None:
        raise LineupNotFoundError
    return lineup


def lineup_detail(db: Session, lineup_id: uuid.UUID) -> LineupDetail:
    """A lineup in full: its entries with players, and a fresh check result."""
    lineup = get_lineup(db, lineup_id)
    team = db.get(Team, lineup.team_id)
    assert team is not None
    entries = _entries(db, lineup)
    details = [
        LineupEntryDetail(
            event=entry.event,
            position=entry.position,
            player=_player(db, entry.player_id),
            partner=_player(db, entry.partner_id) if entry.partner_id else None,
        )
        for entry in entries
    ]
    return LineupDetail(
        lineup=lineup, team=team, entries=details, result=_recheck(db, team, entries)
    )


def _player(db: Session, player_id: uuid.UUID) -> Player:
    player = db.get(Player, player_id)
    assert player is not None
    return player


def approve_lineup(db: Session, lineup_id: uuid.UUID) -> TieLineup:
    """Approve a lineup for copying into Tournament Software."""
    return _set_status(db, lineup_id, LineupStatus.APPROVED)


def flag_lineup(db: Session, lineup_id: uuid.UUID) -> TieLineup:
    """Flag a lineup for the Referee to resolve."""
    return _set_status(db, lineup_id, LineupStatus.FLAGGED)


def _set_status(db: Session, lineup_id: uuid.UUID, status: LineupStatus) -> TieLineup:
    lineup = get_lineup(db, lineup_id)
    if lineup.status is LineupStatus.SUPERSEDED:
        raise LineupActionError("A superseded lineup cannot be reviewed.")
    lineup.status = status
    db.add(lineup)
    db.commit()
    db.refresh(lineup)
    return lineup


def mark_copied(db: Session, lineup_id: uuid.UUID) -> TieLineup:
    """Record that an approved lineup was copied into Tournament Software."""
    lineup = get_lineup(db, lineup_id)
    if lineup.status is not LineupStatus.APPROVED:
        raise LineupActionError("Only an approved lineup can be marked copied.")
    lineup.copied_at = datetime.now(UTC)
    db.add(lineup)
    db.commit()
    db.refresh(lineup)
    return lineup


def finalize_closed_slot(db: Session, slot: RoundSlot) -> None:
    """Re-check each team's latest lineup and record the result.

    An official's approval stands; every other latest lineup is re-checked and
    recorded as submitted or flagged.
    """
    assert slot.id is not None
    for team in _effective_teams(db, slot):
        assert team.id is not None
        lineup = _latest_lineup(db, slot.id, team.id)
        if lineup is None or lineup.status is LineupStatus.APPROVED:
            continue
        result = _recheck(db, team, _entries(db, lineup))
        lineup.status = LineupStatus.SUBMITTED if result.ok else LineupStatus.FLAGGED
        db.add(lineup)
    db.commit()
