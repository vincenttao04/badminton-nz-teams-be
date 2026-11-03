from app.models.enums import Event
from app.rules.results import Finding, Location, Severity, ValidationResult


def _block_finding() -> Finding:
    return Finding(
        severity=Severity.BLOCK,
        location=Location(event=Event.MENS_SINGLES, position=2),
        rule="Relative order within an Event must be preserved",
        message="Position 2 is above position 1 on the Approved Team List",
        how_to_fix="Swap positions 1 and 2",
    )


def test_empty_result_is_ok() -> None:
    result = ValidationResult.from_findings([])
    assert result.ok is True
    assert result.findings == []


def test_a_block_finding_makes_it_not_ok() -> None:
    result = ValidationResult.from_findings([_block_finding()])
    assert result.ok is False


def test_only_flag_findings_stay_ok() -> None:
    flag = _block_finding().model_copy(update={"severity": Severity.FLAG})
    result = ValidationResult.from_findings([flag])
    assert result.ok is True


def test_serialises_to_the_documented_shape() -> None:
    result = ValidationResult.from_findings([_block_finding()])
    dumped = result.model_dump(mode="json")
    assert dumped["ok"] is False
    assert dumped["findings"][0]["severity"] == "block"
    assert dumped["findings"][0]["location"] == {
        "event": "mens_singles",
        "position": 2,
        "player_id": None,
    }
