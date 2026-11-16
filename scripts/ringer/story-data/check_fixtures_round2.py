"""Independent check for fixtures round 2 (contract section 10, F02 to F31).

Run: `python check_fixtures_round2.py <worktree> <first> <last>` with fixture numbers, for example `2 8`.
Shape only (no compiler exists): each fixture needs its test file, the contract names it must cite,
at least one test that runs today without the compiler, and no vacuous skips.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# number: (file stem suffix, tokens the test file must contain)
FIXTURES: dict[int, tuple[str, list[str]]] = {
    2: ("dup_key", ["L1.duplicate_key"]),
    3: ("unknown_key", ["L1.unknown_key", "done_when"]),
    4: ("fact_two_owners", ["L2.fact_one_owner"]),
    5: ("fact_wrong_scene", ["L2.fact_declaring_scene"]),
    6: ("claim_unauthorized", ["L2.claim_authorized", "commits_subset"]),
    7: ("leak_narrowed", ["L2.override_add_only", "boundaries"]),
    8: ("dangling", ["L2.dangling_ref", "use"]),
    9: ("cycles", ["cycle"]),
    10: ("outcome_not_committed", ["outcome"]),
    11: ("observes_missing", ["L2.incident_observes_outcomes"]),
    12: ("passage_rules", ["AMBIGUOUS", "text_when"]),
    13: ("leak_null_vs_empty", ["leak_terms"]),
    14: ("two_owners_manifest", ["L2.ownership"]),
    15: ("manifest_absent", ["manifest"]),
    16: ("claim_order", ["claims"]),
    17: ("lexicon_off_ignored", ["lexicon.yaml"]),
    18: ("lexicon_ref_when_off", ["L1.lexicon_off", "$memory_card"]),
    19: ("lexicon_roundtrip", ["expand"]),
    20: ("lexicon_stale", ["L2.lock_stale"]),
    21: ("override_ratio", ["override_ratio", "over"]),
    22: ("plural_twins", ["L1.plural_off"]),
    23: ("parity_classes", ["parity"]),
    24: ("review_digest", ["digest"]),
    25: ("save_identity", ["UserWarning", "retired_ids"]),
    26: ("review_isolation", ["note"]),
    27: ("examples", ["k_sl_1a_b_r0"]),
    28: ("lookup", ["story_text", "KeyError"]),
    29: ("typed_needs", ["required_dependencies"]),
    30: ("claimless_variant", ["claim_id"]),
    31: ("deterministic", ["digest"]),
}


def main() -> int:
    root = Path(sys.argv[1])
    first, last = int(sys.argv[2]), int(sys.argv[3])
    failures: list[str] = []
    for number in range(first, last + 1):
        stem, tokens = FIXTURES[number]
        path = root / "tests" / "story_source" / f"test_f{number:02d}_{stem}.py"
        if not path.is_file():
            failures.append(f"F{number:02d}: missing {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                failures.append(f"F{number:02d}: test file never mentions {token!r}")
        tree = ast.parse(text)
        tests = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        skipping = [t for t in tests if "importorskip" in ast.get_source_segment(text, t)]
        if len(tests) - len(skipping) < 1:
            failures.append(f"F{number:02d}: every test waits for the compiler; need one that runs today")
        if not skipping and number not in (15, 31):
            failures.append(f"F{number:02d}: no test asserts the compiler or validator result (importorskip)")
        if "pytest.mark.skip" in text or "xfail" in text:
            failures.append(f"F{number:02d}: unconditional skip or xfail is not allowed")
    for failure in failures:
        print(failure)
    print(f"{'FAIL' if failures else 'ok'}: F{first:02d} to F{last:02d}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
