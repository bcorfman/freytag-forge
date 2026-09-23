"""Re-run both judges over a saved results directory."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from storygame.story_package.loader import load_story_package


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    records = json.loads((args.results / "all-turn-records.json").read_text())
    sys.path.insert(0, ".")
    from bench.core import load_variation  # noqa: E402
    from bench.judge_input import judge_turns  # noqa: E402

    variation = load_variation(Path("bench/variations/item-facts-package-two-scene.json"))
    package = load_story_package(Path(variation["_package_path"]))
    records["runs"] = [
        {
            **run,
            "turns": judge_turns(run.get("turns", []), run.get("scene_transitions", []), package),
        }
        for run in records.get("runs", [])
    ]
    records["package_path"] = str(variation["_package_path"])
    (args.out / "input.json").write_text(json.dumps(records))
    for judge, name in (
        ("continuity-judge.mjs", "continuity-judgments.json"),
        ("fact-tracking-judge.mjs", "fact-tracking-judgments.json"),
    ):
        result = subprocess.run(
            [
                "node",
                f"bench/{judge}",
                "--input",
                str(args.out / "input.json"),
                "--output",
                str(args.out / name),
            ],
            capture_output=True,
            text=True,
        )
        print(judge, "rc", result.returncode, result.stderr.strip()[-500:])
        if result.returncode:
            return result.returncode
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
