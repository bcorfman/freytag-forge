PACKAGE := storygame

.PHONY: install test lint format precommit run package

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

package:
	uv run python -m pip install --upgrade build
	uv run python -m build
