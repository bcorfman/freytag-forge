"""CLI for deterministic Phase-5 storylet evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from storygame.authoring.compiler import load_runtime_narrative_fixture
from storygame.authoring.storylet_simulation import simulate_storylets, write_simulation_report
from storygame.runtime.narrative import RuntimeNarrativeProjection
from storygame.runtime.state import bootstrap_runtime_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-storylet-simulate")
    parser.add_argument("--genre", required=True, choices=("mystery", "fantasy", "sci-fi", "relationship"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--max-turns", type=int, default=12)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    projection = load_runtime_narrative_fixture(args.genre)
    if not isinstance(projection, RuntimeNarrativeProjection):
        raise SystemExit("SIMULATION_PACKAGE_UNAVAILABLE: fixture has no reviewed narrative package")
    report = simulate_storylets(projection, lambda: bootstrap_runtime_state(projection), max_turns=args.max_turns)
    write_simulation_report(args.output, report)
    print(f"simulation: {args.output}")
    return 0
