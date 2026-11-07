from app.models.enums import Event
from app.rules.inputs import TieFormat
from app.rules.tournament import required_players_by_sex, validate_tournament_config


def _tie_format(
    mens_singles: int = 1,
    womens_singles: int = 1,
    mens_doubles: int = 1,
    womens_doubles: int = 1,
    mixed_doubles: int = 1,
) -> TieFormat:
    return TieFormat(
        matches_per_event={
            Event.MENS_SINGLES: mens_singles,
            Event.WOMENS_SINGLES: womens_singles,
            Event.MENS_DOUBLES: mens_doubles,
            Event.WOMENS_DOUBLES: womens_doubles,
            Event.MIXED_DOUBLES: mixed_doubles,
        }
    )


def _limits(**overrides: int | None) -> dict[str, int | None]:
    limits: dict[str, int | None] = {
        "min_male": None,
        "max_male": None,
        "min_female": None,
        "max_female": None,
    }
    limits.update(overrides)
    return limits


def test_required_players_takes_the_largest_single_event_demand() -> None:
    # Doubles needs two per match; a player may be reused across events (R-12).
    tie_format = _tie_format(
        mens_singles=1,
        mens_doubles=2,
        mixed_doubles=1,
        womens_singles=3,
        womens_doubles=1,
    )
    # male: max(1, 2 * 2, 1) = 4; female: max(3, 2 * 1, 1) = 3
    assert required_players_by_sex(tie_format) == (4, 3)


def test_config_without_limits_passes() -> None:
    result = validate_tournament_config(_tie_format(), **_limits())
    assert result.ok
    assert result.findings == []


def test_maximum_below_required_is_blocked() -> None:
    # A 1/1/1/1/1 tie needs two males (two for doubles); a max of one cannot field it.
    result = validate_tournament_config(_tie_format(), **_limits(max_male=1))
    assert not result.ok
    assert any("male" in finding.message for finding in result.findings)


def test_maximum_equal_to_required_passes() -> None:
    result = validate_tournament_config(
        _tie_format(), **_limits(max_male=2, max_female=2)
    )
    assert result.ok


def test_minimum_above_maximum_is_blocked() -> None:
    result = validate_tournament_config(
        _tie_format(), **_limits(min_female=5, max_female=4)
    )
    assert not result.ok


def test_empty_tie_format_is_blocked() -> None:
    result = validate_tournament_config(_tie_format(0, 0, 0, 0, 0), **_limits())
    assert not result.ok