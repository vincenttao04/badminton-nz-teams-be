import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime
from sqlmodel import Field, Relationship

from app.models.base import Base
from app.models.enums import Role, enum_column


class User(Base, table=True):
    """A person who signs in and acts in the system.
    Permissions come from RoleAssignment."""

    __tablename__ = "app_user"  # pyright: ignore[reportAssignmentType]

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

    user_id: uuid.UUID = Field(foreign_key="app_user.id", index=True)
    role: Role = Field(sa_column=Column(enum_column(Role), nullable=False, index=True))
    tournament_id: uuid.UUID | None = Field(
        default=None, foreign_key="tournament.id", index=True
    )

    user: User = Relationship(back_populates="role_assignments")


class AuthSession(Base, table=True):
    """A signed-in session for a user account or a team (via access details).
    The cookie carries a random token; only its hash is stored here."""

    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(user_id, team_id) = 1",
            name="session_belongs_to_user_xor_team",
        ),
    )

    token_hash: str = Field(unique=True, index=True)
    user_id: uuid.UUID | None = Field(
        default=None, foreign_key="app_user.id", index=True
    )
    team_id: uuid.UUID | None = Field(default=None, foreign_key="team.id", index=True)
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
