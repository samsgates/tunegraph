.PHONY: install dev lint format typecheck test test-cov migrate run worker docker-up docker-down bootstrap

install:
	uv sync --all-extras

dev:
	uv sync --extra dev

lint:
	uv run ruff check .

format:
	uv run ruff format .
	uv run ruff check --fix .

typecheck:
	uv run mypy src/tunegraph/domain src/tunegraph/security src/tunegraph/services/contracts.py src/tunegraph/services/hashing.py src/tunegraph/schemas.py

test:
	uv run pytest

test-cov:
	uv run pytest --cov=tunegraph --cov-report=term-missing --cov-report=html

migrate:
	uv run alembic upgrade head

run:
	uv run uvicorn tunegraph.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	uv run tunegraph-worker

bootstrap:
	uv run tunegraph bootstrap

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v
