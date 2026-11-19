"""Round-trip YAML I/O for authored story source files."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


def make_yaml() -> YAML:
    """Create the configured round-trip YAML processor."""

    yaml = YAML(typ="rt")
    yaml.width = 10_000
    yaml.allow_unicode = True
    yaml.preserve_quotes = True
    return yaml


def load_document(path: Path) -> Any:
    """Load one authored YAML document while retaining its formatting metadata."""

    yaml = make_yaml()
    return yaml.load(path.read_text(encoding="utf-8"))


def dumps_document(document: Any) -> str:
    """Serialize one round-trip YAML document to UTF-8 text."""

    stream = StringIO()
    yaml = make_yaml()
    yaml.dump(document, stream)
    return stream.getvalue()


def dump_document(document: Any, path: Path) -> None:
    """Serialize one round-trip YAML document to a UTF-8 file."""

    path.write_text(dumps_document(document), encoding="utf-8")
