import uuid
from collections import Counter

from app.models.enums import Event
from app.rules.inputs import ApprovedList, Lineup, TieFormat
from app.rules.results import Finding, Location, Severity, ValidationResult

RULE_MATCH_COUNTS = "The number of matches in each event must match the tie format"
RULE_ONE_MATCH_PER_EVENT = "A player may play at most one match within an event"
RULE_FROM_APPROVED_LIST = "Every player and pair must come from the Approved Team List"
RULE_RELATIVE_ORDER = "The Approved Team List order within each event must be preserved"


def check_lineup(
    lineup: Lineup, approved_list: ApprovedList, tie_format: TieFormat
) -> ValidationResult:
    """Run every Phase B lineup rule and combine the findings into one result."""
    findings: list[Finding] = []
    findings.extend(check_match_counts(lineup, tie_format))
    findings.extend(check_one_match_per_event(lineup))
    findings.extend(check_from_approved_list(lineup, approved_list))
    findings.extend(check_relative_order(lineup, approved_list))
    return ValidationResult.from_findings(findings)


def check_match_counts(lineup: Lineup, tie_format: TieFormat) -> list[Finding]:
    """R-13: Each event has exactly the number of matches the tie format sets."""
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


def check_one_match_per_event(lineup: Lineup) -> list[Finding]:
    """R-12: A player appears at most once within a single event, but may play
    across different events."""
    findings: list[Finding] = []
    for event in Event:
        player_counts: Counter[uuid.UUID] = Counter()
        for entry in lineup.entries:
            if entry.event == event:
                player_counts.update(entry.players())
        for player_id, count in player_counts.items():
            if count > 1:
                findings.append(
                    Finding(
                        severity=Severity.BLOCK,
                        location=Location(event=event, player_id=player_id),
                        rule=RULE_ONE_MATCH_PER_EVENT,
                        message=f"A player appears in {count} {event.value} matches",
                        how_to_fix=f"Use each player at most once in {event.value}",
                    )
                )
    return findings


def check_from_approved_list(
    lineup: Lineup, approved_list: ApprovedList
) -> list[Finding]:
    """R-10: Every player/pair in the lineup is an approved unit for its event."""
    approved_units = {(entry.event, entry.players()) for entry in approved_list.entries}
    findings: list[Finding] = []
    for entry in lineup.entries:
        if (entry.event, entry.players()) not in approved_units:
            findings.append(
                Finding(
                    severity=Severity.BLOCK,
                    location=Location(event=entry.event, position=entry.position),
                    rule=RULE_FROM_APPROVED_LIST,
                    message=(
                        f"{entry.event.value} position {entry.position} "
                        f"is not on the Approved Team List"
                    ),
                    how_to_fix="Pick a player or pair from the Approved Team List",
                )
            )
    return findings


def check_relative_order(lineup: Lineup, approved_list: ApprovedList) -> list[Finding]:
    """R-11: Within each event, the lineup keeps the relative Approved Team List order.
    Units may only be skipped, but not swapped out of their approved order."""
    approved_position = {
        (entry.event, entry.players()): entry.position
        for entry in approved_list.entries
    }
    findings: list[Finding] = []
    for event in Event:
        event_entries = sorted(
            (entry for entry in lineup.entries if entry.event == event),
            key=lambda entry: entry.position,
        )
        max_seen: int | None = None  # highest approved position placed so far
        for entry in event_entries:
            approved_pos = approved_position.get((entry.event, entry.players()))
            if approved_pos is None:
                continue  # not an approved unit
            if max_seen is not None and approved_pos < max_seen:
                findings.append(
                    Finding(
                        severity=Severity.BLOCK,
                        location=Location(
                            event=event,
                            position=entry.position,
                            player_id=entry.player_id,
                        ),
                        rule=RULE_RELATIVE_ORDER,
                        message=(
                            f"Approved Team List position {approved_pos} is placed "
                            f"below position {max_seen} in {event.value}"
                        ),
                        how_to_fix=(
                            f"Order {event.value} by the Approved Team List: "
                            f"position {approved_pos} must come before {max_seen}"
                        ),
                    )
                )
            if max_seen is None or approved_pos > max_seen:
                max_seen = approved_pos
    return findings
