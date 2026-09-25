.PHONY: up down test test-fast lint migrate gen-client check-client

UV := uv run --quiet --python 3.12 --extra dev

# Copy the env template on first run only, then start all five services and wait for healthchecks.
# --renew-anon-volumes: the web container keeps node_modules in an anonymous volume, which would
# otherwise hold on to old packages after package.json changes.
up:
	@[ -f .env ] || cp .env.example .env
	docker compose up -d --build --wait --renew-anon-volumes

down:
	docker compose down

# `alembic check` fails if a model changed without a matching migration.
# Full suite, run inside the containers so local and CI behave the same. Needs `make up`.
# `next typegen` writes the route/layout types tsc needs; they're gitignored, so a fresh clone lacks them.
test: check-client
	docker compose exec -T api ruff check .
	docker compose exec -T api ruff format --check .
	docker compose exec -T api alembic check
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

migrate:
	docker compose exec -T api alembic upgrade head

# Regenerate the frontend's API types from FastAPI's OpenAPI spec. Never edit frontend/lib/api/ by hand.
gen-client:
	docker compose exec -T api python -m app.export_openapi > frontend/lib/api/openapi.json
	docker compose exec -T web npx openapi-typescript lib/api/openapi.json -o lib/api/schema.ts

# Fails if the committed client is out of date with the backend.
check-client: gen-client
	git diff --exit-code -- frontend/lib/api
