"""Round 2 check, run from the task's worktree: callers switched to World helpers, old walks gone, tests pass.

Usage: check_round2.py <group> <patch output path>
"""

import re
import subprocess
import sys
from pathlib import Path

MAIN = "/home/bcorfman/dev/freytag-forge"
GROUPS = {
    "item-facts": {
        "files": {
            "storygame/runtime/item_facts.py": {
                "forbid": [r"seat_for\s*==\s*place_parent"],
                "require": [r"\.contains\(", r"\.under_contents\(", r"\.seats\("],
            }
        }
    },
    "capture-observation": {
        "files": {
            "storygame/runtime/capture.py": {
                "forbid": [r"def _descendants\b", r"def _focus_open_state\b"],
                "require": [r"\.open_state\(", r"\.moved_since\("],
            },
            "storygame/runtime/observation.py": {
                "forbid": [
                    r"def _descendants\b",
                    r"def _is_item\b",
                    r"def _candidate_ids\b",
                    r"def _required_ids\b",
                ],
                "require": [r"\.observable_items\(", r"\.required_observations\("],
            },
        }
    },
    "seating-misc": {
        "files": {
            "storygame/runtime/traversal.py": {"forbid": [r"def _contains\b"], "require": [r"\.contains\("]},
            "storygame/runtime/narration_safety.py": {
                "forbid": [r"def _related_area_ids\b", r"def _location_ancestor_ids\b"],
                "require": [r"\.related_areas\(", r"\.area_ancestors\("],
            },
            "storygame/runtime/seating.py": {
                "forbid": [],
                "require": [r"\.current_seat\(", r"\.reachable_from_seat\(", r"\.visible_vehicle_seats\("],
            },
            "storygame/runtime/taking.py": {"forbid": [], "require": [r"\.takeable_items\("]},
            "storygame/runtime/fixed_refusal.py": {"forbid": [], "require": [r"\.fixed_visible_items\("]},
        }
    },
}
MODULES = "item_facts|capture|observation|seating|taking|fixed_refusal|traversal|narration_safety"


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    env = {"PYTHONPATH": str(Path.cwd()), "TMPDIR": "/tmp", "PATH": "/usr/bin:/bin"}
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def main() -> int:
    group, patch_out = sys.argv[1], Path(sys.argv[2])
    rules = GROUPS[group]["files"]
    py = f"{MAIN}/.venv/bin/python"
    errors = []
    changed = run(["git", "status", "--porcelain"]).stdout.split("\n")
    changed_paths = {line[3:].strip() for line in changed if line.strip()}
    stray = sorted(p for p in changed_paths if p not in rules)
    if stray:
        errors.append(f"changed files outside your ownership: {stray}")
    untouched = sorted(p for p in rules if p not in changed_paths)
    if untouched:
        errors.append(f"owned files not changed: {untouched}")
    for path, rule in rules.items():
        text = Path(path).read_text()
        for pattern in rule["forbid"]:
            if re.search(pattern, text):
                errors.append(f"{path}: still contains /{pattern}/ (the world logic must move to the World helper)")
        for pattern in rule["require"]:
            if not re.search(pattern, text):
                errors.append(f"{path}: never calls /{pattern}/")
    if errors:
        print("FAIL:\n" + "\n".join(errors))
        return 1
    lint = run([py, "-m", "ruff", "check", *rules])
    fmt = run([py, "-m", "ruff", "format", "--check", *rules])
    if lint.returncode or fmt.returncode:
        print("FAIL ruff:\n" + lint.stdout + fmt.stdout)
        return 1
    tests = sorted(
        str(p)
        for p in Path("tests").glob("*.py")
        if re.search(rf"runtime\.({MODULES})\b|runtime import .*\b({MODULES})\b", p.read_text())
    )
    result = run([py, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-n", "8", *tests, "packages/worldkeeper/tests"])
    print(result.stdout[-4000:], result.stderr[-2000:])
    if result.returncode:
        print(f"FAIL: focused tests failed ({len(tests)} files)")
        return 1
    run(["git", "add", "-A"])
    diff = run(["git", "diff", "--cached"]).stdout
    patch_out.write_text(diff)
    print(f"PASS {group}: patch {patch_out} ({len(diff.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
