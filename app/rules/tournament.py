from app.models.enums import Event
from app.rules.inputs import TieFormat
from app.rules.results import Finding, Location, Severity, ValidationResult

RULE_TIE_FORMAT_NON_EMPTY = "A tie format must have at least one match"
RULE_ROSTER_FITS_TIE_FORMAT = "Roster limits must be consistent with the tie format"


def required_players_by_sex(tie_format: TieFormat) -> tuple[int, int]:
    """The fewest distinct male and female players needed to field the tie format.

    A player plays at most one match within an event but may play across events
    (R-12), so one player can cover a slot in every event at once. The floor per
    sex is therefore the largest single-event demand, not the sum across events:
    doubles needs two players per match, mixed needs one of each sex per match.
    """
    required_male = max(
        tie_format.count_for(Event.MENS_SINGLES),
        2 * tie_format.count_for(Event.MENS_DOUBLES),
        tie_format.count_for(Event.MIXED_DOUBLES),
    )
    required_female = max(
        tie_format.count_for(Event.WOMENS_SINGLES),
        2 * tie_format.count_for(Event.WOMENS_DOUBLES),
        tie_format.count_for(Event.MIXED_DOUBLES),
    )
    return required_male, required_female


def validate_tournament_config(
    tie_format: TieFormat,
    *,
    min_male: int | None,
    max_male: int | None,
    min_female: int | None,
    max_female: int | None,
) -> ValidationResult:
    """Check a tournament's tie format and optional roster limits (R-31).

    Blocks an empty tie format, a roster maximum below the players the tie format
    needs, or a minimum above the maximum. A limit left unset is not checked.
    """
    required_male, required_female = required_players_by_sex(tie_format)
    findings: list[Finding] = []
    findings.extend(_check_non_empty(tie_format))
    findings.extend(_check_sex("male", required_male, min_male, max_male))
    findings.extend(_check_sex("female", required_female, min_female, max_female))
    return ValidationResult.from_findings(findings)


def _check_non_empty(tie_format: TieFormat) -> list[Finding]:
    if sum(tie_format.count_for(event) for event in Event) > 0:
        return []
    return [
        Finding(
            severity=Severity.BLOCK,
            location=Location(),
            rule=RULE_TIE_FORMAT_NON_EMPTY,
            message="The tie format has no matches in any event",
            how_to_fix="Set at least one event to one or more matches",
        )
    ]


def _check_sex(
    sex: str, required: int, minimum: int | None, maximum: int | None
) -> list[Finding]:
    findings: list[Finding] = []
    if maximum is not None and maximum < required:
        findings.append(
            Finding(
                severity=Severity.BLOCK,
                location=Location(),
                rule=RULE_ROSTER_FITS_TIE_FORMAT,
                message=(
                    f"The maximum of {maximum} {sex} players is below the "
                    f"{required} the tie format needs"
                ),
                how_to_fix=f"Raise the {sex} maximum to at least {required}",
            )
        )
    if minimum is not None and maximum is not None and minimum > maximum:
        findings.append(
            Finding(
                severity=Severity.BLOCK,
                location=Location(),
                rule=RULE_ROSTER_FITS_TIE_FORMAT,
                message=(
                    f"The minimum of {minimum} {sex} players is above the "
                    f"maximum of {maximum}"
                ),
                how_to_fix=f"Set the {sex} minimum to at most {maximum}",
            )
        )
    return findings
