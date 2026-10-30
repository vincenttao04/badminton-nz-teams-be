import uuid

from app.models.enums import Event
from app.rules.inputs import ApprovedList, Entry, Lineup, TieFormat


def test_tie_format_counts_a_set_event() -> None:
    fmt = TieFormat(matches_per_event={Event.MENS_SINGLES: 2})
    assert fmt.count_for(Event.MENS_SINGLES) == 2


def test_tie_format_defaults_a_missing_event_to_zero() -> None:
    fmt = TieFormat(matches_per_event={Event.MENS_SINGLES: 2})
    assert fmt.count_for(Event.MIXED_DOUBLES) == 0


def test_lineup_and_list_hold_entries() -> None:
    entry = Entry(event=Event.MENS_SINGLES, position=1, player_id=uuid.uuid4())
    assert Lineup(entries=[entry]).entries == [entry]
    assert ApprovedList(entries=[entry]).entries == [entry]
