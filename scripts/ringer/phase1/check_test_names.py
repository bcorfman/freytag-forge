"""Fail if any test function name present at git HEAD vanished, or a frozen file was edited.

Run inside a worktree after `git add`: python scripts/ringer/phase1/check_test_names.py [frozen files...]
"""

import ast
import pathlib
import subprocess
import sys


def _names(source: str) -> set[str]:
    return {
        node.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    }


def main(frozen: list[str]) -> int:
    vanished = []
    for path in sorted(pathlib.Path("tests").glob("test_*.py")):
        old = subprocess.run(["git", "show", f"HEAD:{path.as_posix()}"], capture_output=True, text=True)
        if old.returncode:
            continue
        gone = _names(old.stdout) - _names(path.read_text(encoding="utf-8"))
        if gone:
            vanished.append((path.as_posix(), sorted(gone)))
    if vanished:
        print("FAIL test function names vanished:", vanished)
        return 1
    changed = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True).stdout.split()
    touched = [name for name in changed if name in frozen]
    if touched:
        print("FAIL frozen files edited:", touched)
        return 1
    print("test names preserved; no frozen file edited")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
