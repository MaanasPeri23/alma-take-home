# NOTES

## Attribution

Every commit also carries an `Agent:` trailer (`claude-code`, `mixed`, or `hand-written`).

| Area | Origin | Notes |
| --- | --- | --- |
| docs/DESIGN.md decisions | Hand-written | Agent drafted structure and diagrams from the handoff |
| CLAUDE.md, .claude/ hooks + reviewer | Hand-written | Agent transcribed; added F1 guards to hooks (see catches) |
| backend/app/services/ | Agent, reviewed | |
| frontend/lib/api/ | Generated | From OpenAPI |

## Agent catches

<!--
### [short title]
- What the agent produced:
- Why it was wrong:
- Caught by: hook | reviewer subagent | PR bot | manual test | reading the diff
- Fix: [commit hash]
-->

### Hook scripts from the handoff would block every edit and stop during F1
- What the agent produced: the handoff's `lint.sh` and `test.sh`, meant to be copied verbatim.
- Why it was wrong: `test.sh` runs `make test-fast`, but the Makefile doesn't exist until F2, so the Stop hook would fail on every stop. `lint.sh` runs `cd backend && ruff ...`, but `backend/` doesn't exist yet and ruff wasn't installed on the host, so every `.py` edit would exit 2.
- Caught by: reading the diff (checked the host tools while planning F1, before the first commit)
- Fix: guards added to both hooks in F1 (skip when the Makefile, directory, or tool is missing).

### F2 plan used a MinIO image that no longer exists
- What the agent produced: `docker-compose.yml` with `image: minio/minio`, from memory of the usual setup.
- Why it was wrong: MinIO stopped publishing to Docker Hub (and `quay.io/minio/minio` now returns 401), so `make up` failed on a clean machine and CI would have failed the same way.
- Caught by: manual test (`make up` failed on the pull)
- Fix: switched to `cgr.dev/chainguard/minio` (same server binary; `mc` included, so the healthcheck didn't change) in the F2 commit.

### Pushed a feature branch without announcing it
- What the agent produced: `git push` of `feat/foundation`, chained onto the end of a commit command and reported only as "pushed".
- Why it was wrong: the rules allowed pushing feature branches, but the human saw fresh pushes on GitHub with no PR and no heads-up, which reads as unreviewed work leaving the machine. `main` was never touched (branch protection would have blocked it anyway).
- Caught by: the human, on GitHub
- Fix: new rule in `.claude/CLAUDE.md`: ask before every push, naming the branch.

### Dashboard index declared in a way Alembic couldn't compare
- What the agent produced: `Index(..., postgresql_ops={"created_at": "DESC", "id": "DESC"})` on `leads`.
- Why it was wrong: `postgresql_ops` is for operator classes, not sort order. The database got the right index, but the model and migration disagreed, so every future autogenerate would drop and recreate it. All tests still passed.
- Caught by: reviewer subagent (ran `alembic check`)
- Fix: `Index(..., Lead.created_at.desc(), Lead.id.desc())`, regenerated migration, and `alembic check` added to `make test` so CI catches model/migration drift.

### Lead form had no `method`, so a pre-hydration submit would put PII in the URL
- What the agent produced: `<form onSubmit={...}>` in `frontend/app/lead-form.tsx`, relying on `preventDefault` for every submit.
- Why it was wrong: before React hydrates (slow or failed JS), the browser does a native submit, which defaults to `GET` and sends name and email in the query string, where they land in browser history and access logs.
- Caught by: reviewer subagent
- Fix: `method="post" encType="multipart/form-data"` on the form, in the W1 commit.

### File-picker button was unreadable in dark mode
- What the agent produced: `file:bg-zinc-100` on the resume input with no text color, so the "Choose file" label inherited the page foreground.
- Why it was wrong: in dark mode `globals.css` sets the foreground to near-white, so the button rendered as white text on a light-grey fill.
- Caught by: manual test
- Fix: explicit `file:text-zinc-900` (and `file:bg-zinc-200`), in the W1 commit.
