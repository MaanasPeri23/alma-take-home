# Correcting the agent

After F2, the agent committed and ran `git push` in the same command, reporting it only as
"pushed". The rules allowed pushing feature branches, but I found out from GitHub.

**Me:**
> Dude. you just made a push without a PR at all. this is a really bad red flag. despite the
> guardrails explicitly written why did you do that, did u not see it? you were supposed to make a
> PR and I merge it.....

**Agent (excerpt):**
> Nothing reached `main`. [...] What I did wrong was not telling you clearly. I ran the push
> inside a commit command and reported it with the word "pushed", with no explanation. From your
> side it looked like work going out without review.

It checked `origin/main` to prove nothing had landed, then asked how I wanted PRs handled. I chose
**"Ask me before every push"** and a PR after F2 instead of after F3.

**Outcome:**
- New rule in `.claude/CLAUDE.md`: *"Ask the human before every `git push`, naming the branch.
  Never push as part of another command."*
- The rule was saved to the agent's memory, and the incident logged in `docs/NOTES.md`.
- Every push after that was preceded by a question.
