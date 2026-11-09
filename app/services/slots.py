import uuid
from datetime import UTC, datetime

from sqlmodel import Session, col, select

from app.models import RoundSlot
from app.models.enums import RoundSlotStatus


class RoundSlotNotFoundError(Exception):
    """Raised when no round slot exists for the given id."""


class RoundSlotWindowError(Exception):
    """Raised when a slot's cut-off would not fall after it opens."""


def _ensure_window(opens_at: datetime, closes_at: datetime | None) -> None:
    if closes_at is not None and closes_at <= opens_at:
        raise RoundSlotWindowError("A slot's cut-off must fall after it opens.")


def open_slot(
    db: Session,
    *,
    tournament_id: uuid.UUID,
    opens_at: datetime | None = None,
    closes_at: datetime | None = None,
) -> RoundSlot:
    """Open a round slot so its tournament's teams can submit lineups.

    Opens now unless a time is given; an optional cut-off can be set here or
    added later by extending the slot.
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


def update_slot(
    db: Session,
    slot_id: uuid.UUID,
    *,
    status: RoundSlotStatus | None = None,
    closes_at: datetime | None = None,
) -> RoundSlot:
    """Close, reopen, or extend a slot.

    Setting ``status`` opens or closes it; setting ``closes_at`` moves the
    cut-off. Both can be given together, so a late Tie can be reopened and
    extended in one step. Applied in a single transaction.
    """
    slot = get_slot(db, slot_id)
    if closes_at is not None:
        _ensure_window(slot.opens_at, closes_at)
        slot.closes_at = closes_at
    if status is not None:
        slot.status = status
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot
