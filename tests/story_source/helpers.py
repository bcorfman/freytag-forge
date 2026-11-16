"""Helpers for copying and patching declarative story-source fixtures."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import yaml


class DuplicateKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_mapping(loader: DuplicateKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.constructor.ConstructorError(
                None,
                None,
                f"duplicate key {key!r}",
                key_node.start_mark,
            )
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


DuplicateKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)

DELETE = object()
_SEGMENT = re.compile(r"^(?P<key>[^.\[\]]+)(?:\[(?P<selector>[^\]]+)\])?$")


def _load(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return yaml.load(stream, Loader=DuplicateKeyLoader)


def copy_fixture(name: str, tmp_path: Path) -> Path:
    """Copy a named story-source fixture into ``tmp_path`` and return its root."""

    source = Path(__file__).parents[1] / "fixtures" / "story_source" / name
    destination = tmp_path / name
    shutil.copytree(source, destination)
    return destination


def _parse(address: str) -> list[tuple[str, str | None]]:
    if not address:
        raise KeyError(address)
    segments: list[tuple[str, str | None]] = []
    for raw in address.split("."):
        match = _SEGMENT.fullmatch(raw)
        if match is None:
            raise KeyError(address)
        segments.append((match["key"], match["selector"]))
    return segments


def _select(value: object, selector: str, address: str) -> tuple[list[object], int]:
    if not isinstance(value, list):
        raise KeyError(address)
    if selector.isdigit():
        index = int(selector)
        if index >= len(value):
            raise KeyError(address)
        return value, index
    for index, item in enumerate(value):
        if isinstance(item, dict) and (item.get("id") == selector or item.get("claim_id") == selector):
            return value, index
    raise KeyError(address)


def patch_source(root: Path, file: str, address: str, value: object = DELETE) -> None:
    """Patch one YAML value using mapping keys, list IDs, or list indexes."""

    path = root / file
    if not path.is_file():
        raise KeyError(address)
    document = _load(path)
    segments = _parse(address)
    current = document
    for position, (key, selector) in enumerate(segments):
        last = position == len(segments) - 1
        if not isinstance(current, dict) or key not in current:
            if last and isinstance(current, dict) and value is not DELETE:
                current[key] = value
                return _dump(path, document)
            raise KeyError(address)
        if selector is None:
            if last:
                if value is DELETE:
                    del current[key]
                else:
                    current[key] = value
                return _dump(path, document)
            current = current[key]
            continue
        selected, index = _select(current[key], selector, address)
        if last:
            if value is DELETE:
                selected.pop(index)
            else:
                selected[index] = value
            return _dump(path, document)
        current = selected[index]
    raise KeyError(address)


def _dump(path: Path, document: object) -> None:
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(document, stream, sort_keys=False, width=10_000, allow_unicode=True)


def load_tree(root: Path) -> dict[str, object]:
    """Load every YAML file below ``root``, rejecting duplicate keys."""

    return {path.relative_to(root).as_posix(): _load(path) for path in sorted(root.rglob("*.yaml"))}
