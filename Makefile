.PHONY: up down test test-fast lint

UV := uv run --quiet --python 3.12 --extra dev

# Copy the env template on first run only, then start all five services and wait for healthchecks.
up:
	@[ -f .env ] || cp .env.example .env
	docker compose up -d --build --wait

down:
	docker compose down

# Full suite, run inside the containers so local and CI behave the same. Needs `make up`.
# `next typegen` writes the route/layout types tsc needs; they're gitignored, so a fresh clone lacks them.
test:
	docker compose exec -T api ruff check .
	docker compose exec -T api ruff format --check .
	docker compose exec -T api pytest -q
	docker compose exec -T web npm run lint
	docker compose exec -T web sh -c "npx next typegen && npx tsc --noEmit"

# Stop-hook suite: no Docker needed. Backend unit tests on the host via uv, plus frontend typecheck.
# Needs `npm ci` in frontend/ once.
test-fast:
	cd backend && $(UV) pytest -q -m "not integration"
	cd frontend && npx next typegen >/dev/null && npx tsc --noEmit

lint:
	cd backend && $(UV) ruff check . && $(UV) ruff format --check .
	cd frontend && npm run lint
