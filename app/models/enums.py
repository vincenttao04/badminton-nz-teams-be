from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class Event(StrEnum):
    """A badminton discipline contested within a tie."""

    MENS_SINGLES = "mens_singles"
    WOMENS_SINGLES = "womens_singles"
    MENS_DOUBLES = "mens_doubles"
    WOMENS_DOUBLES = "womens_doubles"
    MIXED_DOUBLES = "mixed_doubles"


class Role(StrEnum):
    """A role a user account can hold, scoped by a RoleAssignment."""

    TECHNICAL_OFFICIAL = "technical_official"
    REFEREE = "referee"
    SYSTEM_ADMINISTRATOR = "system_administrator"


class ListStatus(StrEnum):
    """Lifecycle of a Ranked Team List."""

    ## In the first release a seeded list is entered as a draft and marked approved.
    ## Phase A adds the submission and protest states.

    DRAFT = "draft"
    APPROVED = "approved"


class RoundSlotStatus(StrEnum):
    """Whether a round slot is accepting submissions."""

    OPEN = "open"
    CLOSED = "closed"


class LineupStatus(StrEnum):
    """Lifecycle of a Tie Lineup submission."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    SUPERSEDED = "superseded"
    FLAGGED = "flagged"
    APPROVED = "approved"


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
