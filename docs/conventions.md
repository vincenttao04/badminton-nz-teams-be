# Conventions

How code is written in this repository. The other docs describe *what* the system does and *why*; this file describes *how* to build it. [CLAUDE.md](../CLAUDE.md) links here, and its engineering standards are made concrete below. Where this file and the system-level design in [technical.md](technical.md) overlap, technical.md owns the design decision and this file owns the coding practice.

## Code

- Clean, simple, straightforward. Prefer the clear solution over the clever one. Do not add abstraction, configuration, or indirection before a second caller needs it.
- Small, single-purpose functions and modules. A reader should be able to tell what a unit does from its name and signature.
- Type everything. Pydantic models at the API boundary, SQLModel for persisted models, type hints throughout. The generated OpenAPI schema is the frontend's contract, so request and response models are public API and change deliberately.
- No dead code, no speculative features, no commented-out blocks left behind.

## Module boundaries

- **The rules engine is pure.** It takes data in and returns a validation result; it does no I/O, no database access, and knows nothing about FastAPI. This is what lets the same engine power the live check and the official check (see [rules.md](rules.md) and the Shared Rules Engine decision in [technical.md](technical.md#major-technical-decisions)), and it is what makes the rules unit-testable in isolation.
- **Thin API handlers.** A route validates input, authorises, calls a service, and shapes the response. Business logic lives in services and the rules engine, not in handlers.
- **Database access through SQLModel**, behind the services. No raw SQL strings in handlers.

## Error handling

- **Domain validation failures are not errors.** A broken rule returns a structured validation result (`ok` plus `findings`), never an exception or a 500. The result shape is in [technical.md](technical.md#validation-results); the rules are in [rules.md](rules.md).
- **Genuine errors are handled explicitly**, not swallowed. Use a consistent error response format and standard HTTP status codes. Submission conflicts and submissions to a closed slot return `409 Conflict`.
- Never let an unexpected exception leak internal detail to the client.

## Security

Security is not a later milestone; write it in from the first endpoint.

- Validate every input at the boundary with Pydantic. Never trust the client; no client-side check is a security boundary.
- Authorise on the server on every protected request: role-based access plus team, association, and tournament scope. The frontend only hides what a role cannot do.
- Hash passwords and team access details with a strong algorithm such as Argon2id. Store sessions in httpOnly, Secure, SameSite cookies. Rate-limit authentication endpoints.
- Parameterise all database queries through the ORM. Keep secrets out of the source. Add CSRF protection for cookie auth.
- Submissions carry an idempotency key so a retried request cannot create a duplicate version.
- Treat player data as protected under the NZ Privacy Act 2020: collect the minimum, and keep it in a New Zealand or Australian region.

## Data and migrations

- **Every schema change goes through an Alembic migration.** The SQLModel models and the migration are the authoritative schema; the ERD in [technical.md](technical.md#database-design) is a guideline. Flag schema changes to the project owner when you make them.
- **Immutability is a new row, not a mutation.** A resubmission inserts a new version row; it never updates an earlier one. The latest is in effect, earlier ones are superseded.
- **A state change and its audit record commit in one transaction.** If the state write succeeds the audit write must succeed, or both roll back.

## Testing

Tests are the safety net that lets later changes be made confidently. Write them with the feature, not afterwards.

- **The rules engine has comprehensive unit tests:** at least one per rule in [rules.md](rules.md) (by ID), plus the edge cases, covering both `block` and `flag` outcomes.
- **The submission, versioning, and authorisation paths carry integration tests:** a closed slot rejects a submission, a resubmission supersedes the previous version, an idempotent retry returns the original outcome, and a role cannot act outside its scope.
- A change to a rule or a submission path is not done until its test is updated or added.

## Adding to the system

- **A new endpoint:** thin handler, then validate and authorise, then call a service, then (for a write) one transaction that changes state and writes the audit record. Add it under the `/v1` prefix.
- **A new or changed rule:** state it in [rules.md](rules.md) with a stable ID, implement it in the pure rules engine, and add its test. Never reuse a retired ID.
- **A schema change:** update the SQLModel model, generate an Alembic migration, and flag it to the owner.

## What not to do

- Do not model the matchup (which Team plays which) or build a Tie Sheet; both stay in Tournament Software.
- Do not build Phase A features in the first release. Phase A is documented but deferred.
- Do not over-document. Keep these files few and high-value; a file that goes stale misleads the agent more than a missing one.
