"""Offline command line entry point for the evaluation harness."""

from __future__ import annotations

import argparse
from pathlib import Path

from storygame.story_package.loader import load_story_package

from .model import EvalCase, Expectation, load_cases
from .runner import PipelineArm, render_report, run_arm


def _smoke() -> int:
    case = EvalCase(
        id="smoke-1a-search",
        category="smoke",
        split="diagnostic",
        scene="1A",
        setup_facts=(),
        commands=("Search the kitchen.",),
        save_load_after=None,
        expect=Expectation(),
    )
    package = load_story_package(Path("data/stories/continuity-initiative"))
    arm = PipelineArm(lambda _: {"segments": [{"kind": "narration", "text": "You search the kitchen."}]})
    print(render_report({arm.name: run_arm(arm, (case,), package)}, (case,)))
    return 0


def _report(path: str) -> int:
    cases = load_cases(path)
    counts: dict[tuple[str, str], int] = {}
    for case in cases:
        counts[(case.category, case.split)] = counts.get((case.category, case.split), 0) + 1
    for (category, split), count in sorted(counts.items()):
        print(f"{category} [{split}]: {count}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bench.pipeline_eval")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("smoke")
    report = subparsers.add_parser("report")
    report.add_argument("--cases", required=True)
    args = parser.parse_args(argv)
    if args.command == "smoke":
        return _smoke()
    return _report(args.cases)


if __name__ == "__main__":
    raise SystemExit(main())
