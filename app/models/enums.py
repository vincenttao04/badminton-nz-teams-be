from enum import StrEnum


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
