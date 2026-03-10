PACKAGE := storygame

.PHONY: install test lint format precommit run run-cli package

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check -q --fix

format:
	uv run ruff format

precommit:
	uv sync --group dev
	uv run pre-commit install

run:
	uv run uvicorn storygame.web:app --reload

run-cli:
	uv run uvicorn storygame.web:app --reload --host 127.0.0.1 --port 8000

package:
	uv run python -m pip install --upgrade build
	uv run python -m build
