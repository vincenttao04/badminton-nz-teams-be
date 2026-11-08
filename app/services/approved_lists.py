import uuid
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import Event, ListEntry, ListStatus, RankedTeamList
from app.services.players import get_or_create_player
from app.services.teams import get_team


@dataclass(frozen=True)
class PlayerInput:
    member_id: str
    full_name: str


@dataclass(frozen=True)
class ApprovedListEntryInput:
    event: Event
    position: int
    player: PlayerInput
    partner: PlayerInput | None


def team_has_approved_list(db: Session, team_id: uuid.UUID) -> bool:
    """Whether the team already has at least one ranked list."""
    statement = select(RankedTeamList).where(RankedTeamList.team_id == team_id)
    return db.exec(statement).first() is not None


def create_approved_list(
    db: Session, team_id: uuid.UUID, entries: list[ApprovedListEntryInput]
) -> RankedTeamList:
    """Record a new, approved version of a team's ranked list."""
    get_team(db, team_id)  # raises TeamNotFoundError if the team is missing

    resolved: list[tuple[uuid.UUID, uuid.UUID | None]] = []
    for entry in entries:
        player = get_or_create_player(
            db, entry.player.member_id, entry.player.full_name
        )
        assert player.id is not None
        partner_id: uuid.UUID | None = None
        if entry.partner is not None:
            partner = get_or_create_player(
                db, entry.partner.member_id, entry.partner.full_name
            )
            assert partner.id is not None
            partner_id = partner.id
        resolved.append((player.id, partner_id))

    existing = db.exec(
        select(RankedTeamList).where(RankedTeamList.team_id == team_id)
    ).all()
    ranked_list = RankedTeamList(
        team_id=team_id,
        version=len(existing) + 1,
        approval_status=ListStatus.APPROVED,
    )
    db.add(ranked_list)
    db.flush()
    assert ranked_list.id is not None

    for entry, (player_id, partner_id) in zip(entries, resolved, strict=True):
        db.add(
            ListEntry(
                ranked_team_list_id=ranked_list.id,
                event=entry.event,
                position=entry.position,
                player_id=player_id,
                partner_id=partner_id,
            )
        )
    db.commit()
    db.refresh(ranked_list)
    return ranked_list
