"""Round-trip YAML I/O for authored story source files."""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

_SEQUENCE = re.compile(r"^(?P<indent> *)- ")
_FLOW_NULL = re.compile(r"^(?P<prefix>.*,\s+)(?P<key>[^,:{}\n]+)\}$")


def make_yaml() -> YAML:
    """Create the configured round-trip YAML processor."""

    yaml = YAML(typ="rt")
    yaml.width = 10_000
    yaml.allow_unicode = True
    yaml.preserve_quotes = True
    return yaml


def _configure_source_style(yaml: YAML, text: str) -> tuple[int, int, int] | None:
    """Preserve the authored block-sequence indentation convention."""

    previous = ""
    for line in text.splitlines():
        match = _SEQUENCE.match(line)
        if match and previous.rstrip().endswith(":") and not previous.lstrip().startswith("-"):
            previous_indent = len(previous) - len(previous.lstrip(" "))
            sequence_indent = len(match["indent"])
            if sequence_indent > previous_indent:
                style = (2, 4, 2)
                yaml.indent(mapping=style[0], sequence=style[1], offset=style[2])
                return style
        if line.strip():
            previous = line
    return None


def load_document(path: Path) -> Any:
    """Load one authored YAML document while retaining its formatting metadata."""

    text = path.read_text(encoding="utf-8")
    yaml = make_yaml()
    style = _configure_source_style(yaml, text)
    document = yaml.load(text)
    if document is not None and hasattr(document, "__dict__"):
        document._yamlio_style = style
        document._yamlio_source_text = text
    return document


def _restore_flow_nulls(document: Any, text: str) -> str:
    """Retain shorthand flow-map entries that ruamel expands with null."""

    source = getattr(document, "_yamlio_source_text", None)
    if source is None:
        return text
    replacements: dict[str, str] = {}
    for line in source.splitlines(keepends=True):
        match = _FLOW_NULL.match(line.rstrip("\r\n"))
        if match is None:
            continue
        old = line.rstrip("\r\n")
        new = f"{match['prefix']}{match['key']}: null}}"
        replacements[new] = old
    lines = []
    for line in text.splitlines(keepends=True):
        bare = line.rstrip("\r\n")
        lines.append(replacements.get(bare, bare) + line[len(bare) :])
    return "".join(lines)


def dumps_document(document: Any) -> str:
    """Serialize one round-trip YAML document to UTF-8 text."""

    stream = StringIO()
    yaml = make_yaml()
    style = getattr(document, "_yamlio_style", None)
    if style is not None:
        yaml.indent(mapping=style[0], sequence=style[1], offset=style[2])
    yaml.dump(document, stream)
    return _restore_flow_nulls(document, stream.getvalue())


def dump_document(document: Any, path: Path) -> None:
    """Serialize one round-trip YAML document to a UTF-8 file."""

    path.write_text(dumps_document(document), encoding="utf-8")
