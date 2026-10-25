from sqlmodel import Field

from app.models.base import Base


class Player(Base, table=True):
    """A badminton player, identified by their Tournament Software Member ID."""

    member_id: str = Field(unique=True, index=True)
    full_name: str = Field(index=True)
