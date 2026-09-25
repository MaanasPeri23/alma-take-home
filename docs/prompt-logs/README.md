# Prompt logs

Excerpts from the Claude Code sessions, trimmed to the moments that shaped the build. The full
sessions ran in two worktrees: `alma-take-home` (foundation + backend) and `alma-take-home-web`
(frontend). Nothing here contains secrets; the only credentials in the project are local dev
defaults from `.env.example`.

| File | What it shows |
| --- | --- |
| [01-kickoff-and-guardrails.md](01-kickoff-and-guardrails.md) | Starting from the handoff; the agent checking the environment before writing code, and fixing the handoff's own hook scripts |
| [02-correcting-the-agent.md](02-correcting-the-agent.md) | I caught an unannounced push; the rule that came out of it |
| [03-reviewer-and-a-failing-test.md](03-reviewer-and-a-failing-test.md) | The reviewer finding a bug, its fix being wrong, and a test catching that |
| [04-a-design-decision.md](04-a-design-decision.md) | Choosing how logout behaves, with the tradeoffs laid out before deciding |
