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
