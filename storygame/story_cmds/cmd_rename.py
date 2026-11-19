"""Rename an authored story identifier and all exact YAML references."""

from __future__ import annotations

import difflib
import json
import re
import sys
from pathlib import Path
from typing import Any

from storygame.story_source import check_source_tree
from storygame.story_source.compiler import compile_source_tree
from storygame.story_source.diagnostics import SourceError
from storygame.story_source.yamlio import dumps_document, load_document

_SNAKE_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_OUTLINE_ID = re.compile(r"^[1-9][A-Z]\.[0-9]+$")
_SCENE_ID = re.compile(r"^[1-9][A-Z]$")
_STORYLET_ID = re.compile(r"^SL-[1-9][A-Z]-[A-Z]$")
_REALIZATION_ID = re.compile(r"^SL-[1-9][A-Z]-[A-Z]-R[0-9]+$")


def add_parser(commands: Any, add_global_options: Any) -> None:
    parser = commands.add_parser("rename", help="rename a story identifier")
    add_global_options(parser, defaults=False)
    parser.add_argument("address")
    parser.add_argument("new_id")
    parser.add_argument("--retire")


def _valid_id(kind: str, identifier: str) -> bool:
    if kind == "outline":
        return bool(_OUTLINE_ID.fullmatch(identifier))
    if kind == "scene":
        return bool(_SCENE_ID.fullmatch(identifier))
    if kind == "storylet":
        return bool(_STORYLET_ID.fullmatch(identifier))
    if kind == "realization":
        return bool(_REALIZATION_ID.fullmatch(identifier))
    return bool(_SNAKE_ID.fullmatch(identifier))


def _definition_kind(parent: str, key: str, value: Any) -> str | None:
    if key == "claim_id" or key == "claim":
        return "claim"
    if key == "storylet_id":
        return "storylet"
    if key == "realization_id":
        return "realization"
    if key == "id":
        return {
            "beats": "beat",
            "outcome": "outcome",
            "outcomes": "outcome",
            "reveals": "reveal",
            "parts": "part",
            "outline": "outline",
        }.get(parent)
    return None


def _collect_ids(value: Any, parent: str = "", ids: dict[str, set[str]] | None = None) -> dict[str, set[str]]:
    if ids is None:
        ids = {}
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            kind = _definition_kind(parent, key_text, child)
            if kind and isinstance(child, str):
                ids.setdefault(kind, set()).add(child)
            if parent in {
                "facts",
                "claims",
                "deliveries",
                "characters",
                "groups",
                "items",
                "places",
                "kinds",
                "props",
                "outcomes",
                "outline",
            } and isinstance(key, str):
                kind = {
                    "facts": "fact",
                    "claims": "claim",
                    "deliveries": "delivery",
                    "characters": "entity",
                    "groups": "entity",
                    "items": "entity",
                    "places": "entity",
                    "kinds": "kind",
                    "props": "prop",
                    "outcomes": "outcome",
                    "outline": "outline",
                }.get(parent)
                if kind:
                    ids.setdefault(kind, set()).add(key)
            _collect_ids(child, key_text, ids)
    elif isinstance(value, list):
        for child in value:
            if parent == "unplaced_facts" and isinstance(child, str):
                ids.setdefault("fact", set()).add(child)
            _collect_ids(child, parent, ids)
    return ids


def _manifest_ids() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    project_root = Path(__file__).resolve().parents[2]
    if not (project_root / "tests/fixtures/save_identity").is_dir():
        project_root = Path.cwd()
    candidates = sorted((project_root / "tests/fixtures/save_identity").glob("*.yaml"))
    for path in candidates:
        try:
            document = load_document(path)
        except Exception:
            continue
        if isinstance(document, dict) and isinstance(document.get("ids"), dict):
            for kind, values in document["ids"].items():
                if isinstance(values, list):
                    result.setdefault(str(kind), set()).update(str(item) for item in values)
    return result


def _mentioned(identifier: str) -> tuple[list[str], list[str]]:
    tests: list[str] = []
    readers: list[str] = []
    project_root = Path(__file__).resolve().parents[2]
    if not (project_root / "tests").is_dir():
        project_root = Path.cwd()
    roots = (
        (project_root / "tests", tests, (project_root / "tests/fixtures/save_identity",)),
        (project_root / "scripts", readers, ()),
        (project_root / "docs", readers, ()),
        (project_root / "storygame", readers, ()),
    )
    for root, output, excluded in roots:
        if not root.is_dir():
            continue
        for path in sorted(item for item in root.rglob("*") if item.is_file()):
            if any(path.is_relative_to(item) for item in excluded):
                continue
            try:
                if identifier in path.read_text(encoding="utf-8"):
                    output.append(path.relative_to(project_root).as_posix())
            except (OSError, UnicodeDecodeError):
                continue
    return tests, readers


def _replace(value: Any, old: str, new: str) -> Any:
    if isinstance(value, dict):
        for key in list(value):
            child = value.pop(key)
            replacement_key = new if str(key) == old else key
            value[replacement_key] = _replace(child, old, new)
        return value
    if isinstance(value, list):
        for index, child in enumerate(value):
            value[index] = _replace(child, old, new)
        return value
    return new if value == old else value


def _diagnostics(root: Path) -> list[Any]:
    problems = list(check_source_tree(root))
    try:
        compile_source_tree(root)
    except SourceError as error:
        problems.append(error)
    return problems


def _print_problems(problems: list[Any]) -> None:
    for problem in problems:
        print(str(problem), file=sys.stderr)


def run(args: Any, root: Path) -> int:
    kind, separator, old = args.address.partition(":")
    if not separator or not kind or not old or not _valid_id(kind, args.new_id):
        print(f"invalid rename address or id: {args.address} {args.new_id}", file=sys.stderr)
        return 2
    new = args.new_id
    paths = sorted(root.rglob("*.yaml"))
    documents: dict[Path, Any] = {}
    original: dict[Path, bytes] = {}
    all_ids: dict[str, set[str]] = {}
    for path in paths:
        original[path] = path.read_bytes()
        documents[path] = load_document(path)
        found = _collect_ids(documents[path])
        for found_kind, values in found.items():
            all_ids.setdefault(found_kind, set()).update(values)
    manifest = _manifest_ids()
    for frozen_kind, values in manifest.items():
        all_ids.setdefault(frozen_kind, set()).update(values)
    frozen = old in manifest.get(kind, set()) or (
        kind in {"claim", "storylet", "beat"} and old in all_ids.get(kind, set())
    )
    defined_kinds = {found_kind for found_kind, values in all_ids.items() if old in values}
    if kind not in defined_kinds:
        print(f"unknown address: {args.address}", file=sys.stderr)
        return 2
    other_kinds = sorted(defined_kinds - {kind})
    if other_kinds:
        print(f"ambiguous id {old!r}; also defined as: {', '.join(other_kinds)}", file=sys.stderr)
        return 1
    if any(new in values for values in all_ids.values()):
        print(f"new id already exists: {new}", file=sys.stderr)
        return 1
    if frozen and args.retire is None:
        print(f"frozen id requires --retire: {old}", file=sys.stderr)
        return 1
    if args.retire is not None and not frozen:
        print(f"--retire is only valid for a frozen id: {old}", file=sys.stderr)
        return 1

    rendered_documents: dict[Path, str] = {}
    try:
        for path, document in documents.items():
            updated = _replace(document, old, new)
            if args.retire is not None and path == root / "story.yaml":
                retired = updated.setdefault("retired_ids", {})
                retired.setdefault(kind, {})[old] = args.retire
            rendered_documents[path] = dumps_document(updated)
    except Exception as error:
        print(f"rename failed before writing: {error}", file=sys.stderr)
        return 1

    changed: list[str] = []
    diffs: list[str] = []
    try:
        for path, rendered in rendered_documents.items():
            before = original[path].decode("utf-8")
            if rendered == before:
                continue
            path.write_text(rendered, encoding="utf-8")
            relative = path.relative_to(root).as_posix()
            changed.append(relative)
            diffs.extend(
                difflib.unified_diff(
                    before.splitlines(keepends=True),
                    rendered.splitlines(keepends=True),
                    fromfile=relative,
                    tofile=relative,
                )
            )
    except Exception as error:
        for path, data in original.items():
            path.write_bytes(data)
        print(f"rename failed while writing: {error}", file=sys.stderr)
        return 1
    problems = _diagnostics(root)
    if problems:
        for path, data in original.items():
            path.write_bytes(data)
        _print_problems(problems)
        return 1
    tests, readers = _mentioned(old)
    diff = "".join(diffs)
    if args.json:
        print(json.dumps({"changed": changed, "diff": diff, "tests": tests, "readers": readers}, ensure_ascii=False))
    else:
        print(diff, end="")
        print("tests: " + (", ".join(tests) if tests else "none"))
        print("readers: " + (", ".join(readers) if readers else "none"))
    return 0
