# Domain Rules

The rules the system must enforce, written as clear, testable statements so they can be turned directly into rules engine tests. This file is the behaviour specification for the shared rules engine. The engine's design and the structure of a validation result are in [technical.md](technical.md#major-technical-decisions) (Shared Rules Engine) and [technical.md](technical.md#validation-results) (Validation Results). For the entities these rules act on, see the ERD in [technical.md](technical.md#database-design). Domain terms are defined in [glossary.md](glossary.md).

Each rule has an ID (R-xx), a statement, and a check type:

- **Automatic:** the engine can decide it from the data.
- **Judgement:** needs a person; the engine flags or records, but does not decide.
- **Mixed:** part is automatic, part needs judgement.

A failing rule is a structured finding, not an error. Severity is `block` (the submission cannot pass) or `flag` (needs attention or justification). For example, a Singles order break is a `block`, while a Doubles or Mixed pair placed against combined-points order with no justification is a `flag`. Final severities are confirmed as the rules engine is built.

## Ranked Team List ordering (Phase A)

| ID | Rule | Check type |
| --- | --- | --- |
| R-01 | Singles Positions are ordered by Singles Player Points, and the relative order of ranked Singles players is never changed. | Automatic |
| R-02 | Doubles and Mixed pairs default to order by the pair's combined Player Points. | Automatic |
| R-03 | A Doubles or Mixed pair ordered against combined-points order is allowed only if a justification is attached. | Mixed: detect the deviation and the presence of a justification automatically; whether the justification is acceptable is judgement. |
| R-04 | Unranked players may be placed in any Position chosen by the Coach or Team Manager, as long as the relative order of ranked players is unchanged. | Mixed: the ranked order check is automatic; the unranked placement is judgement. |
| R-05 | Badminton NZ or another Association may challenge a pair they consider placed too high or too low. | Judgement |

## Protests (Phase A)

| ID | Rule | Check type |
| --- | --- | --- |
| R-06 | Once released, every Association can view every Team's Ranked Team List, and released lists are read-only to Associations. | Automatic |
| R-07 | A protest may be lodged only up to the protest deadline; after it, protesting is blocked. | Automatic |
| R-08 | A protest is resolved either by the Team adjusting its list or by Badminton NZ adjusting it with Referee approval, and the original list, the change, and the approver are all retained. | Mixed: the resolution is judgement; retaining the history is automatic. |
| R-09 | The protest deadline falls before the tournament starts, so Phase A must be fully resolved and approved before any Phase B check runs. | Automatic |

## Tie Lineup selection (Phase B)

| ID | Rule | Check type |
| --- | --- | --- |
| R-10 | Every player and pair in a Tie Lineup must come from that Team's Approved Team List. | Automatic |
| R-11 | The approved relative ranking order within each Event must be preserved in the lineup. | Automatic |
| R-12 | A player may play at most one match within a single Event, but may play across Singles, Doubles and Mixed. | Automatic |
| R-13 | The number of matches per Event is defined by the tournament's Tie Format. | Automatic |

## Substitutions (Phase B)

| ID | Rule | Check type |
| --- | --- | --- |
| R-14 | A substitution is permitted only for a special reason, such as injury. | Judgement |
| R-15 | A substitution may occur only between matches, never during a match. | Mixed: timing against match state is automatic; the reason is judgement. |
| R-16 | An injured player forfeits their current match, and a teammate may take their later matches. | Mixed: applying the change to later matches is automatic; the circumstance is judgement. |
| R-17 | The replacement must not already be playing in that Event. | Automatic |
| R-18 | A substitution takes effect only after the Referee approves it. | Automatic (state) |

## Submission, versioning and deadlines (both phases)

| ID | Rule | Check type |
| --- | --- | --- |
| R-19 | A Team may submit multiple times before the deadline; the latest submission is the one in effect, and earlier ones are marked superseded. | Automatic |
| R-20 | Submitting a Ranked Team List after its deadline is blocked. | Automatic |
| R-21 | A Tie Lineup submitted after a Tie has overrun is still accepted and marked late. | Automatic |
| R-22 | A retry after an unclear submission result must not create a duplicate; the idempotency key returns the original outcome instead. | Automatic |
