"""Render the dependency impact report for an addressed story record."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from storygame.story_package.impact_report import render_impact_report
from storygame.story_source.compiler import compile_source_tree
from storygame.story_source.lookup import story_value


def add_parser(commands: Any, add_global_options: Any) -> None:
    """Register the ``impact`` command with the story CLI parser."""

    parser = commands.add_parser("impact", help="render a record impact report")
    add_global_options(parser, defaults=False)
    parser.add_argument("address")


def _subject(address: str) -> str:
    kind, separator, rest = address.partition(":")
    if not kind or not separator or not rest:
        raise KeyError(address)
    identifier = rest.split(".", 1)[0].split("[", 1)[0]
    if not identifier:
        raise KeyError(address)
    return identifier


def _package_root(source_root: Path, package: Any) -> tuple[tempfile.TemporaryDirectory[str] | None, Path]:
    """Return a package root that the existing report renderer can load."""

    if (source_root / "ownership.yaml").is_file() and (source_root / "source").is_dir():
        return None, source_root

    temporary = tempfile.TemporaryDirectory(prefix="story-impact-")
    package_root = Path(temporary.name)
    shutil.copytree(source_root, package_root / "source")
    ownership = {
        "schema": 1,
        "catalog": "compiled",
        "scenes": {scene.metadata.scene_id: "compiled" for scene in package.scenes},
    }
    (package_root / "ownership.yaml").write_text(yaml.safe_dump(ownership, sort_keys=False), encoding="utf-8")
    return temporary, package_root


def run(args: Any, root: Path) -> int:
    """Validate an address and print its existing read-only impact report."""

    try:
        package = compile_source_tree(root)
        story_value(args.address, package=package)
        subject = _subject(args.address)
        temporary, report_root = _package_root(root, package)
        try:
            report = render_impact_report(report_root, subject)
        finally:
            if temporary is not None:
                temporary.cleanup()
    except (KeyError, ValueError):
        print(f"unknown address: {args.address}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps({"address": args.address, "subject": subject, "report": report}, ensure_ascii=False))
    else:
        print(report, end="")
    return 0
