"""Print a read-only dependency report for one package record."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from storygame.story_package.impact_report import render_impact_report

_STORIES = Path(__file__).resolve().parents[1] / "data" / "stories"
DEFAULT_ROOT = next(path for path in sorted(_STORIES.iterdir()) if path.is_dir())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("subject")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    options = parser.parse_args(argv)
    try:
        print(render_impact_report(options.root, options.subject), end="")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
