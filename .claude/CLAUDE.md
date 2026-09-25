# Leads App — agent rules

## Stack (fixed)
FastAPI + SQLAlchemy 2.x + Alembic + Pydantic v2 (backend/), Next.js App Router + TypeScript (frontend/),
Postgres, MinIO, Mailpit. All run via docker-compose. Do not add frameworks.

## Source of truth
docs/DESIGN.md defines the API, data model, and decisions. Follow it. If something in it seems wrong, stop and ask.

## Backend layering
routers/ = HTTP only. services/ = business logic. storage/ and email/ = interfaces + implementations.
Routers never import boto3/smtplib directly. Missing rows are 404, never 500.
Lead state transitions go through the ALLOWED map in lead_service.py and always write a lead_state_events row.

## Frontend
lib/api/ is generated from FastAPI's OpenAPI (`make gen-client`). Never hand-edit it.
Browser calls go to /api/* (proxied by Next.js rewrites). No CORS config.
Next.js is version 16 and differs from older docs (e.g. middleware.ts is now proxy.ts). Check node_modules/next/dist/docs/ before writing Next.js code.

## Scope
One plan item per request. No unrelated refactors. Do not build rate limiting, CAPTCHA,
or an outbox worker — those are documented future work.

## Git rules
- Never push to main. Never merge a PR (no `gh pr merge`, no merging into main). The human merges.
- Work only on the feature branch you were given. Commit there, one commit per plan item.
- Ask the human before every `git push`, naming the branch. Never push as part of another command.
- You may push your feature branch (after asking), open a PR with `gh pr create`, and resolve merge conflicts on your branch.
- Never force-push.
- Conventional commit messages. Every commit ends with the trailer `Agent: claude-code`.

## Worktrees
Backend lane: this folder (`feat/backend`). Frontend lane: `../alma-take-home-web` (`feat/frontend`).
Run only one Docker stack, from the backend folder.

## Before every commit
1. `make test` passes.
2. Run the reviewer subagent on the diff and fix blockers.
3. Print the manual check for this plan item (from docs/DESIGN.md) and wait for me to confirm it passed.
4. If you or I found an agent mistake, append it to docs/NOTES.md under "Agent catches".

## Commands
make up | make test | make test-fast | make e2e | make lint | make seed | make gen-client
