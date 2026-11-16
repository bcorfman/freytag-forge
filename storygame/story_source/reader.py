"""Read declarative story YAML while retaining source locations and duplicate keys."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .diagnostics import Diagnostic

PathPart = str | int


@dataclass(frozen=True)
class _DuplicateKey:
    path: tuple[PathPart, ...]
    key: str
    first_line: int
    repeated_line: int


class _TrackingLoader(yaml.SafeLoader):
    """SafeLoader variant that converts nodes while recording source positions."""

    def __init__(self, stream: Any) -> None:
        super().__init__(stream)
        self.lines: dict[tuple[PathPart, ...], int] = {}
        self.duplicates: list[_DuplicateKey] = []

    def get_single_data(self) -> object:
        node = self.get_single_node()
        if node is None:
            return None
        return self._convert(node, ())

    def _convert(self, node: yaml.Node, path: tuple[PathPart, ...]) -> object:
        self.lines.setdefault(path, node.start_mark.line + 1)
        if isinstance(node, yaml.MappingNode):
            result: dict[Any, object] = {}
            key_lines: dict[Any, int] = {}
            for key_node, value_node in node.value:
                key = self._convert(key_node, path)
                try:
                    repeated = key in result
                except TypeError:
                    repeated = False
                key_line = key_node.start_mark.line + 1
                value_path = path + (key,) if isinstance(key, (str, int)) else path
                if repeated:
                    self.duplicates.append(
                        _DuplicateKey(
                            path=path,
                            key=str(key),
                            first_line=key_lines[key],
                            repeated_line=key_line,
                        )
                    )
                    continue
                try:
                    key_lines[key] = key_line
                    self.lines.setdefault(value_path, key_line)
                    result[key] = self._convert(value_node, value_path)
                except TypeError:
                    self.lines.setdefault(value_path, key_line)
                    result[str(key)] = self._convert(value_node, value_path)
            return result
        if isinstance(node, yaml.SequenceNode):
            result: list[object] = []
            for index, item_node in enumerate(node.value):
                item_path = path + (index,)
                self.lines[item_path] = item_node.start_mark.line + 1
                result.append(self._convert(item_node, item_path))
            return result
        return self.construct_object(node, deep=True)


@dataclass
class SourceTree:
    """Parsed source files and their line locations."""

    root: Path
    files: dict[str, object]
    _lines: dict[str, dict[tuple[PathPart, ...], int]] = field(default_factory=dict, repr=False)

    def line_of(self, file: str, path: tuple[PathPart, ...]) -> int | None:
        """Return the one-based source line for a parsed path, if known."""

        return self._lines.get(file, {}).get(path)


def _path_address(path: tuple[PathPart, ...]) -> str:
    if not path:
        return "root"
    address = ""
    for part in path:
        if isinstance(part, int):
            address += f"[{part}]"
        elif not address:
            address = part
        else:
            address += f".{part}"
    return address


def _syntax_diagnostic(file: str, error: Exception) -> Diagnostic:
    return Diagnostic(
        name="L1.syntax",
        file=file,
        address="root",
        field="syntax",
        message=str(error),
    )


def read_source_tree(root: Path) -> tuple[SourceTree, list[Diagnostic]]:
    """Read all YAML files below ``root`` and return parsed data plus reader diagnostics."""

    files: dict[str, object] = {}
    lines: dict[str, dict[tuple[PathPart, ...], int]] = {}
    diagnostics: list[Diagnostic] = []
    for path in sorted(root.rglob("*.yaml")):
        relative = path.relative_to(root).as_posix()
        loader: _TrackingLoader | None = None
        try:
            with path.open(encoding="utf-8") as stream:
                loader = _TrackingLoader(stream)
                files[relative] = loader.get_single_data()
            lines[relative] = loader.lines
            diagnostics.extend(
                Diagnostic(
                    name="L1.duplicate_key",
                    file=relative,
                    address=_path_address(duplicate.path),
                    field=duplicate.key,
                    message=(
                        f"duplicate key {duplicate.key!r}; first occurrence at line "
                        f"{duplicate.first_line}, repeated at line {duplicate.repeated_line}"
                    ),
                )
                for duplicate in loader.duplicates
            )
        except Exception as error:
            files[relative] = None
            if loader is not None:
                lines[relative] = loader.lines
            diagnostics.append(_syntax_diagnostic(relative, error))
        finally:
            if loader is not None:
                loader.dispose()
    return SourceTree(root=root, files=files, _lines=lines), diagnostics
