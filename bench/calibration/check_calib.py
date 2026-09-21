"""Score saved judge verdicts against an author's calibration labels."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", required=True, type=Path)
    parser.add_argument("--judgments", type=Path)
    parser.add_argument("--records", type=Path)
    parser.add_argument("--bar", type=float, default=0.9)
    args = parser.parse_args()

    labels = json.loads(args.labels.read_text())
    results_dir = Path(labels["results_dir"])
    judgments_dir = args.judgments or results_dir
    records_path = args.records or results_dir / "all-turn-records.json"
    records = json.loads(records_path.read_text())

    report = []
    passed = True
    for block, filename in (
        ("continuity", "continuity-judgments.json"),
        ("fact", "fact-tracking-judgments.json"),
    ):
        path = judgments_dir / filename
        if not path.exists():
            print(f"FAIL: {filename} missing")
            return 1
        judgments = json.loads(path.read_text())["judgments"]
        agree = total = 0
        per_label: dict[str, list[int]] = {}
        mismatches = []
        for run, judgment in zip(records["runs"], judgments, strict=True):
            by_turn = {verdict["turn"]: verdict for verdict in judgment["turns"]}
            for turn in run["turns"]:
                key = f"{run['replicate']}:{turn['turn_number']}"
                wanted = labels[block][key]
                verdict = by_turn.get(turn["turn_number"])
                for label, expected in wanted.items():
                    total += 1
                    counts = per_label.setdefault(label, [0, 0])
                    counts[1] += 1
                    actual = verdict.get(label) if verdict else None
                    if actual == expected:
                        agree += 1
                        counts[0] += 1
                    else:
                        reason = verdict.get("reason", "") if verdict else "no verdict"
                        mismatches.append(
                            f"r{run['replicate']} t{turn['turn_number']} {label}: "
                            f"want {expected}, judge {actual} - {reason}"
                        )
        rate = agree / total if total else 0
        report.append(f"## {block} judge: {agree}/{total} = {rate:.1%}")
        report.extend(f"- {label}: {good}/{count}" for label, (good, count) in sorted(per_label.items()))
        report.append("Mismatches:")
        report.extend(f"  - {mismatch}" for mismatch in mismatches)
        if rate < args.bar or any(good / count < args.bar for good, count in per_label.values()):
            passed = False

    text = "\n".join(report)
    (judgments_dir / "calibration-report.md").write_text(text + "\n")
    print(text)
    if not passed:
        print(f"FAIL: a judge agreed with the labels on less than {args.bar:.0%} of cells")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
