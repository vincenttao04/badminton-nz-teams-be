import uuid
from dataclasses import dataclass

from sqlmodel import Session, col, select

from app.models import LineupStatus, RoundSlot, Team, TieLineup
from app.services.slots import list_admitted_teams
from app.services.tournaments import get_tournament


@dataclass(frozen=True)
class TeamSubmission:
    """An admitted team and its latest submission, or none if outstanding."""

    team: Team
    lineup: TieLineup | None


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
