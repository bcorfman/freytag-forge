"""Format authored story-source YAML files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from storygame.story_source.yamlio import dumps_document, load_document


def add_parser(commands: Any, add_global_options: Any) -> None:
    """Register the ``fmt`` command with the story CLI parser."""

    parser = commands.add_parser("fmt", help="format authored YAML source")
    add_global_options(parser, defaults=False)
    parser.add_argument("scene", nargs="?")
    parser.add_argument("--check", action="store_true")


def _paths(root: Path, scene: str | None) -> list[Path]:
    if scene is None:
        return sorted(root.rglob("*.yaml"))
    candidates = [root / "scenes" / f"{scene}.yaml", root / "scenes" / f"{scene}.match.yaml"]
    return [path for path in candidates if path.is_file()]


def _values_equal(old_text: str, new_text: str) -> bool:
    return yaml.safe_load(old_text) == yaml.safe_load(new_text)


def _format_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def format_source_tree(root: Path, *, check: bool) -> tuple[list[str], list[str]]:
    """Format every YAML file below ``root`` and report changed and refused paths."""

    changed: list[str] = []
    refused: list[str] = []
    for path in _paths(root, None):
        old_text = path.read_text(encoding="utf-8")
        new_text = dumps_document(load_document(path))
        if old_text == new_text:
            continue
        relative = _format_path(path, root)
        if not _values_equal(old_text, new_text):
            refused.append(relative)
            continue
        changed.append(relative)
        if not check:
            path.write_text(new_text, encoding="utf-8")
    return changed, refused


def run(args: Any, root: Path) -> int:
    """Format selected source files, or report files that need formatting."""

    paths = _paths(root, args.scene)
    if args.scene is not None and not paths:
        print(f"unknown scene id: {args.scene}", file=sys.stderr)
        return 2

    if args.scene is None:
        changed, refused = format_source_tree(root, check=args.check)
        for path in refused:
            print(f"{path}: value changed, not written", file=sys.stderr)
        safety_failed = bool(refused)
    else:
        changed = []
        safety_failed = False
        for path in paths:
            old_text = path.read_text(encoding="utf-8")
            new_text = dumps_document(load_document(path))
            if old_text == new_text:
                continue
            relative = _format_path(path, root)
            if not _values_equal(old_text, new_text):
                print(f"{relative}: value changed, not written", file=sys.stderr)
                safety_failed = True
                continue
            changed.append(relative)
            if not args.check:
                path.write_text(new_text, encoding="utf-8")

    if args.json:
        print(json.dumps({"checked": len(paths), "changed": changed}, ensure_ascii=False))
    elif args.check:
        for path in changed:
            print(f"would reformat {path}")
    else:
        for path in changed:
            print(f"reformatted {path}")
    return 1 if safety_failed or (args.check and changed) else 0
