"""Check for the probe-retirement task: seed paths are gone or explained, and nothing that survives names a removed module."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROTECTED = (
    "scripts/ringer/stage7/",
    "bench/frozen_prompts.py",
    "bench/exit_audit.py",
    "bench/frozen/",
    "bench/variations/",
    "bench/results/",
    "tests/shard_durations.json",
    "tests/story_source/",
    "data/",
    "storygame/",
    "packages/",
    "factory/",
    ".plans/",
)


LIVE_RINGER = ("stage7/", "story-data/", "dark-factory/", "gates/", "environment_narration/", "probe-retire/")


def is_live(path: str) -> bool:
    """Live code: everything except .plans and the historical run folders under scripts/ringer."""
    if path.startswith(".plans/"):
        return False
    if path.startswith("scripts/ringer/"):
        return path[len("scripts/ringer/") :].startswith(LIVE_RINGER)
    return True


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def main() -> int:
    seed = [line.strip() for line in Path(sys.argv[1]).read_text().splitlines() if line.strip()]
    notes = Path("NOTES_retire.txt").read_text() if Path("NOTES_retire.txt").exists() else ""
    problems: list[str] = []

    # 1. every seed path is gone, or restored and explained in the notes
    restored = [p for p in seed if Path(p).exists()]
    unexplained = [p for p in restored if p not in notes]
    if unexplained:
        problems.append(
            "seed paths still present and not explained in NOTES_retire.txt: " + ", ".join(unexplained[:15])
        )
    removed_count = len(seed) - len(restored)
    if removed_count < len(seed) * 0.9:
        problems.append(f"only {removed_count} of {len(seed)} seed paths were removed; expected at least 90 percent")

    # 2. protected paths unchanged
    changed = git("status", "--porcelain").splitlines()
    for line in changed:
        path = line[3:].strip().split(" -> ")[-1]
        if path.startswith(PROTECTED):
            problems.append(f"protected path changed: {path}")

    # 3. nothing surviving outside scripts/ringer run records names a removed python module
    removed = [p for p in seed if not Path(p).exists() and p.endswith(".py")]
    dotted = sorted({p[:-3].replace("/", ".") for p in removed if p.startswith(("tests/", "bench/", "scripts/"))})
    survivors = [
        f
        for f in git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
        if f.endswith(".py") and Path(f).exists() and is_live(f)
    ]
    for f in survivors:
        text = Path(f).read_text(errors="ignore")
        for name in dotted:
            if re.search(r"(?<![\w.])" + re.escape(name) + r"(?![\w])", text):
                problems.append(f"{f} still imports or names removed module {name}")
    if problems:
        print("\n".join(problems[:40]))
        return 1
    print(f"ok: {removed_count} of {len(seed)} seed paths removed, {len(restored)} restored and explained")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
