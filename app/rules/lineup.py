from collections import Counter

from app.models.enums import Event
from app.rules.inputs import Lineup, TieFormat
from app.rules.results import Finding, Location, Severity

RULE_MATCH_COUNTS = "The number of matches in each event must match the tie format"


def check_match_counts(lineup: Lineup, tie_format: TieFormat) -> list[Finding]:
    """Each event has exactly the number of matches the tie format sets."""
    counts = Counter(entry.event for entry in lineup.entries)
    findings: list[Finding] = []
    for event in Event:
        expected = tie_format.count_for(event)
        actual = counts[event]
        if actual != expected:
            findings.append(
                Finding(
                    severity=Severity.BLOCK,
                    location=Location(event=event),
                    rule=RULE_MATCH_COUNTS,
                    message=(
                        f"{event.value} has {actual} matches "
                        f"but the tie format requires {expected}"
                    ),
                    how_to_fix=f"Add/remove {event.value} matches to reach {expected}",
                )
            )
    return findings
