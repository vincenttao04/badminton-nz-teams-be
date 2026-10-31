import uuid

from app.models.enums import Event
from app.rules.inputs import ApprovedList, Entry, Lineup, TieFormat
from app.rules.lineup import (
    check_from_approved_list,
    check_match_counts,
    check_one_match_per_event,
)
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


def test_one_match_per_event_allows_a_player_across_events() -> None:
    pid = uuid.uuid4()
    lineup = Lineup(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=pid),
            Entry(
                event=Event.MENS_DOUBLES,
                position=1,
                player_id=pid,
                partner_id=uuid.uuid4(),
            ),
        ]
    )
    assert check_one_match_per_event(lineup) == []


def test_one_match_per_event_flags_a_repeat_within_an_event() -> None:
    pid = uuid.uuid4()
    lineup = Lineup(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=pid),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=pid),
        ]
    )
    findings = check_one_match_per_event(lineup)
    assert len(findings) == 1
    assert findings[0].location.event == Event.MENS_SINGLES
    assert findings[0].location.player_id == pid
    assert findings[0].severity == Severity.BLOCK


def test_one_match_per_event_flags_a_repeat_inside_a_pair() -> None:
    shared = uuid.uuid4()
    lineup = Lineup(
        entries=[
            Entry(
                event=Event.MENS_DOUBLES,
                position=1,
                player_id=shared,
                partner_id=uuid.uuid4(),
            ),
            Entry(
                event=Event.MENS_DOUBLES,
                position=2,
                player_id=shared,
                partner_id=uuid.uuid4(),
            ),
        ]
    )
    findings = check_one_match_per_event(lineup)
    assert any(f.location.player_id == shared for f in findings)


def test_one_match_per_event_passes_distinct_players() -> None:
    lineup = Lineup(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=uuid.uuid4()),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=uuid.uuid4()),
        ]
    )
    assert check_one_match_per_event(lineup) == []


def test_from_approved_list_passes_a_listed_singles_player() -> None:
    pid = uuid.uuid4()
    approved = ApprovedList(
        entries=[Entry(event=Event.MENS_SINGLES, position=1, player_id=pid)]
    )
    lineup = Lineup(
        entries=[Entry(event=Event.MENS_SINGLES, position=1, player_id=pid)]
    )
    assert check_from_approved_list(lineup, approved) == []


def test_from_approved_list_flags_an_unlisted_player() -> None:
    approved = ApprovedList(
        entries=[Entry(event=Event.MENS_SINGLES, position=1, player_id=uuid.uuid4())]
    )
    lineup = Lineup(
        entries=[Entry(event=Event.MENS_SINGLES, position=1, player_id=uuid.uuid4())]
    )
    findings = check_from_approved_list(lineup, approved)
    assert len(findings) == 1
    assert findings[0].severity == Severity.BLOCK
    assert findings[0].location.event == Event.MENS_SINGLES
    assert findings[0].location.position == 1


def test_from_approved_list_matches_a_pair_regardless_of_order() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    approved = ApprovedList(
        entries=[Entry(event=Event.MENS_DOUBLES, position=1, player_id=a, partner_id=b)]
    )
    lineup = Lineup(
        entries=[Entry(event=Event.MENS_DOUBLES, position=1, player_id=b, partner_id=a)]
    )
    assert check_from_approved_list(lineup, approved) == []


def test_from_approved_list_flags_a_repaired_pair() -> None:
    a, b, c, d = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    approved = ApprovedList(
        entries=[
            Entry(event=Event.MENS_DOUBLES, position=1, player_id=a, partner_id=b),
            Entry(event=Event.MENS_DOUBLES, position=2, player_id=c, partner_id=d),
        ]
    )
    lineup = Lineup(
        entries=[Entry(event=Event.MENS_DOUBLES, position=1, player_id=a, partner_id=c)]
    )
    assert len(check_from_approved_list(lineup, approved)) == 1


def test_from_approved_list_is_event_specific() -> None:
    pid = uuid.uuid4()
    approved = ApprovedList(
        entries=[
            Entry(
                event=Event.MENS_DOUBLES,
                position=1,
                player_id=pid,
                partner_id=uuid.uuid4(),
            )
        ]
    )
    lineup = Lineup(
        entries=[Entry(event=Event.MENS_SINGLES, position=1, player_id=pid)]
    )
    assert len(check_from_approved_list(lineup, approved)) == 1
