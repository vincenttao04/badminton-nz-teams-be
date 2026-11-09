import uuid
from dataclasses import dataclass

from sqlmodel import Session, col, select

from app.models import ListEntry, ListStatus, Player, RankedTeamList, Team
from app.models.enums import Event
from app.rules import ApprovedList, Entry, Lineup, TieFormat, check_lineup
from app.rules.results import ValidationResult
from app.services.tournaments import get_tournament, tie_format_of


class NoApprovedListError(Exception):
    """Raised when a team has no approved Ranked Team List to check against."""


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
