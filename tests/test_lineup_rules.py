import uuid

from app.models.enums import Event
from app.rules.inputs import Entry, Lineup, TieFormat
from app.rules.lineup import check_match_counts
from app.rules.results import Severity


def _entry(event: Event, position: int) -> Entry:
    return Entry(event=event, position=position, player_id=uuid.uuid4())


def test_match_counts_pass_when_lineup_matches_format() -> None:
    fmt = TieFormat(matches_per_event={Event.MENS_SINGLES: 2, Event.MENS_DOUBLES: 1})
    lineup = Lineup(
        entries=[
            _entry(Event.MENS_SINGLES, 1),
            _entry(Event.MENS_SINGLES, 2),
            _entry(Event.MENS_DOUBLES, 1),
        ]
    )
    assert check_match_counts(lineup, fmt) == []


def test_match_counts_flag_too_few() -> None:
    fmt = TieFormat(matches_per_event={Event.MENS_SINGLES: 2})
    lineup = Lineup(entries=[_entry(Event.MENS_SINGLES, 1)])
    findings = check_match_counts(lineup, fmt)
    assert len(findings) == 1
    assert findings[0].location.event == Event.MENS_SINGLES
    assert findings[0].severity == Severity.BLOCK


def test_match_counts_flag_too_many() -> None:
    fmt = TieFormat(matches_per_event={Event.MENS_SINGLES: 1})
    lineup = Lineup(
        entries=[_entry(Event.MENS_SINGLES, 1), _entry(Event.MENS_SINGLES, 2)]
    )
    findings = check_match_counts(lineup, fmt)
    assert len(findings) == 1
    assert findings[0].location.event == Event.MENS_SINGLES


def test_match_counts_flag_an_event_not_in_the_format() -> None:
    fmt = TieFormat(matches_per_event={Event.MENS_SINGLES: 1})
    lineup = Lineup(
        entries=[_entry(Event.MENS_SINGLES, 1), _entry(Event.MIXED_DOUBLES, 1)]
    )
    findings = check_match_counts(lineup, fmt)
    assert len(findings) == 1
    assert findings[0].location.event == Event.MIXED_DOUBLES


def test_match_counts_report_only_the_wrong_events() -> None:
    fmt = TieFormat(matches_per_event={Event.MENS_SINGLES: 1, Event.WOMENS_SINGLES: 1})
    lineup = Lineup(entries=[_entry(Event.MENS_SINGLES, 1)])
    findings = check_match_counts(lineup, fmt)
    assert len(findings) == 1
    assert findings[0].location.event == Event.WOMENS_SINGLES
