"""Print deterministic, read-only story gap flags."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from storygame.story_package.gap_rules import render_flags, run_gap_rules

_STORIES = Path(__file__).resolve().parents[1] / "data" / "stories"
DEFAULT_ROOT = next(path for path in sorted(_STORIES.iterdir()) if path.is_dir())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("anchor")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--rule", action="append", dest="rules")
    options = parser.parse_args(argv)
    try:
        flags = run_gap_rules(options.root, options.anchor, options.rules)
        print(render_flags(flags, options.anchor), end="")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
