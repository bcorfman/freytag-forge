"""Phase-0 offline source selector for future causal compilation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from storygame.authoring.compiler import CompilationError
from storygame.authoring.sources import StorySourceLoader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-blueprint")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--outline-id")
    selection.add_argument("--story", type=Path)
    parser.add_argument("--inventory", type=Path, default=Path("data/story_outlines.yaml"))
    parser.add_argument("--profile-root", type=Path, default=Path("data/genre_profiles"))
    return parser


def select_source(args: argparse.Namespace) -> dict[str, object]:
    loader = StorySourceLoader(args.inventory, args.profile_root)
    source = loader.select_outline(args.outline_id) if args.outline_id else loader.load_brief(args.story)
    return source.model_dump(mode="json")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        print(json.dumps(select_source(args), sort_keys=True))
    except CompilationError as exc:
        raise SystemExit(str(exc)) from exc
    return 0
