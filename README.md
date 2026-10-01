# Badminton New Zealand Team Events (Backend)

Backend for a web application that digitises and validates Badminton New Zealand Team Event submissions: Ranked Team Lists before a tournament (Phase A) and Tie Lineups during it (Phase B). It replaces a manual, paper-based checking process. The frontend is a separate repository.

Stack: Python, FastAPI, SQLModel, PostgreSQL. See the docs below for the full picture.

## Documentation

Start with [CLAUDE.md](CLAUDE.md) for a short project summary, the stack, the key decisions, and the engineering standards. The detailed planning docs live in [docs/](docs/):

- [docs/non-technical.md](docs/non-technical.md): problem, domain, current state, and all requirements (user roles, the 39 user stories, non-functional requirements).
- [docs/technical.md](docs/technical.md): architecture, system design, workflows, technical decisions, the ERD, API design, security, deployment, testing, and the implementation plan.
- [docs/glossary.md](docs/glossary.md): domain term definitions.
- [docs/rules.md](docs/rules.md): the domain rules as testable statements.

If the code and the docs disagree, the code is the source of truth; update the doc to match.
