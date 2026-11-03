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


def test_entry_players_singles() -> None:
    pid = uuid.uuid4()
    entry = Entry(event=Event.MENS_SINGLES, position=1, player_id=pid)
    assert entry.players() == frozenset({pid})


def test_entry_players_pair_is_order_insensitive() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    entry = Entry(event=Event.MENS_DOUBLES, position=1, player_id=a, partner_id=b)
    assert entry.players() == frozenset({a, b})
