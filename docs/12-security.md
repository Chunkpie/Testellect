# 12 — Security

## Authentication

- **JWT-based**, access token (short-lived, default 30 min) + refresh token (longer-lived, default 14 days, stored hashed in `refresh_tokens` table per `03-database-schema.md`, revocable).
- Passwords hashed with **bcrypt or argon2** (argon2 preferred for new builds if the dependency is acceptable on target hardware) — never plaintext, never reversible encryption.
- Login endpoint (`POST /api/v1/auth/login`) rate-limited per IP/email (e.g., 5 attempts per 15 minutes) to slow down brute-force attempts, even in an offline LAN context — a compromised device on the school network shouldn't get unlimited login attempts.
- Refresh token rotation: each use of a refresh token issues a new refresh token and invalidates the old one (detect reuse of an already-rotated token as a signal of possible token theft, and revoke the whole token family if detected).

## Authorization Model

- **Role-Based Access Control** with four roles: `administrator`, `teacher`, `principal`, `deo` (per `03-database-schema.md`).
- Every protected endpoint declares its allowed roles explicitly via a FastAPI dependency (`require_role([...])`) — default-deny, not default-allow. No endpoint should be reachable without an explicit role check unless it's on the small, explicit public allowlist (`/auth/login`, `/auth/refresh`, `/health`).
- **School-scoping**: every service function that queries school-specific tables takes the current user's `school_id` and applies it as a hard filter — this must happen in the service layer, not just be "implied" by the frontend only showing the user their own school's data. A teacher's JWT does not grant access to another school's data even if they guess another school's resource ID.
- **DEO scoping**: DEO-role users are scoped by `district_id` across all schools in that district — implement as a separate scoping branch in the same authorization helper, not a special-cased copy of every query.
- **Principal scoping**: principals see all classes/teachers within their own `school_id` (broader than a teacher, who by default sees only their own assigned classes — confirm this assumption against how the school actually wants teacher visibility configured, and make it a per-school setting if there's any ambiguity).

## Audit Logging

Every state-changing action writes an `audit_logs` row (per `03-database-schema.md`) including at minimum:

- User creation/deactivation, role changes
- Student/class creation, edit, deletion
- Book upload, deletion, reprocessing
- Question approval, rejection, edit
- Blueprint creation, paper generation
- OMR scan, manual score correction
- Report generation
- Backup creation/restoration
- Settings changes
- Failed login attempts (for security monitoring, not just successful actions)

Audit logs are **append-only** from the application's perspective — no endpoint should ever update or delete an `audit_logs` row. Administrators can view audit logs for their own school; DEO can view across their district; there is no endpoint that allows cross-district audit log access.

## Data protection

- Student PII (names, roll numbers, DOB) stays within the local deployment — never transmitted externally, consistent with the offline-first constraint in `01-project-overview.md`.
- Database file (`gseb.db`) and Shared File Storage should sit on a Docker volume with host filesystem permissions restricted to the deploying user/service account — document this in `16-installation.md` rather than relying on application-level encryption alone for a single-PC deployment (full-disk encryption at the OS level is the more appropriate control here and should be recommended, not re-implemented at the app layer).
- Backups (`14-docker-deployment.md`/`backups` table) should be encrypted at rest if they're ever moved off the original machine (e.g., a password-protected archive) — flag this as a requirement for the backup service implementation, since a backup file is a full copy of student PII.

## Input validation and injection protection

- All input validated via Pydantic schemas before reaching service logic (per `04-backend-specification.md`).
- SQLAlchemy ORM usage (parameterized queries by construction) — no raw string-interpolated SQL anywhere in the codebase.
- File upload validation: enforce file type (PDF only for book uploads, image types only for OMR scan uploads) by content inspection (magic bytes), not just filename extension; enforce a maximum file size; store uploads outside any web-servable static directory and only serve them back through authenticated endpoints that re-validate ownership/school-scoping on every download.
- Sanitize any user-supplied text that gets embedded into LLM prompts (per `06-ai-engine.md`) against basic prompt-injection patterns where that text originates from less-trusted sources (e.g., raw extracted PDF text could in theory contain text designed to manipulate a downstream prompt) — at minimum, clearly delimit untrusted content within prompts (as already specified in `07-rag-architecture.md`'s prompt assembly pattern) so instructions-vs-content boundaries are explicit to the model.

## Transport security

Even on a LAN/offline deployment, serve the frontend and API over HTTPS using a self-signed or locally-issued certificate (documented in `14-docker-deployment.md`) rather than plaintext HTTP, particularly because JWTs and student data traverse the school's local network and multiple devices (teacher laptops, admin PCs) may share that network with other, less-trusted devices.

## Secrets management

- `JWT_SECRET_KEY` must be a long, randomly generated value, generated fresh per deployment (e.g., during first-run setup in `16-installation.md`) — never a hardcoded default shipped in the repo or Docker image.
- No secrets committed to version control; `.env` files are gitignored, with a `.env.example` template showing required keys without real values.

## Dependency and container hygiene

- Pin dependency versions (`requirements.txt`/`package.json` with locked versions) so a rebuild months later doesn't silently pull in a different, potentially vulnerable version.
- Run containers as non-root users where feasible (set a non-root `USER` in each Dockerfile).
- Keep the base images reasonably current at release time; document a periodic update cadence in `17-developer-guide.md` rather than treating this as a one-time concern.

## Known limitations to document for users (not to hide)

Be upfront in `16-installation.md` that this is a single-machine, LAN-deployed system: if the host PC is physically stolen or compromised, an attacker with disk access could potentially access the SQLite database directly, bypassing application-level auth. OS-level disk encryption and physical security of the host machine are explicitly the school's responsibility and should be called out in installation guidance, not silently assumed.
