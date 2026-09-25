# Kickoff and guardrails

**Me:**
> read this handoff, this is the bases for this project so far

The agent read the 23-page handoff and checked the repo against it before writing anything. It
found that the GitHub review workflows the handoff called "installed" weren't in my clone yet.

**Me:**
> The GitHub app PR is merged on GitHub; my local clone just hasn't pulled it. Run git pull on
> main and confirm both workflow files are there. Then check gh secret list for ANTHROPIC_API_KEY
> and gh api repos/{owner}/{repo}/branches/main/protection for branch protection, and report
> what's missing.

**Agent (summary):** the workflows use `CLAUDE_CODE_OAUTH_TOKEN`, so no API key is needed; branch
protection is blocked while the repo is private on a free plan; SSH pushes fail, so switch to
HTTPS.

Then, planning F1, it flagged a problem in the handoff itself. The handoff said to copy the hooks
verbatim, and the agent's plan said:

> **`test.sh`:** runs `make test-fast`, but no Makefile exists until F2 → the Stop hook would
> block every stop during F1/early F2. Add `[ -f Makefile ] || exit 0` before the make call.
> **`lint.sh`:** `cd backend` / `cd frontend` fail until those dirs exist, and ruff isn't
> installed → exit 2 on every edit.

Both guards went in, and this became the first entry in `docs/NOTES.md`.
