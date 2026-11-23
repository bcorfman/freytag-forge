"""Resolve the repository's default story package root."""

from __future__ import annotations

from pathlib import Path


def default_package_root() -> Path:
    """Return the default story package directory shipped with the repository."""

    return Path(__file__).resolve().parents[2] / "data" / "stories" / "continuity-initiative"
