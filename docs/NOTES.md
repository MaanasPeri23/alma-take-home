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
