import uuid

from app.models.enums import Event
from app.rules import ApprovedList, Entry, Lineup, TieFormat, check_lineup
from app.rules.lineup import RULE_FROM_APPROVED_LIST


def test_check_lineup_passes_a_valid_lineup() -> None:
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    d, e = uuid.uuid4(), uuid.uuid4()
    tie_format = TieFormat(
        matches_per_event={Event.MENS_SINGLES: 2, Event.MENS_DOUBLES: 1}
    )
    approved = ApprovedList(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=a),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=b),
            Entry(event=Event.MENS_SINGLES, position=3, player_id=c),
            Entry(event=Event.MENS_DOUBLES, position=1, player_id=d, partner_id=e),
        ]
    )
    lineup = Lineup(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=a),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=b),
            Entry(event=Event.MENS_DOUBLES, position=1, player_id=d, partner_id=e),
        ]
    )
    result = check_lineup(lineup, approved, tie_format)
    assert result.ok is True
    assert result.findings == []


def test_check_lineup_flags_an_off_list_player() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    tie_format = TieFormat(matches_per_event={Event.MENS_SINGLES: 2})
    approved = ApprovedList(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=a),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=b),
        ]
    )
    lineup = Lineup(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=a),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=uuid.uuid4()),
        ]
    )
    result = check_lineup(lineup, approved, tie_format)
    assert result.ok is False
    assert any(f.rule == RULE_FROM_APPROVED_LIST for f in result.findings)


def test_check_lineup_aggregates_findings_from_several_rules() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    tie_format = TieFormat(
        matches_per_event={Event.MENS_SINGLES: 2, Event.MENS_DOUBLES: 1}
    )
    approved = ApprovedList(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=a),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=b),
        ]
    )
    # singles inverted (b above a); no doubles entry (count short)
    lineup = Lineup(
        entries=[
            Entry(event=Event.MENS_SINGLES, position=1, player_id=b),
            Entry(event=Event.MENS_SINGLES, position=2, player_id=a),
        ]
    )
    result = check_lineup(lineup, approved, tie_format)
    assert result.ok is False
    assert len({f.rule for f in result.findings}) >= 2
