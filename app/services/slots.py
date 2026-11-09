import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models import RoundSlot, SlotTeam, Team
from app.models.enums import RoundSlotStatus


class RoundSlotNotFoundError(Exception):
    """Raised when no round slot exists for the given id."""


class RoundSlotWindowError(Exception):
    """Raised when a slot's cut-off would not fall after it opens."""


class RoundSlotTeamError(Exception):
    """Raised when an admitted team does not belong to the slot's tournament."""


def _ensure_window(opens_at: datetime, closes_at: datetime | None) -> None:
    if closes_at is not None and closes_at <= opens_at:
        raise RoundSlotWindowError("A slot's cut-off must fall after it opens.")


def _replace_admitted_teams(
    db: Session, slot: RoundSlot, team_ids: list[uuid.UUID]
) -> None:
    """Make the slot's allowlist exactly ``team_ids`` (deduped, order kept).

    An empty list clears the allowlist, which admits every team in the
    tournament. Does not commit, so it composes into one transaction.
    """
    assert slot.id is not None  # persisted by the caller before admitting teams
    unique_ids = list(dict.fromkeys(team_ids))
    for team_id in unique_ids:
        team = db.get(Team, team_id)
        if team is None or team.tournament_id != slot.tournament_id:
            raise RoundSlotTeamError(
                "Every admitted team must belong to the slot's tournament."
            )
    existing = db.exec(select(SlotTeam).where(SlotTeam.round_slot_id == slot.id)).all()
    for row in existing:
        db.delete(row)
    for team_id in unique_ids:
        db.add(SlotTeam(round_slot_id=slot.id, team_id=team_id))


def open_slot(
    db: Session,
    *,
    tournament_id: uuid.UUID,
    opens_at: datetime | None = None,
    closes_at: datetime | None = None,
    team_ids: list[uuid.UUID] | None = None,
) -> RoundSlot:
    """Open a round slot so its tournament's teams can submit lineups.

    Opens now unless a time is given; an optional cut-off can be set here or
    added later by extending the slot. Passing ``team_ids`` admits only those
    teams; omitting it admits every team in the tournament.
    """
    opened_at = opens_at or datetime.now(UTC)
    _ensure_window(opened_at, closes_at)
    slot = RoundSlot(
        tournament_id=tournament_id,
        status=RoundSlotStatus.OPEN,
        opens_at=opened_at,
        closes_at=closes_at,
    )
    db.add(slot)
    if team_ids is not None:
        db.flush()  # assign slot.id before admitting teams
        _replace_admitted_teams(db, slot, team_ids)
    db.commit()
    db.refresh(slot)
    return slot


def list_slots(db: Session, tournament_id: uuid.UUID) -> list[RoundSlot]:
    """Every round slot for a tournament, earliest opened first."""
    statement = (
        select(RoundSlot)
        .where(RoundSlot.tournament_id == tournament_id)
        .order_by(col(RoundSlot.opens_at))
    )
    return list(db.exec(statement).all())


def get_slot(db: Session, slot_id: uuid.UUID) -> RoundSlot:
    """One round slot, or raise RoundSlotNotFoundError."""
    slot = db.get(RoundSlot, slot_id)
    if slot is None:
        raise RoundSlotNotFoundError
    return slot


def list_admitted_teams(db: Session, slot_id: uuid.UUID) -> list[Team]:
    """The teams a slot admits, by name. Empty means it admits all of them."""
    get_slot(db, slot_id)
    statement = (
        select(Team)
        .join(SlotTeam, onclause=col(SlotTeam.team_id) == col(Team.id))
        .where(SlotTeam.round_slot_id == slot_id)
        .order_by(col(Team.name))
    )
    return list(db.exec(statement).all())


def update_slot(
    db: Session,
    slot_id: uuid.UUID,
    *,
    status: RoundSlotStatus | None = None,
    closes_at: datetime | None = None,
    team_ids: list[uuid.UUID] | None = None,
) -> RoundSlot:
    """Close, reopen, extend, or re-admit teams for a slot.

    Setting ``status`` opens or closes it; ``closes_at`` moves the cut-off;
    ``team_ids`` replaces the allowlist (an empty list admits all teams). Any
    combination can be given, so a late Tie can be reopened for specific teams
    in one step. Applied in a single transaction.
    """
    slot = get_slot(db, slot_id)
    if closes_at is not None:
        _ensure_window(slot.opens_at, closes_at)
        slot.closes_at = closes_at
    if status is not None:
        slot.status = status
    if team_ids is not None:
        _replace_admitted_teams(db, slot, team_ids)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


def team_is_admitted(db: Session, slot_id: uuid.UUID, team_id: uuid.UUID) -> bool:
    """Whether a team may submit to a slot. A slot with no admitted-team rows
    admits every team; otherwise only the teams on its allowlist."""
    rows = db.exec(select(SlotTeam).where(SlotTeam.round_slot_id == slot_id)).all()
    if not rows:
        return True
    return any(row.team_id == team_id for row in rows)
