"""Check for the pipeline-eval widen task: run inside the worker's worktree."""

from __future__ import annotations

import collections
import json
import sys

REFUSAL_WORDS = ("cannot", "can't", "unable", "refuse")


def main(path: str) -> int:
    cases = json.load(open(path))["cases"]
    counts = collections.Counter((c["category"], c["split"]) for c in cases)
    categories = {c["category"] for c in cases}
    if len(categories) != 14:
        print(f"FAIL expected 14 categories, found {len(categories)}")
        return 1
    for category in sorted(categories):
        for split in ("diagnostic", "held_out"):
            if counts[(category, split)] < 3:
                print(f"FAIL {category} [{split}] has {counts[(category, split)]} cases, need 3")
                return 1
    for case in cases:
        included = " ".join(case.get("expect", {}).get("prose_includes", [])).lower()
        if any(word in included for word in REFUSAL_WORDS):
            print(f"FAIL refusal word match in {case['id']}")
            return 1
    print(f"cases {len(cases)} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
