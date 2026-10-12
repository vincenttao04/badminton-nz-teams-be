import uuid

from sqlalchemy import CheckConstraint, Column, Index, text
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
    """One grant: a user may act in one role, over one scope.
    The authorisation backbone.
    """

    __table_args__ = (
        CheckConstraint(
            """
            CASE role
                WHEN 'coach' THEN
                    team_id IS NOT NULL
                    AND association_id IS NULL
                    AND tournament_id IS NULL
                WHEN 'team_manager' THEN
                    team_id IS NOT NULL
                    AND association_id IS NULL
                    AND tournament_id IS NULL
                WHEN 'association' THEN
                    association_id IS NOT NULL
                    AND team_id IS NULL
                    AND tournament_id IS NULL
                WHEN 'referee' THEN
                    tournament_id IS NOT NULL
                    AND team_id IS NULL
                    AND association_id IS NULL
                WHEN 'technical_official' THEN
                    team_id IS NULL
                    AND association_id IS NULL
                    AND tournament_id IS NULL
                WHEN 'system_administrator' THEN
                    team_id IS NULL
                    AND association_id IS NULL
                    AND tournament_id IS NULL
                ELSE FALSE
            END
            """,
            name="role_scope_matches_role",
        ),
        Index(
            "uq_one_coach_manager_per_team",
            "team_id",
            "role",
            unique=True,
            postgresql_where=text("role IN ('coach', 'team_manager')"),
        ),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", index=True)
    role: Role = Field(sa_column=Column(enum_column(Role), nullable=False, index=True))
    team_id: uuid.UUID | None = Field(default=None, foreign_key="team.id", index=True)
    association_id: uuid.UUID | None = Field(
        default=None, foreign_key="association.id", index=True
    )
    tournament_id: uuid.UUID | None = Field(
        default=None, foreign_key="tournament.id", index=True
    )

    user: User = Relationship(back_populates="role_assignments")
