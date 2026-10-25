# Domain Rules

The rules the system must enforce, written as clear, testable statements so they can be turned directly into rules engine tests. This file is the behaviour specification for the shared rules engine. The engine's design and the structure of a validation result are in [technical.md](technical.md#major-technical-decisions) (Shared Rules Engine) and [technical.md](technical.md#validation-results) (Validation Results). For the entities these rules act on, see the ERD in [technical.md](technical.md#database-design). Domain terms are defined in [glossary.md](glossary.md).

The rules are grouped by phase. **Phase B is the first release**, so its rules come first; the **Phase A rules are the later release** and are not built yet. Cross-cutting submission rules apply to both.

Each rule has an ID (R-xx), a statement, and a check type:

- **Automatic:** the engine can decide it from the data.
- **Judgement:** needs a person; the engine flags or records, but does not decide.
- **Mixed:** part is automatic, part needs judgement.

A failing rule is a structured finding, not an error. Severity is `block` (the submission cannot pass) or `flag` (needs attention or justification). For example, a lineup drawn from outside the Approved Team List is a `block`, while a Doubles or Mixed pair placed against combined-points order with no justification is a `flag`. Final severities are confirmed as the rules engine is built.

Rule IDs are stable and are never reused. Retired IDs are listed at the end.

## Tie Lineup selection (Phase B, first release)

The Tie Format gives a count of Matches per Event, and a Tie Lineup fills one entry per (Event, Position) slot. Event is defined in [glossary.md](glossary.md).

| ID | Rule | Check type |
| --- | --- | --- |
| R-10 | Every player and pair in a Tie Lineup must come from that Team's Approved Team List. | Automatic |
| R-11 | The approved relative ranking order within each Event must be preserved in the lineup. | Automatic |
| R-12 | A player may play at most one Match within a single Event, but may play across different Events (for example Men's Singles, Men's Doubles, and Mixed). | Automatic |
| R-13 | The number of Matches per Event is set by the tournament's Tie Format. | Automatic |

## Round slots (Phase B, first release)

| ID | Rule | Check type |
| --- | --- | --- |
| R-23 | A Tie Lineup can be submitted only while its round slot is open; once the slot closes, submission is blocked. | Automatic (state) |
| R-24 | A Technical Official sets each slot's cut-off and may extend it, or reopen a closed slot for specific teams; an extension or reopen lets the affected teams submit again. | Automatic (state) |
| R-25 | A round slot may be limited to specific teams; a team not included in the slot cannot submit to it. | Automatic |

## Submission and versioning (both phases)

| ID | Rule | Check type |
| --- | --- | --- |
| R-19 | A Team may submit multiple times while submission is open; the latest submission is the one in effect, and earlier ones are marked superseded. | Automatic |
| R-22 | A retry after an unclear submission result must not create a duplicate; the idempotency key returns the original outcome instead. | Automatic |
| R-27 | When a round slot closes, the final check runs on each team's latest lineup, and that result is the authoritative record. | Automatic |

## Ranked Team List ordering (Phase A, later release)

| ID | Rule | Check type |
| --- | --- | --- |
| R-01 | Singles Positions are ordered by Singles Player Points, and the relative order of ranked Singles players is never changed. | Automatic |
| R-02 | Doubles and Mixed pairs default to order by the pair's combined Player Points. | Automatic |
| R-03 | A Doubles or Mixed pair ordered against combined-points order is allowed only if a justification is attached. | Mixed: detect the deviation and the presence of a justification automatically; whether the justification is acceptable is judgement. |
| R-04 | Unranked players may be placed in any Position chosen by the Coach or Team Manager, as long as the relative order of ranked players is unchanged. | Mixed: the ranked order check is automatic; the unranked placement is judgement. |
| R-05 | Badminton NZ or another Association may challenge a pair they consider placed too high or too low. | Judgement |

## Protests and Phase A deadlines (Phase A, later release)

| ID | Rule | Check type |
| --- | --- | --- |
| R-06 | Once released, every Association can view every Team's Ranked Team List, and released lists are read-only to Associations. | Automatic |
| R-07 | A protest may be lodged only up to the protest deadline; after it, protesting is blocked. | Automatic |
| R-08 | A protest is resolved either by the Team adjusting its list or by Badminton NZ adjusting it with Referee approval, and the original list, the change, and the approver are all retained. | Mixed: the resolution is judgement; retaining the history is automatic. |
| R-09 | The protest deadline falls before the tournament starts, so Phase A must be fully resolved and approved before any Phase B check runs. | Automatic |
| R-20 | Submitting a Ranked Team List after its deadline is blocked. | Automatic |

## Team composition and eligibility

The tournament's male and female player limits are optional and are set at tournament setup (Phase B), where R-31 checks them against the Tie Format. R-28 to R-30 then use `Player.sex` and those limits when the Ranked Team List is built and checked (Phase A, later release). The Phase B lineup check inherits correct entries from the Approved Team List and does not re-check these.

| ID | Rule | Check type |
| --- | --- | --- |
| R-28 | A player may be listed only in events for their sex: men in men's events, women in women's events, either in Mixed Doubles. | Automatic |
| R-29 | A Mixed Doubles pair must be one male and one female. | Automatic |
| R-30 | A Team's Ranked Team List must respect the tournament's minimum and maximum male and female player counts, where the official has set them (each is optional). | Automatic |
| R-31 | The player-count limits must be consistent with the Tie Format: a maximum below the number of Matches a Tie requires, or a minimum above the maximum, is rejected at tournament setup. | Automatic |

## Retired rule IDs

Never reuse these numbers. They are kept here so references do not silently resolve to a different rule.

- **R-14 to R-18** — Substitution rules. Substitutions are out of the system's scope; they are handled by officials during play.
- **R-21** — "A Tie Lineup submitted after a Tie has overrun is still accepted and marked late." Replaced by the round-slot model: submission is gated by an open slot (R-23), and overruns are handled by the official extending or reopening the slot (R-24).
