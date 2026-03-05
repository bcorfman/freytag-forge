PACKAGE := freytag-forge
PACKAGE_DIR := src/${PACKAGE}
SHELL := env PYTHON_VERSION=3.12 /bin/bash
.SILENT: install devinstall tools test run lint format
PYTHON_VERSION ?= 3.12

setup:
	curl -LsSf https://astral.sh/uv/install.sh | sh

install:
	uv python pin $(PYTHON_VERSION)
	uv sync --frozen --no-dev

devinstall:
	uv python pin $(PYTHON_VERSION)
	uv add pytest pytest-cov --dev
	uv sync --all-extras --dev

tools:
	uv tool install ruff --force
	uv tool install ipython --force

test:
	uv run pytest

run: 
	uv run python main.py

lint:
	uv tool run ruff check -q

format:
	uv tool run ruff format

all: devinstall tools lint format test
