# Leads App

Prospects submit their name, email, and resume through a public form. Both the prospect and an
attorney get an email. Attorneys log in to a dashboard, review each lead, download the resume,
and mark the lead as reached out (or undo it).

The stack was fixed by the assignment: FastAPI for the API and Next.js for the web app. I added
Postgres for data, MinIO for resume files, and Mailpit to catch outgoing email locally.

**More detail:**
[docs/DESIGN.md](docs/DESIGN.md) (decisions, data model, API) ·
[docs/AGENT_USAGE.md](docs/AGENT_USAGE.md) (how agents were used) ·
[docs/NOTES.md](docs/NOTES.md) (attribution, and every agent mistake with how it was caught) ·
[docs/prompt-logs/](docs/prompt-logs/)

## Running it

You need Docker Desktop, and `make` (preinstalled on macOS and most Linux distros). Nothing else
has to be installed.

```bash
git clone https://github.com/MaanasPeri23/alma-take-home.git
cd alma-take-home
make up      # builds and starts all five services; returns once every one is healthy (first run: a few minutes)
make seed    # creates the attorney login
```

`make up` copies `.env.example` to `.env` the first time. Every value in it is a local default;
there are no real credentials anywhere in this repo.

| URL | What it is |
| --- | --- |
| http://localhost:3000 | Public lead form |
| http://localhost:3000/dashboard | Attorney dashboard. Log in as `attorney@example.com` / `change-me-locally` |
| http://localhost:8025 | Mailpit, where every email the app sends ends up |
| http://localhost:8000/docs | Interactive API docs (Swagger) |
| http://localhost:9001 | MinIO console, where resumes are stored (`minioadmin` / `minioadmin`) |

### A two-minute tour

1. Open http://localhost:3000 and submit the form with a PDF, DOC or DOCX resume.
2. Open http://localhost:8025: there's a confirmation to the prospect and a "New lead" email to the
   attorney.
3. Try a fake file (any non-document renamed to `.pdf`): the form shows an error under the resume
   field. The type is checked by the file's contents, not its name.
4. Open http://localhost:3000/dashboard: you're sent to the login page. Log in.
5. Open the lead, download the resume, and mark it reached out. The history shows who did it and
   when. Undo moves it back to pending.

### Other commands

```bash
make test        # everything CI runs: ruff, alembic check, pytest, eslint, tsc, client drift check
make test-fast   # backend unit tests + frontend typecheck, no Docker needed (~5 s)
make smoke       # puts one file in MinIO and sends one email to Mailpit
make gen-client  # regenerate the frontend's API types from FastAPI's OpenAPI spec
make down        # stop everything (docker compose down -v also wipes the data)
```

## How it's built, and the tradeoffs

**The browser talks to one origin.** Next.js forwards every `/api/*` request to FastAPI, so the
browser never calls port 8000 directly. That means no CORS setup and no cross-port cookie issues.
The cost is an extra hop through the Next.js server. At this scale that doesn't matter, and it's
easy to replace with a real reverse proxy later.

**The API owns authentication.** Attorney accounts are seeded by a script, and there's no signup.
Passwords are hashed with bcrypt, and a successful login sets a JWT in an httpOnly cookie. Because
the check lives in FastAPI, the data is protected even if someone skips the UI and calls the API
directly. The web app's login redirect only makes the pages behave nicely. It isn't the security
boundary.

**A lead is saved before any email is sent.** Emails go out in a FastAPI background task after the
lead is stored and the response has been returned. If the mail server is down, the lead is still
safe and the error is logged. The tradeoff: if the API process dies between saving and sending,
that email is lost. The production fix is an outbox table, written in the same transaction as the
lead and drained by a worker that retries. I scoped that out and documented it instead of
building it.

**Storage and email sit behind small interfaces.** Business logic calls `StorageBackend` and
`EmailSender`, never boto3 or smtplib directly. Moving from MinIO to S3, or from Mailpit to SES or
Postmark, then changes configuration, not code. It also makes both easy to fake in tests. The cost
is one extra layer of indirection.

**Email is local-only on purpose.** Real providers need a verified domain (SPF, DKIM, DMARC) and
an API key. That's setup work, not engineering, and it would put a secret in a public repo. The app
still speaks plain SMTP, so switching providers means changing `SMTP_HOST`, `SMTP_PORT`, and
credentials.

**Uploads are validated by content, not by name.** Only PDF, DOC, and DOCX files are accepted, up to
5 MB. The type is checked by reading the file's first bytes, so an `.exe` renamed to `.pdf` is
rejected. Files are stored under a random UUID. The original filename is kept only as metadata and
is never used as a path.

**Lead state changes go through one table of allowed transitions.** `PENDING → REACHED_OUT` (and
back, for undo) is defined in a single map in the service layer. Anything outside that map returns
409. Every change also writes a row to `lead_state_events` recording who made it and when, in the same
transaction, and the lead row is locked while it changes, so two attorneys clicking at once can't
both apply it. That one mechanism gives us history and undo. Adding a state like `REJECTED` later is a one-line
change with no migration.

**The API contract comes first.** The TypeScript client in `frontend/lib/api/` is generated from
FastAPI's OpenAPI spec. The frontend can't drift from the backend without failing to compile, and
the two can be built in parallel once the contract is merged.

**Not built, but worth naming:** rate limiting and a CAPTCHA on the public form, the email outbox,
and routing leads to different attorneys. All of these are covered in
[docs/DESIGN.md](docs/DESIGN.md).

## Repository layout

```
backend/     FastAPI app: routers (HTTP only) → services (logic) → storage / email / models
frontend/    Next.js app: public form, login, attorney dashboard
docs/        Design doc, agent usage write-up, notes on agent mistakes, prompt logs
.claude/     Rules, hooks, and a reviewer agent for Claude Code (see below)
.github/     CI and automated PR review
```

## Tests

94 backend tests, most of them against real Postgres, MinIO and Mailpit, in a separate
`leads_test` database so they never touch demo data. They cover:
- **Upload rejection:** a fake file type, a file over 5 MB, an empty file, a path-traversal
  filename, and control characters in names.
- **Failure handling:** an email failure still saves the lead; a database failure deletes the
  stored file.
- **Auth:** 401 on every internal route (the list is read from the API spec), and forged, expired
  or unsigned tokens.
- **Leads:** paging, 404s, and every state transition checked against the allowed map, including
  its history row.

`make test` also fails if a database model changed without a migration, or if the frontend's
generated API types are out of date.

## How this was built

Most of the code was written with Claude Code, under constraints I set up first:
- **Rules** live in `.claude/CLAUDE.md`.
- **Hooks** lint every file the agent edits and run the fast tests before it can say it's done.
- **A read-only reviewer agent** checked every diff before commit, and found a real issue in
  almost every one.
- **The backend and frontend** were built in parallel in two git worktrees, against an API
  contract merged first.
- **Every PR** gets CI (a required check on `main`) plus an automated Claude review.
- **Nothing merges without me.**

Each commit ends with an `Agent:` trailer saying whether it was agent-written, hand-written, or
mixed. [docs/NOTES.md](docs/NOTES.md) records each place the agent got something wrong and how it
was caught. [docs/AGENT_USAGE.md](docs/AGENT_USAGE.md) is the short version.

## Progress

**Foundation** (PRs #2, #3)
- [x] F1: Agent rules, hooks, reviewer, design doc draft
- [x] F2: Docker setup for all five services, Makefile, empty apps, the `/api` proxy, CI
- [x] F3: Database tables and migrations, API contract, route stubs, generated client

**Backend** (PR #4)
- [x] B1: Storage and email interfaces
- [x] B2: Public lead submission
- [x] B3: Attorney login and seed script
- [x] B4: List, detail, resume download, state changes (with undo)

**Frontend** (separate worktree, built in parallel)
- [x] W1: Public form and thank-you page
- [ ] W2: Login and redirect when signed out
- [ ] W3: Dashboard, lead detail, download, mark reached out
- [ ] W4: Playwright end-to-end test

**Wrap-up**
- [x] D1: README, design doc, agent usage write-up, prompt logs
- [ ] Loom walkthrough and submission

## Notes

- The PR review bot runs on my Claude subscription (`CLAUDE_CODE_OAUTH_TOKEN`), so the repo
  doesn't need an Anthropic API key.
- `main` is protected: changes land through PRs only, CI must pass, and force pushes are blocked.
- MinIO no longer publishes its image on Docker Hub, so `minio/minio` fails to pull. I use
  `cgr.dev/chainguard/minio`, the same server rebuilt and published by Chainguard.
- Next.js 16 renamed `middleware.ts` to `proxy.ts`; the login redirect uses the new name.
