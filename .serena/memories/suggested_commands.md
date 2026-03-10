Setup: `uv sync --group dev` or `make install`.
Run tests: `uv run python -m pytest -q` or `make test`.
Lint: `uv run python -m ruff check .` or `make lint`.
Format: `uv run python -m ruff format` or `make format`.
Run web app locally: `uv run uvicorn storygame.web:app --reload` or `make run`.
Run CLI: `uv run python -m storygame --seed 123`.
Useful shell tools on Linux: `git`, `ls`, `find`, `rg`, `sed`, `cat`.