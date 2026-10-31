"""Validate a worldkeeper boundary audit report written by a Ringer review worker.

Usage: check_audit.py <report.json> <owned source file>...
"""

import ast
import json
import sys
from pathlib import Path

ROOT = Path("/home/bcorfman/dev/freytag-forge")
VERDICTS = {"move", "split", "stay"}


def functions(path: Path) -> dict[str, tuple[int, int]]:
    tree = ast.parse(path.read_text())
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found[node.name] = (node.lineno, node.end_lineno or node.lineno)
    return found


def main() -> int:
    report_path = Path(sys.argv[1])
    owned = {str(Path(p).relative_to(ROOT)) if p.startswith("/") else p for p in sys.argv[2:]}
    errors = []
    try:
        report = json.loads(report_path.read_text())
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: report is not valid JSON: {exc}")
        return 1
    entries = report.get("findings")
    if not isinstance(entries, list) or not entries:
        print("FAIL: report needs a non-empty 'findings' list")
        return 1
    covered = set()
    cache = {}
    for i, entry in enumerate(entries):
        where = f"findings[{i}]"
        for key in ("file", "function", "verdict", "world_state_read", "reason"):
            if not entry.get(key):
                errors.append(f"{where}: missing '{key}'")
        file = entry.get("file", "")
        if file not in owned:
            errors.append(f"{where}: file {file!r} is not one of the audited files {sorted(owned)}")
            continue
        covered.add(file)
        if file not in cache:
            cache[file] = functions(ROOT / file)
        name = entry.get("function", "")
        if name not in cache[file]:
            errors.append(f"{where}: function {name!r} does not exist in {file}")
        verdict = entry.get("verdict")
        if verdict not in VERDICTS:
            errors.append(f"{where}: verdict {verdict!r} not in {sorted(VERDICTS)}")
        if verdict in {"move", "split"}:
            for key in ("proposed_world_method", "callers"):
                if not entry.get(key):
                    errors.append(f"{where}: a {verdict} finding needs '{key}'")
            if entry.get("needs_story_package") is not False:
                errors.append(f"{where}: a {verdict} finding must set needs_story_package false for the moved part")
    missing = owned - covered
    if missing:
        errors.append(f"no findings at all for {sorted(missing)}; list every function that calls World, even as 'stay'")
    if errors:
        print("FAIL:")
        print("\n".join(errors))
        return 1
    counts = {v: sum(1 for e in entries if e.get("verdict") == v) for v in sorted(VERDICTS)}
    print(f"PASS: {len(entries)} findings {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
