# CLAUDE.md

Agent context for the Badminton New Zealand Team Events backend. Read this first, then open the linked docs as needed. This file summarises and points; it does not copy the docs.

## What this is

A web application for Badminton New Zealand that digitises and validates Team Event submissions: Ranked Team Lists before a tournament (Phase A) and Tie Lineups during it (Phase B). It replaces a manual, paper-based process in which officials check lists and lineups by hand against Player Points and the tournament rules under tight time pressure. This repository is the backend (API, domain rules, database). The frontend is a separate repository.

## Stack

- Backend: Python, FastAPI, Pydantic for request/response models, SQLModel for typed models, Alembic for migrations.
- Database: PostgreSQL.
- Frontend (separate repo): TypeScript, React, Next.js, TanStack Query, with a typed client generated from this backend's OpenAPI schema.

Full stack and the reasons behind it: [docs/technical.md](docs/technical.md#technology-stack).

## Key decisions in brief

- **Shared rules engine.** One pure module powers both the live check (while building, saves nothing) and the official check (on submit), so the two can never disagree.
- **Versioned Player Points.** Points are imported as frozen, versioned snapshots; checks read the snapshot in force, never the live source.
- **Immutable submission history.** Each submission is a new row, never an update. The new-row-per-submission behaviour is what delivers immutability.
- **Approved Team List is a state** of the Ranked Team List (`approval_status`), not a separate entity.
- **Transactional writes.** A state change and its audit record commit in the same database transaction.
- **Server-side authorisation.** Role-based access plus team and association scope, enforced on the server on every request. The frontend only hides what a role cannot do; the server is the gate.
- **Audit log records business actions, not endpoint hits**, and is append-only.

Full architecture, decisions, and API design: [docs/technical.md](docs/technical.md).

## Engineering standards

- Clean, simple, straightforward code. Not over-engineered. Prefer the clear solution over the clever one.
- Enterprise grade and production ready: reliable and robust enough to run during live tournaments.
- Secure by default: validate input at the boundary, enforce authorisation on the server, never trust the client, keep secrets out of the source, and treat player data as protected under the NZ Privacy Act 2020. The system must not be open to abuse or misuse.
- Fail safely: domain rule failures are returned as structured validation results, not crashes; genuine errors are handled explicitly rather than swallowed.
- Tested where it matters: the rules engine and the submission, versioning, and authorisation paths carry tests, so later changes are safe to make.

## Documentation

- [docs/non-technical.md](docs/non-technical.md): problem, domain, current state, and all requirements (user roles, the 39 user stories, non-functional requirements).
- [docs/technical.md](docs/technical.md): architecture, system design, workflows, technical decisions, the ERD, API design, security, deployment, testing, and the implementation plan.
- [docs/glossary.md](docs/glossary.md): domain term definitions.
- [docs/rules.md](docs/rules.md): the domain rules as testable statements, next to the rules engine.

## Source of truth

If the code and the docs disagree, the code is the source of truth. Update the doc to match, rather than changing the code to fit a stale doc. The ERD in docs/technical.md is a guideline and is expected to change as the build progresses; flag schema changes when you make them.
