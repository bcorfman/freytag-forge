# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 11b: factory station 6 (prompt snapshot), free: `bench prompt` captures compared against a baseline, diff limited to intended lines.

One Codex task. Usage: build_round11b_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-prompt-snapshot"

OWNED = [
    "factory/stations/prompt_snapshot.py",
    "factory/stations/__init__.py",
    "tests/test_factory_prompt_snapshot.py",
    "tests/test_factory_stations.py",
]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, standard library only). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. `factory/line.py` drives tickets through fixed stations with handlers `Callable[[Ticket, datetime], StationResult]` (`StationResult(passed, check, output, tokens=0)`). `factory/stations/` already holds handlers for stations 2 and 5; read `factory/stations/__init__.py`, `factory/stations/free_gates.py` (its style, its injected `run` callable, its 4000-character output cap) and `tests/test_factory_stations.py` first. This task builds station 6, `Station.PROMPT_SNAPSHOT`: "payload diff limited to intended lines". The free command `python -m bench prompt` (see `bench/cli.py`, function `_prompt`) prints the exact narrator prompt for a scene: `python -m bench prompt --scene 1A --text` is the prompt as the scene is entered; `--beat 1A.2 --text` is one beat; `--scene 1A --list-beats` prints beat ids (lines `1A.1  Title`) then a blank line then storylets (`SL-1A-A  Title  (presents ...)`). It takes about 2 seconds, calls no model, and is deterministic. The idea: capture every prompt for a scene before a change (the baseline), capture again after, and require that every added or removed line is one the ticket intended.

YOUR TASK. Create `factory/stations/prompt_snapshot.py` and `tests/test_factory_prompt_snapshot.py`; edit `factory/stations/__init__.py` to add `Station.PROMPT_SNAPSHOT: prompt_snapshot_handler(root)` to `build_handlers` and update its trailing comment (stations 0, 1, 3, 4, 7, 8 and 9 remain unbuilt); edit `tests/test_factory_stations.py` ONLY where its `build_handlers` assertion expects exactly two stations (make it expect three). Own nothing else.

prompt_snapshot.py:
- `capture_scene(scene: str, out_dir: Path, *, root: Path, package: str | None = None, run=subprocess.run) -> list[str]`: writes one text file per capture into out_dir (create it): `<scene>.entry.txt` (the entry prompt) and `<scene>.beat-<beat id>.txt` for each beat id found by `--list-beats` (take the beat lines before the blank line; the id is the first whitespace-separated token). Commands run through `run` with cwd=root, `sys.executable -m bench prompt ...`, `--package PATH` added when `package` is given, `capture_output=True, text=True, timeout=120`. A non-zero exit or `subprocess.TimeoutExpired` raises `SnapshotError(message)` (define it; the message names the command's tail of stderr). Returns the written file names, sorted.
- `diff_captures(baseline_dir: Path, current_dir: Path) -> dict[str, list[str]]`: for every capture name in either directory, the changed lines as `+<line>` and `-<line>` strings from `difflib.unified_diff` (skip the `---`, `+++` and `@@` header lines; ignore blank-only lines). A capture only in current gives `+` lines for all its lines , and a capture only in baseline gives `-` lines. Return `dict[str, list[str]]` and let the caller tell new and removed captures by checking whether the file exists in each directory. Identical captures are omitted.
- `unintended(changes: dict[str, list[str]], allowed: list[dict], baseline_dir: Path, current_dir: Path) -> list[str]`: returns one line per unintended change, formatted `<capture>: <+/-line>`; for a new or removed capture one line `<capture>: new capture` or `<capture>: removed capture` instead of its lines. `allowed` is the payload's `allowed_changes`: a list of dicts `{{"capture": "<name or beat id or 'entry' or '*'>", "contains": ["<substring>", ...], "new_capture": false}}`. A changed line is intended when some entry matches its capture and one of that entry's `contains` substrings occurs in the line (without its leading +/-). `capture` matches the capture file name exactly, or the part after `<scene>.` (so `entry` or `beat-1B.4`), or a bare beat id (`1B.4` matches `beat-1B.4`), or `*` for any. A new or removed capture is intended only when an entry matches it and has `"new_capture": true`.
- `prompt_snapshot_handler(root: Path | None = None, run=subprocess.run) -> StationHandler`. `root` defaults to the repository root (two parents above `factory/`). Payload keys: `baseline_dir` (REQUIRED, path, relative paths resolve against root; it must exist and hold the baseline for `ticket.scene`), `allowed_changes` (optional list, default empty: nothing may change), `package` (optional, passed as `--package`). The handler captures `ticket.scene` into a fresh temporary directory (clean it up afterwards), compares with the baseline (only the files that start with `<scene>.` in the baseline), and passes when `unintended` is empty: `StationResult(True, "prompt_snapshot", "<n> captures compared, <m> intended changed lines")`. On failure `StationResult(False, "prompt_snapshot", output)` with the unintended lines (keep the first 4000 characters, and say how many more lines were cut). A missing `baseline_dir` key, a baseline directory that does not exist or holds no capture for the scene, or a `SnapshotError` fails with a plain reason; never raise for these. tokens is always 0.
- A tiny CLI so a baseline can be recorded: `python -m factory.stations.prompt_snapshot record --scene 1A --out DIR [--package PATH]` (expose `main(argv=None) -> int`; prints the written file names; exit 0, or 2 on SnapshotError with the message).

TESTS (`tests/test_factory_prompt_snapshot.py`, hermetic apart from the single real-bench test, tmp_path only, no network, no model). With a fake `run` that returns scripted stdout per command: capture_scene file names and contents for an entry plus two beats, the `--package` flag, a non-zero exit and a TimeoutExpired raising SnapshotError; diff_captures on identical, one changed line, a new capture and a removed capture, blank-only changes ignored; `unintended` with every matching rule (exact file name, `entry`, `beat-1B.4`, bare beat id, `*`, `new_capture`, a substring that does not occur); the handler passing when nothing changed, passing when the only changed line is allowed, failing with the exact unintended line, the 4000-character cap with a cut count, missing `baseline_dir`, missing directory, empty baseline for the scene, and that the temporary directory is removed. One real-bench test: record the baseline for scene `1A` with `capture_scene` using the real `bench` into tmp_path (about 2 seconds per capture, 5 captures), then run the handler with the real `run` against it and assert it passes with zero changed lines; then append a line to one baseline file and assert the handler now fails and names that capture.

HARD LIMITS. Edit only the four files above. Never edit `bench/`, `factory/config/`, other factory modules or other tests. Do not add dependencies. Write NOTES_11b.txt (worktree root, never committed) listing every rule you found ambiguous and the choice you made.
"""

CHECK = f"""set -e
WORK={WORK}
mkdir -p "$WORK"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF -e factory/stations/prompt_snapshot.py -e factory/stations/__init__.py -e tests/test_factory_prompt_snapshot.py -e tests/test_factory_stations.py || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
for f in factory/stations/prompt_snapshot.py tests/test_factory_prompt_snapshot.py; do [ -s "$f" ] || {{ echo "missing $f"; exit 1; }}; done
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_prompt_snapshot.py tests/test_factory_stations.py tests/test_factory_line.py tests/test_factory_frozen.py
.venv/bin/python -m ruff check factory/stations tests/test_factory_prompt_snapshot.py tests/test_factory_stations.py
.venv/bin/python -m ruff format --check factory/stations tests/test_factory_prompt_snapshot.py tests/test_factory_stations.py
# independent probe: record a real baseline for 1B, check the handler passes, then break it
out="$WORK/probe.out"
base=$(mktemp -d)
.venv/bin/python -m factory.stations.prompt_snapshot record --scene 1B --out "$base" > "$out" 2>&1
test "$(ls "$base" | wc -l)" -ge 3 || {{ echo "record wrote too few captures"; cat "$out"; exit 1; }}
.venv/bin/python - "$base" >> "$out" 2>&1 <<'PY'
import sys
from datetime import UTC, datetime
from pathlib import Path
from factory.stations import build_handlers
from factory.tickets import Station, Ticket

base = Path(sys.argv[1])
now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
def ticket(payload):
    return Ticket(id="t", scene="1B", station=Station.PROMPT_SNAPSHOT, token_budget=1, created_at=now, updated_at=now, payload=payload)
handler = build_handlers(Path.cwd())[Station.PROMPT_SNAPSHOT]
r = handler(ticket({{"baseline_dir": str(base)}}), datetime.now(UTC))
assert r.passed and r.tokens == 0, r
victim = sorted(base.glob("1B.beat-*.txt"))[0]
victim.write_text(victim.read_text() + "\\nAn unintended new line.\\n")
r = handler(ticket({{"baseline_dir": str(base)}}), datetime.now(UTC))
assert not r.passed and "unintended new line" in r.output and victim.stem.split(".", 1)[1] in r.output, r
r = handler(ticket({{"baseline_dir": str(base), "allowed_changes": [{{"capture": "*", "contains": ["unintended new line"]}}]}}), datetime.now(UTC))
assert r.passed, r
r = handler(ticket({{}}), datetime.now(UTC))
assert not r.passed, r
print("probe ok")
PY
cat "$out"
grep -q "probe ok" "$out" || {{ echo "probe failed"; exit 1; }}
git diff --cached > {WORK}/prompt-snapshot.patch
test -s {WORK}/prompt-snapshot.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-prompt-snapshot",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "station-6",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "Snapshot tests plus the station, line and frozen suites green; probe records a real 1B baseline, passes unchanged, fails on an added line naming the capture, passes when that line is allowed; ruff clean; only four files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round11b-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
