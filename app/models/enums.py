from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class Event(StrEnum):
    """A badminton discipline contested within a tie."""

    SINGLES = "singles"
    DOUBLES = "doubles"
    MIXED = "mixed"


class Role(StrEnum):
    """A role a user can hold, always scoped by a RoleAssignment."""

    COACH = "coach"
    TEAM_MANAGER = "team_manager"
    TECHNICAL_OFFICIAL = "technical_official"
    REFEREE = "referee"
    ASSOCIATION = "association"
    SYSTEM_ADMINISTRATOR = "system_administrator"


def enum_column(enum_type: type[StrEnum]) -> SAEnum:
    """Store a Python StrEnum as a plain VARCHAR: no native DB enum, no value CHECK.

    Keeps roles and statuses flexible: adding, removing or merging a value stays a
    code and data change, with no migration to a database enum type or constraint.
    """
    return SAEnum(
        enum_type,
        native_enum=False,
        create_constraint=False,
        values_callable=lambda enum: [member.value for member in enum],
    )
