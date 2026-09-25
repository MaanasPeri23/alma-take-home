# Leads App

Prospects submit their name, email, and resume through a public form. Both the prospect and an
attorney get an email. Attorneys log in to a dashboard, review each lead, download the resume,
and mark the lead as reached out.

The stack was fixed by the assignment: FastAPI for the API and Next.js for the web app. I added
Postgres for data, MinIO for resume files, and Mailpit to catch outgoing email locally.

## Running it

You need Docker Desktop. Nothing else has to be installed to run the app.

```bash
make up      # build and start all five services; returns once every one is healthy
make test    # lint, typecheck, and tests, all run inside the containers
make down    # stop everything (add -v to docker compose down to wipe data)
```

| URL | What it is |
| --- | --- |
| http://localhost:3000 | The web app |
| http://localhost:8000/docs | Interactive API docs (Swagger) |
| http://localhost:8025 | Mailpit, where every email the app sends ends up |
| http://localhost:9001 | MinIO console, where uploaded resumes are stored (`minioadmin` / `minioadmin`) |

`make up` copies `.env.example` to `.env` the first time it runs. Every value in there is a
local default. There are no real credentials anywhere in this repo.

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
409. Every change also writes a row to `lead_state_events` recording who made it and when, which
gives us history and undo from one mechanism. Adding a state like `REJECTED` later is a one-line
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
docs/        Design doc, notes on agent mistakes, how agents were used
.claude/     Rules, hooks, and a reviewer agent for Claude Code (see below)
.github/     CI and automated PR review
```

## How this was built

Most of the code was written with Claude Code, under constraints I set up first. The rules live
in `.claude/CLAUDE.md`. A hook lints every file the agent edits and runs the fast tests before it
can say it's done. A separate read-only reviewer agent checks every diff before commit, and every
PR gets CI plus an automated review. Nothing merges without me.

Each commit ends with an `Agent:` trailer saying whether it was agent-written, hand-written, or
mixed. [docs/NOTES.md](docs/NOTES.md) records the places the agent got something wrong and how
each one was caught.

## Progress

Each step is one commit. The note after each step is the check I do by hand before committing it.

**Foundation** (PR 1)
- [x] F1: Agent rules, hooks, reviewer, design doc draft
- [x] F2: Docker setup for all five services, Makefile, empty apps, the `/api` proxy, CI.
  Check: the web app, `/api/health`, Mailpit, and MinIO all load
- [x] F3: Database tables and migrations, API request/response shapes, route stubs, generated
  client. Check: Swagger lists every route

**Backend** (PR 2)
- [x] B1: Storage and email interfaces. Check: a test email shows up in Mailpit and a test file in MinIO
- [x] B2: Public lead submission. Check: a real PDF returns 201 with two emails; a renamed `.exe` returns 422
- [x] B3: Attorney login and seed script. Check: listing leads without login returns 401
- [x] B4: List, detail, resume download, state changes. Check: marking twice returns 409

**Frontend** (PR 3, built in parallel with the backend)
- [ ] W1: Public form and thank-you page. Check: validation errors show under the right field
- [ ] W2: Login and redirect when signed out. Check: `/dashboard` sends you to `/login`
- [ ] W3: Dashboard, lead detail, download, mark reached out. Check: the full flow in a browser
- [ ] W4: Playwright end-to-end test. Check: watch it run once

**Wrap-up**
- [ ] D1: Final README, design doc, agent usage write-up, prompt logs. Check: a fresh clone runs from this README alone
- [ ] Loom walkthrough and submission

If time runs short, I cut in this order: the undo button, list filters and pagination in the UI,
then the Playwright test. The docs and the walkthrough stay.

## Notes

Decisions and surprises along the way. Agent mistakes are logged separately in
[docs/NOTES.md](docs/NOTES.md).

- The PR review bot runs on my Claude subscription (`CLAUDE_CODE_OAUTH_TOKEN`), so the repo
  doesn't need an Anthropic API key.
- `main` is protected: changes land through PRs only, and force pushes are blocked.
- MinIO no longer publishes its image on Docker Hub, which is where Docker downloads images by
  default, so `minio/minio` fails to pull. I use `cgr.dev/chainguard/minio` instead. It's the same
  MinIO server, rebuilt and published by Chainguard. Everything still runs in Docker; only this
  one image comes from a different registry.
- Next.js 16 renamed `middleware.ts` to `proxy.ts`. The login redirect (W2) will use the new name.
- API collection routes are declared without a trailing slash. FastAPI's automatic slash redirect
  would otherwise point the browser at the internal `api:8000` host, which it can't reach.
