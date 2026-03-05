PACKAGE := storygame

.PHONY: install test lint format run package

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check -q --fix

format:
	uv run ruff format

run:
	uv run python -m storygame

package:
	uv run python -m pip install --upgrade build
	uv run python -m build
