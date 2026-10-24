# Glossary

Domain terms for the Badminton New Zealand Team Events system. This file is the single definition source for these terms; the other documents use them and link here rather than redefining them. For how these terms map to database tables, see the ERD in [technical.md](technical.md#database-design).

| Term | Definition |
| --- | --- |
| Team Event | A competition where Associations enter Teams that compete against each other. Made up of many Ties. |
| Association | A regional body that enters one or more Teams. |
| Team | A squad of players representing an Association, run by a Team Manager and Coach. Signs in with Access Details scoped to itself. |
| Team Manager | Submits each Tie Lineup (and, in Phase A, the Ranked Team List) to Badminton NZ. |
| Coach | Sets the ranking order, places unranked players, and builds each Tie Lineup. |
| Player / Pair | A single player (Singles) or two players together (Doubles or Mixed). |
| Player Points | Badminton NZ's official National Ranking points. Badminton NZ maintains them, and the most recent version is the one used. Used only in Phase A. |
| Event | A discipline: Singles, Doubles, or Mixed Doubles. |
| Position | A ranked slot within an Event, ordered by strength (for example, first Singles, second Singles). |
| Tie | A contest between two Teams, decided across a set number of Matches in each Event. A domain term only: the system does not model the matchup (which Team plays which); that stays in Tournament Software. |
| Match | A single contest between two Players or Pairs within a Tie. |
| Tie Format | How many Matches each Event has in a Tie. Varies by tournament. |
| Round Slot | A submission window a Technical Official opens for a wave of Ties that start together. Teams submit their Tie Lineups while it is open; it closes at a cut-off the official sets. The official can extend the cut-off or reopen the slot for specific teams when a Tie runs late. Slots replace fixed per-Tie deadlines, because the draw is not known far ahead. |
| Access Details | The credential a Team uses to sign in and submit, scoped to that Team's own submissions. Issued per Team by a Technical Official, and reissued by an official if lost. A deliberately non-technical term; the concrete mechanism is decided in code. |
| Ranked Team List | The ordered list submitted before the tournament. It states the Position each player or pair is eligible to play. Checked against Player Points and by other Associations, then approved by the Referee. (Phase A.) |
| Approved Team List | A Ranked Team List approved by the Referee. The reference the Tie Lineup check runs against. It is a state of the Ranked Team List (`approval_status`), not a separate record. In the first release it is seeded; in Phase A it is produced by the approval flow. |
| Tie Lineup | The selection a Team submits for one Tie, drawn from its Approved Team List. |
| Protest | A challenge one Association raises against another Team's Ranked Team List before the tournament, for not following the ranking rules. (Phase A.) |
| Referee | Checks lists and lineups and approves them. In Phase A, approves protest adjustments. |
| Technical Officials | Open and close round slots, receive submissions, review and copy approved lineups into Tournament Software, run the tournament, and resolve issues on the day. |
| Snapshot | A frozen, versioned copy of Player Points imported from Tournament Software. Checks read the snapshot in force rather than the live source, so validation is fast and reproducible. A snapshot is one import; the per player, per event points sit in entries that belong to it. (Phase A.) |
| Superseded | The status of a submission that a later submission has replaced. When a new Ranked Team List or Tie Lineup version is submitted, the earlier version is marked superseded and the latest is the one in effect. |
| Seed (seeded first release) | For the first release (Phase B), Teams, their Access Details, and their Approved Team Lists are entered directly rather than produced by Phase A. Phase A later generates the same data against the same model. |

## Out of the system's scope

These are real parts of the manual process but the system does not implement them. They are defined here only so the other documents can refer to them.

| Term | Definition |
| --- | --- |
| Tie Sheet | The printed matchup sheet showing both Teams' lineups, Position by Position. It needs the matchup, so it stays in Tournament Software; the system does not produce it. |
| Substitution | Replacing a player between Matches in a Tie for a special reason, such as injury. Handled by officials during play, not by the system. |

## Phases

| Term | Definition |
| --- | --- |
| Phase A | The pre-tournament half: Ranked Team List submission, checking against Player Points, release, protests, and Referee approval, producing the Approved Team List. The later release. |
| Phase B | The in-tournament half: Tie Lineup submission and checking against the Approved Team List, through round slots. The first release. |
