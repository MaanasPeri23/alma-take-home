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

### Resume download would have failed mid-stream instead of returning 404
- What the agent produced: `S3Storage.open` written as a generator, so `get_object` only ran when the first chunk was read.
- Why it was wrong: in B4 the download route streams the file. A missing object would have raised *after* the 200 headers were sent, giving the attorney a broken download instead of a clean 404. The round-trip test passed because it iterated inside `pytest.raises`.
- Caught by: reviewer subagent
- Fix: `open` fetches eagerly and raises `ObjectNotFound` on the call itself; the test now asserts that without iterating. Same review added S3 timeouts, `restart: unless-stopped` on the api, and bucket creation only on a real 404.

### A name with a hidden NUL character caused a 500, and the reviewer's fix was also wrong
- What the agent produced: a name rule that only blocked line breaks (`[^\r\n]`), so `Ada\x00` passed validation. Postgres rejects NUL in text, so the prospect got a 500 instead of a 422 on the field.
- Why it was wrong: validation has to match what the database accepts. The reviewer caught it and suggested `^[^\x00-\x1f\x7f]*\S[^\x00-\x1f\x7f]*$`. That suggestion still let NUL through: the middle `\S` ("any non-space") matches NUL itself.
- Caught by: reviewer subagent (the original bug), then a failing test (the reviewer's fix). I added a `nul-in-name` case before applying the suggested pattern, and it failed.
- Fix: `[^\s\x00-\x1f\x7f]` for the required visible character. The same review turned on `hide_parameters=True` on the engine, because a failed insert's error message would otherwise log the prospect's name and email.

### Security tests that would have passed with the security broken
- What the agent produced: "bad signature" and "expired" token tests that signed tokens for a random UUID.
- Why it was wrong: no attorney has that id, so the request got a 401 from the account lookup, whether or not the signature or expiry check worked. Removing either check would still have left the tests green. The same review found that a token without `exp` never expired, and that a password over 72 bytes crashed login with a 500 (bcrypt 5 raises).
- Caught by: reviewer subagent
- Fix: forged tokens are now built for a real attorney, and each test first proves the valid token works. Added other-secret, `alg: none` and no-`exp` cases, and made `exp`/`iat`/`sub` required. Checked by removing the `require` option: exactly the no-`exp` test failed. Passwords over 72 bytes are now a 401.

### Dashboard had a dead end past the last page
- What the agent produced: when a page had no rows but `total > 0` (a hand-edited `?offset=500`, or leads moving out of a filter while on its last page), the list showed "No leads on this page." and hid the Previous/Next controls.
- Why it was wrong: the only way out was the filter links, which isn't obvious. It also happens in normal use: mark the last Pending lead on a page as reached out, go back, and the Pending view is empty.
- Caught by: reviewer subagent
- Fix: a "Back to first page" link in that state, in the W3 commit. The same review added a guard so a late re-fetch after a 409 can't overwrite a different lead.

### E2E test would have timed out on a clean stack
- What the agent produced: a Playwright config with the default timeouts (30 s per test, 5 s per `expect`), verified only against a warm dev server.
- Why it was wrong: the `web` container runs `next dev`, which compiles each route on its first visit. The design's "Full E2E" check is `make e2e` from a clean stack, which is exactly the cold case, so the first navigation or the first-row check could exceed 5 s. The same review found that `make e2e` hardcoded the login instead of reading `SEED_ATTORNEY_*` from `.env`, and that the attorney-email check didn't look at the recipient.
- Caught by: reviewer subagent
- Fix: 90 s test / 15 s expect timeouts, credentials passed from `.env` by the Makefile, attorney email matched by `to:` and exact subject, in the W4 commit.
