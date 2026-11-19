"""Report per-test redundancy from a coverage data file."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from coverage import CoverageData


def _base_test_id(context: str) -> str:
    """Remove coverage.py's phase suffix from a test context."""

    return context.split("|", 1)[0]


def _test_lines(data: CoverageData) -> dict[str, set[tuple[str, int]]]:
    """Return each test's distinct covered file/line pairs."""

    tests: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for filename in data.measured_files():
        for line, contexts in data.contexts_by_lineno(filename).items():
            for context in contexts:
                tests[_base_test_id(context)].add((filename, line))
    return dict(tests)


def _subset_candidates(
    test_id: str, lines: set[tuple[str, int]], line_tests: dict[tuple[str, int], set[str]]
) -> list[str]:
    """Find superset tests by intersecting the inverted index for each line."""

    if not lines:
        return []
    candidates: set[str] | None = None
    for line in lines:
        matching = line_tests[line] - {test_id}
        candidates = matching if candidates is None else candidates & matching
        if not candidates:
            return []
    return sorted(candidates)[:3]


def build_report(data: CoverageData) -> dict[str, object]:
    """Build the JSON-serializable redundancy report for loaded coverage data."""

    tests = _test_lines(data)
    line_tests: dict[tuple[str, int], set[str]] = defaultdict(set)
    for test_id, lines in tests.items():
        for line in lines:
            line_tests[line].add(test_id)

    unique_counts = {test_id: sum(len(line_tests[line]) == 1 for line in lines) for test_id, lines in tests.items()}
    per_test = []
    for test_id, lines in tests.items():
        per_test.append(
            {
                "id": test_id,
                "lines": len(lines),
                "unique_lines": unique_counts[test_id],
                "subset_of": (_subset_candidates(test_id, lines, line_tests) if unique_counts[test_id] == 0 else []),
            }
        )
    per_test.sort(key=lambda item: (item["unique_lines"] != 0, item["lines"], item["id"]))

    equal_sets: dict[frozenset[tuple[str, int]], list[str]] = defaultdict(list)
    for test_id, lines in tests.items():
        equal_sets[frozenset(lines)].append(test_id)
    identical_groups = [sorted(group) for group in equal_sets.values() if len(group) >= 2]
    identical_groups.sort(key=lambda group: group[0])

    return {
        "tests": len(tests),
        "files": len(data.measured_files()),
        "per_test": per_test,
        "no_unique_lines": [item["id"] for item in per_test if item["unique_lines"] == 0],
        "identical_groups": identical_groups,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_data_file", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if not args.coverage_data_file.is_file() or args.coverage_data_file.stat().st_size == 0:
        print(f"Coverage data file is missing or empty: {args.coverage_data_file}", file=sys.stderr)
        return 2

    data = CoverageData(basename=str(args.coverage_data_file))
    try:
        data.read()
    except Exception as exc:
        print(f"Could not read coverage data file {args.coverage_data_file}: {exc}", file=sys.stderr)
        return 2
    if not data.measured_files() or not data.measured_contexts():
        print(f"Coverage data file is empty: {args.coverage_data_file}", file=sys.stderr)
        return 2

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(build_report(data), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
