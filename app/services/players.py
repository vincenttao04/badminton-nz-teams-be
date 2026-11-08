from sqlmodel import Session, select

from app.models import Player


def get_or_create_player(db: Session, member_id: str, full_name: str) -> Player:
    """Find a player by Member ID, or create one."""
    existing = db.exec(
        select(Player).where(Player.member_id == member_id)
    ).one_or_none()
    if existing is not None:
        return existing
    player = Player(member_id=member_id, full_name=full_name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return player
