.PHONY: lint format fix check

lint:
	uv run ruff check .

format:
	uv run ruff format --check .

fix:
	uv run ruff check --fix . && uv run ruff format .

check: lint format
	uv run pytest tests/ -q
