import uuid

from sqlalchemy import CheckConstraint, Column
from sqlmodel import Field, Relationship

from app.models.base import Base
from app.models.enums import Role, enum_column


class User(Base, table=True):
    """A person who signs in and acts in the system.
    Permissions come from RoleAssignment."""

    email: str = Field(unique=True, index=True)
    full_name: str
    hashed_password: str
    is_active: bool = Field(default=True)

    role_assignments: list["RoleAssignment"] = Relationship(back_populates="user")


class RoleAssignment(Base, table=True):
    """One grant: a user may act in one role, optionally scoped to a tournament.
    The authorisation backbone.
    """

    __table_args__ = (
        CheckConstraint(
            """
            CASE role
                WHEN 'referee' THEN tournament_id IS NOT NULL
                WHEN 'technical_official' THEN tournament_id IS NULL
                WHEN 'system_administrator' THEN tournament_id IS NULL
                ELSE FALSE
            END
            """,
            name="role_scope_matches_role",
        ),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    role: Role = Field(sa_column=Column(enum_column(Role), nullable=False, index=True))
    tournament_id: uuid.UUID | None = Field(
        default=None, foreign_key="tournament.id", index=True
    )

    user: User = Relationship(back_populates="role_assignments")
