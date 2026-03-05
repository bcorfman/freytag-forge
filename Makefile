PACKAGE := storygame

.PHONY: install test lint run package

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

run:
	uv run python -m storygame

package:
	uv run python -m pip install --upgrade build
	uv run python -m build
