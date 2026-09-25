#!/usr/bin/env bash
# Runs when Claude tries to stop. Exit code 2 blocks it and shows the failures.
input=$(cat)
# Prevent an infinite loop: if Claude is already continuing because of this hook, let it stop.
if echo "$input" | grep -q '"stop_hook_active": *true'; then exit 0; fi
cd "$CLAUDE_PROJECT_DIR" || exit 0
# Guard: the Makefile doesn't exist until F2.
[ -f Makefile ] || exit 0
if ! make test-fast > /tmp/claude-test.log 2>&1; then
  echo "Tests failing. Fix before finishing:" >&2
  tail -40 /tmp/claude-test.log >&2
  exit 2
fi
exit 0
