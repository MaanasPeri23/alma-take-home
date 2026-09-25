#!/usr/bin/env bash
# Runs after every file edit. Exit code 2 sends the error back to Claude to fix.
file=$(python3 -c 'import sys,json; print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))')
cd "$CLAUDE_PROJECT_DIR" || exit 0
case "$file" in
  *.py)
    # Guard: backend/ doesn't exist until F2, and ruff may not be installed yet.
    [ -d backend ] || exit 0
    command -v ruff >/dev/null || { echo "lint.sh: ruff not installed, skipping (uv tool install ruff)" >&2; exit 0; }
    out=$(cd backend && ruff check --fix "$file" 2>&1 && ruff format "$file" 2>&1) || { echo "$out" >&2; exit 2; } ;;
  *.ts|*.tsx)
    # Guard: frontend/ and its node_modules don't exist until F2.
    [ -d frontend/node_modules ] || exit 0
    out=$(cd frontend && npx eslint --fix "$file" 2>&1) || { echo "$out" >&2; exit 2; } ;;
esac
exit 0
