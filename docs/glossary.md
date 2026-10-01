# Glossary

Domain terms for the Badminton New Zealand Team Events system. This file is the single definition source for these terms; the other documents use them and link here rather than redefining them. For how these terms map to database tables, see the ERD in [technical.md](technical.md#database-design).

| Term | Definition |
| --- | --- |
| Team Event | A competition where Associations enter Teams that compete against each other. Made up of many Ties. |
| Association | A regional body that enters one or more Teams. |
| Team | A squad of players representing an Association, run by a Team Manager and Coach. |
| Team Manager | Submits the Ranked Team List and each Tie Lineup to Badminton NZ. |
| Coach | Sets the ranking order, places unranked players, and builds each Tie Lineup. |
| Player / Pair | A single player (Singles) or two players together (Doubles or Mixed). |
| Player Points | Badminton NZ's official National Ranking points. Badminton NZ maintains them, and the most recent version is the one used. |
| Event | A discipline: Singles, Doubles, or Mixed Doubles. |
| Position | A ranked slot within an Event, ordered by strength (for example, first Singles, second Singles). |
| Tie | A contest between two Teams, decided across a set number of matches in each Event. |
| Tie Format | How many matches each Event has in a Tie. Varies by tournament. |
| Ranked Team List | The ordered list submitted before the tournament. It states the Position each player or pair is eligible to play. Checked by Badminton NZ and other Associations, then approved by the Referee. |
| Approved Team List | A Ranked Team List approved by the Referee. Used to check Tie Lineups during the tournament. It is a state of the Ranked Team List, not a separate record. |
| Tie Lineup | The selection submitted for one Tie, drawn from the Approved Team List. |
| Protest | A challenge one Association raises against another Team's Ranked Team List before the tournament, for not following the ranking rules. |
| Substitution | Replacing a player between matches in a Tie for a special reason, such as injury. |
| Referee | Checks lists and lineups. Approves protest adjustments and substitutions. |
| Technical Officials | Receive submissions, run the tournament with the Referee, and resolve issues on the day. |
| Tie Sheet | The printed matchup sheet showing both Teams' lineups, Position by Position. Used by everyone at the event, including players, managers, coaches, and spectators. |
| Snapshot | A frozen, versioned copy of Player Points imported from Tournament Software. Checks read the snapshot in force rather than the live source, so validation is fast and reproducible. A snapshot is one import; the per player, per event points sit in entries that belong to it. |
| Superseded | The status of a submission that a later submission has replaced. When a new Ranked Team List or Tie Lineup version is submitted, the earlier version is marked superseded and the latest is the one in effect. |
