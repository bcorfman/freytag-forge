"""Print a read-only branch handoff report for one incident."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORLDKEEPER_SRC = REPO_ROOT / "packages" / "worldkeeper" / "src"
for path in (REPO_ROOT, WORLDKEEPER_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from storygame.story_package.branch_report import render_branch_report  # noqa: E402

_STORIES = REPO_ROOT / "data" / "stories"
DEFAULT_ROOT = next(path for path in sorted(_STORIES.iterdir()) if path.is_dir())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("incident")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    options = parser.parse_args(argv)
    try:
        print(render_branch_report(options.root, options.incident), end="")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
