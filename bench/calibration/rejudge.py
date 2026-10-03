"""Re-run both judges over a saved results directory."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from storygame.story_package.loader import load_story_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--variation",
        type=Path,
        default=Path("bench/variations/item-facts-world-two-scene.json"),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    backend = os.environ.get("BENCH_FACT_JUDGE", "").strip() or "jev"
    if backend not in {"jev", "luna"}:
        raise ValueError(f"unknown fact judge backend: {backend}")

    args.out.mkdir(parents=True, exist_ok=True)
    records = json.loads((args.results / "all-turn-records.json").read_text())
    sys.path.insert(0, ".")
    from bench.judge_input import judge_turns  # noqa: E402
    from storygame.runtime.item_facts import _protagonist_name  # noqa: E402

    package_path = records.get("package_path") or "data/stories/continuity-initiative"
    if not Path(package_path).exists():
        package_path = "data/stories/continuity-initiative"
    package = load_story_package(Path(package_path))
    variation = json.loads(args.variation.read_text())
    state_axes = variation.get("item_facts", {}).get("state_axes", {})
    records["runs"] = [
        {
            **run,
            "turns": judge_turns(
                run.get("turns", []),
                run.get("scene_transitions", []),
                package,
                state_axes=state_axes,
            ),
        }
        for run in records.get("runs", [])
    ]
    records["package_path"] = str(package_path)
    (args.out / "input.json").write_text(json.dumps(records))
    if args.dry_run:
        print("wrote", args.out / "input.json")
        return 0
    continuity = subprocess.run(
        [
            "node",
            "bench/continuity-judge.mjs",
            "--input",
            str(args.out / "input.json"),
            "--output",
            str(args.out / "continuity-judgments.json"),
        ],
        capture_output=True,
        text=True,
    )
    print("continuity-judge.mjs", "rc", continuity.returncode, continuity.stderr.strip()[-500:])
    if continuity.returncode:
        return continuity.returncode

    if backend == "jev":
        fact_command = [
            "node",
            "bench/jev-judge.mjs",
            "--input",
            str(args.out / "input.json"),
            "--package",
            str(package_path),
            "--out",
            str(args.out),
            "--judges",
            "fact",
        ]
        protagonist_name = _protagonist_name(package)
        if protagonist_name is not None:
            fact_command.extend(["--protagonist", protagonist_name])
    else:
        fact_command = [
            "node",
            "bench/fact-tracking-judge.mjs",
            "--input",
            str(args.out / "input.json"),
            "--output",
            str(args.out / "fact-tracking-judgments.json"),
        ]
    fact = subprocess.run(fact_command, capture_output=True, text=True)
    print("fact judge", "rc", fact.returncode, fact.stderr.strip()[-500:])
    if fact.returncode:
        return fact.returncode
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
