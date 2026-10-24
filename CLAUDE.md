# CLAUDE.md

Agent context for the Badminton New Zealand Team Events backend. Read this first, then open the linked docs as needed. This file summarises and points; it does not copy the docs.

## What this is

A web application for Badminton New Zealand that digitises and validates Team Event submissions. It replaces a manual, paper-based process in which officials check lineups by hand against the tournament rules under tight time pressure, and it works alongside the officials' existing Tournament Software rather than replacing it.

The work is delivered in two phases:

- **Phase B, the first release.** The in-tournament Tie Lineup check. Teams submit a lineup into a round slot, the system checks it against that Team's Approved Team List and the rules, and an official reviews it and copies the approved lineup into Tournament Software.
- **Phase A, a later release.** The pre-tournament Ranked Team List flow: submission, checking against Player Points, release, protests, and approval, producing the Approved Team List.

This repository is the backend (API, domain rules, database). The frontend is a separate repository.

## Current focus

**Build Phase B.** Phase A is fully documented but deferred; do not build it unless asked. In the first release, Teams, their Access Details, and their Approved Team Lists are seeded (entered directly), standing in for the data Phase A will later produce. Everything downstream of that seed is the same whether the data was seeded or produced by Phase A, so Phase B can be built and shipped first.

## Stack

- Backend: Python, FastAPI, Pydantic for request/response models, SQLModel for typed models, Alembic for migrations.
- Database: PostgreSQL.
- Frontend (separate repo): TypeScript, React, Next.js, TanStack Query, with a typed client generated from this backend's OpenAPI schema.

Full stack and the reasons behind it: [docs/technical.md](docs/technical.md#technology-stack).

## Key decisions in brief

- **No matchup stored.** The system never records which Team plays which. Each lineup is checked against its own Team's Approved Team List. This is what keeps the system complementary to Tournament Software; there is no Tie entity and no Tie Sheet.
- **Round slot as the submission window.** Submissions are gated by a slot an official opens and closes, with an official-set cut-off they can extend or reopen for specific teams, rather than fixed deadlines, because the draw is not known far ahead.
- **Access details for team login.** Teams sign in with access details scoped to their own team and submissions; officials and associations use accounts.
- **Phased delivery, Phase B first.** The Approved Team List (and the access details) are the seam: seeded in the first release, produced by Phase A later. Nothing in the Phase B flow changes when Phase A arrives.
- **Shared rules engine.** One pure module powers both the live check (while building, saves nothing) and the official check (on submit), so the two can never disagree.
- **Approved Team List is a state** of the Ranked Team List (`approval_status`), not a separate entity.
- **Immutable submission history.** Each submission is a new row, never an update. The new-row-per-submission behaviour is what delivers immutability; the latest is in effect and earlier ones are superseded.
- **Versioned Player Points (Phase A).** Points are imported as frozen, versioned snapshots; checks read the snapshot in force, never the live source.
- **Transactional writes.** A state change and its audit record commit in the same database transaction.
- **Server-side authorisation.** Role-based access plus team and association scope, enforced on the server on every request. The frontend only hides what a role cannot do; the server is the gate.
- **Audit log records business actions, not endpoint hits**, and is append-only.

Full architecture, decisions, ERD, and API design: [docs/technical.md](docs/technical.md).

## Engineering standards

Clean, simple, straightforward code, not over-engineered, enterprise grade and production ready, secure by default, and tested where it matters. These are stated as concrete, actionable rules in [docs/conventions.md](docs/conventions.md). Follow that file when writing code.

## Documentation

- [docs/non-technical.md](docs/non-technical.md): the problem, domain, current state, and all requirements (user roles, the 42 user stories across 12 epics, non-functional requirements).
- [docs/technical.md](docs/technical.md): architecture, system design, workflows, technical decisions, the ERD, API design, security, deployment, testing, and the delivery plan.
- [docs/glossary.md](docs/glossary.md): domain term definitions.
- [docs/rules.md](docs/rules.md): the domain rules as testable statements, next to the rules engine.
- [docs/conventions.md](docs/conventions.md): how code is written here, with the testing and secure-coding standards.

## Source of truth

If the code and the docs disagree, the code is the source of truth. Update the doc to match, rather than changing the code to fit a stale doc. The ERD in docs/technical.md is a guideline and is expected to change as the build progresses; flag schema changes when you make them.
