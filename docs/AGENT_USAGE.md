# How I used coding agents

## Tools

Claude Code for everything, set up before any feature work:
- **`.claude/CLAUDE.md`:** rules the agent reads every session (layering, scope, git rules).
- **Hooks:** lint and format every file the agent edits, and run the fast tests before it can say it's done.
- **A read-only reviewer subagent** that critiques each diff before commit.
- **Plan mode** for every commit.
- **Two git worktrees,** so a backend session and a frontend session could build in parallel against a contract merged first.

On GitHub: the Claude PR review action on every PR, and CI (`make up` + `make test` in Docker) as a required check.

## What I delegated vs. wrote myself

**Delegated:** the code (models, routes, services, tests, UI), the generated client, and first drafts of these docs.

**Kept for myself:**
- **The decisions:** stack, auth model, "save the lead before emailing", the state machine.
- **The guardrails:** CLAUDE.md, the hooks, the reviewer checklist, branch protection.
- **The approvals:** every plan, every manual check before a commit, and every merge.

**Decided mid-build, when the agent brought me the tradeoffs:** worktrees versus subagents for the frontend, and making logout public.

**Why:** the agent is fast at code that follows a spec, and weakest at deciding what the spec should be and at noticing when a check proves nothing.

## How I kept it honest

- The hooks run whether or not the agent remembers.
- The reviewer ran on every commit and found a real issue in almost every one.
- CI runs on every PR, and `main` only accepts green PRs.
- Every commit carries an `Agent:` trailer. [NOTES.md](NOTES.md) logs each mistake as it happened.

## One thing the agent got wrong

Names on the public form were only checked for line breaks, so a name containing a NUL character passed validation. Postgres rejects NUL, and the prospect got a 500 instead of a field error. The reviewer subagent caught it, but its suggested fix, `^[^\x00-\x1f\x7f]*\S[^\x00-\x1f\x7f]*$`, was also wrong: the middle `\S` matches NUL itself.

I had the agent add a NUL test case *before* applying the suggestion. The test failed and exposed the second bug. The fix, `[^\s\x00-\x1f\x7f]`, landed in B2 (`a13fbe9`).

A close second: two token-security tests signed tokens for a random user, so the account lookup rejected them, and they would have stayed green even with signature checking deleted. They now use a real attorney. I also proved the fix by removing the expiry check and watching exactly one test fail (B3, `a98004c`).

The lesson both times: a passing test only counts if it could have failed.
