import uuid
from dataclasses import dataclass

from sqlmodel import Session, col, select

from app.models import (
    LineupEntry,
    LineupStatus,
    ListEntry,
    ListStatus,
    Player,
    RankedTeamList,
    RoundSlotStatus,
    Team,
    TieLineup,
)
from app.models.enums import Event
from app.rules import ApprovedList, Entry, Lineup, TieFormat, check_lineup
from app.rules.results import ValidationResult
from app.services.slots import RoundSlotNotFoundError, get_slot, team_is_admitted
from app.services.tournaments import get_tournament, tie_format_of

_SINGLES = {Event.MENS_SINGLES, Event.WOMENS_SINGLES}


class NoApprovedListError(Exception):
    """Raised when a team has no approved Ranked Team List to check against."""


class SlotClosedError(Exception):
    """Raised when a lineup is submitted into a slot that is not open."""


class TeamNotAdmittedError(Exception):
    """Raised when a team is not admitted to the slot it submits into."""


class LineupShapeError(Exception):
    """Raised when an entry has the wrong shape for its event (pairing)."""


@dataclass(frozen=True)
class ApprovedUnit:
    """One approved (event, position) slot with its player details resolved."""

    event: Event
    position: int
    player: Player
    partner: Player | None


def _current_approved_list(db: Session, team_id: uuid.UUID) -> RankedTeamList:
    """The team's latest approved list, or raise NoApprovedListError."""
    statement = (
        select(RankedTeamList)
        .where(
            RankedTeamList.team_id == team_id,
            RankedTeamList.approval_status == ListStatus.APPROVED,
        )
        .order_by(col(RankedTeamList.version).desc())
    )
    ranked_list = db.exec(statement).first()
    if ranked_list is None:
        raise NoApprovedListError
    return ranked_list


def _list_entries(db: Session, ranked_list_id: uuid.UUID) -> list[ListEntry]:
    statement = (
        select(ListEntry)
        .where(ListEntry.ranked_team_list_id == ranked_list_id)
        .order_by(col(ListEntry.event), col(ListEntry.position))
    )
    return list(db.exec(statement).all())


def approved_list_input(db: Session, team_id: uuid.UUID) -> ApprovedList:
    """The team's current Approved Team List as the engine's reference input."""
    ranked_list = _current_approved_list(db, team_id)
    assert ranked_list.id is not None
    return ApprovedList(
        entries=[
            Entry(
                event=entry.event,
                position=entry.position,
                player_id=entry.player_id,
                partner_id=entry.partner_id,
            )
            for entry in _list_entries(db, ranked_list.id)
        ]
    )


def list_approved_units(db: Session, team_id: uuid.UUID) -> list[ApprovedUnit]:
    """The team's approved units with player details, for building a lineup."""
    ranked_list = _current_approved_list(db, team_id)
    assert ranked_list.id is not None
    units: list[ApprovedUnit] = []
    for entry in _list_entries(db, ranked_list.id):
        player = db.get(Player, entry.player_id)
        assert player is not None
        partner = db.get(Player, entry.partner_id) if entry.partner_id else None
        units.append(
            ApprovedUnit(
                event=entry.event,
                position=entry.position,
                player=player,
                partner=partner,
            )
        )
    return units


def tie_format_for_team(db: Session, team: Team) -> TieFormat:
    """The tie format of the team's tournament."""
    return tie_format_of(get_tournament(db, team.tournament_id))


def check_team_lineup(db: Session, team: Team, lineup: Lineup) -> ValidationResult:
    """Check a proposed lineup against the team's Approved Team List and tie
    format. A pure read: it saves nothing."""
    assert team.id is not None
    approved = approved_list_input(db, team.id)
    tie_format = tie_format_for_team(db, team)
    return check_lineup(lineup, approved, tie_format)


def _enforce_shape(lineup: Lineup) -> None:
    """Each doubles/mixed entry needs a pair; each singles entry needs none."""
    for entry in lineup.entries:
        needs_partner = entry.event not in _SINGLES
        if needs_partner and entry.partner_id is None:
            raise LineupShapeError(f"{entry.event.value} needs a pair.")
        if not needs_partner and entry.partner_id is not None:
            raise LineupShapeError(
                f"{entry.event.value} is a singles match and takes one player."
            )


def submit_lineup(
    db: Session, team: Team, round_slot_id: uuid.UUID, lineup: Lineup
) -> tuple[TieLineup, ValidationResult]:
    """Record a team's lineup submission into an open slot.

    Each submission is a new immutable version that supersedes the team's
    previous one in that slot. The lineup is recorded whatever the check says:
    a passing lineup is ``submitted``, a blocking one is ``flagged`` for the
    official to review. Rejects a closed slot, a team not admitted, a lineup of
    the wrong shape, or a team with no approved list.
    """
    assert team.id is not None
    slot = get_slot(db, round_slot_id)
    if slot.tournament_id != team.tournament_id:
        raise RoundSlotNotFoundError  # not this team's slot to see
    if slot.status is not RoundSlotStatus.OPEN:
        raise SlotClosedError
    if not team_is_admitted(db, round_slot_id, team.id):
        raise TeamNotAdmittedError
    _enforce_shape(lineup)

    result = check_team_lineup(db, team, lineup)
    status = LineupStatus.SUBMITTED if result.ok else LineupStatus.FLAGGED

    existing = db.exec(
        select(TieLineup).where(
            TieLineup.round_slot_id == round_slot_id,
            TieLineup.team_id == team.id,
        )
    ).all()
    next_version = max((row.version for row in existing), default=0) + 1
    for row in existing:
        if row.status is not LineupStatus.SUPERSEDED:
            row.status = LineupStatus.SUPERSEDED
            db.add(row)

    submission = TieLineup(
        round_slot_id=round_slot_id,
        team_id=team.id,
        version=next_version,
        status=status,
    )
    db.add(submission)
    db.flush()
    assert submission.id is not None
    for entry in lineup.entries:
        db.add(
            LineupEntry(
                tie_lineup_id=submission.id,
                event=entry.event,
                position=entry.position,
                player_id=entry.player_id,
                partner_id=entry.partner_id,
            )
        )
    db.commit()
    db.refresh(submission)
    return submission, result
