# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 11a: the first two factory station handlers, both free (no billed model): station 2 (world-need check) and station 5 (free gates).

One Codex task. Usage: build_round11a_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-stations"

OWNED = [
    "factory/stations/__init__.py",
    "factory/stations/world_need.py",
    "factory/stations/free_gates.py",
    "tests/test_factory_stations.py",
]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, standard library plus what the repo already uses). Never pass --cov to pytest. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <test files>`.

BACKGROUND. `factory/line.py` is a deterministic state machine. It calls one handler per ticket station: `StationHandler = Callable[[Ticket, datetime], StationResult]`, with `StationResult(passed, check, output, tokens=0)`. `python -m factory run --handlers module:function` loads a function that returns `dict[Station, handler]` (see `_handlers` in `factory/__main__.py`). Read `factory/line.py`, `factory/tickets.py` (the `Ticket` and `Station` classes; a ticket's `payload` is a free dict), `factory/checks/world_need.py`, `factory/checks/gap_delta.py` and `tests/test_factory_line.py` first. No handler is built yet. This task builds the two handlers that need no billed model: station 2 (`Station.WORLD_NEED`) and station 5 (`Station.FREE_GATES`). Handlers never call a model, so `tokens` is always 0.

YOUR TASK. Create exactly these four files and nothing else: `factory/stations/__init__.py`, `factory/stations/world_need.py`, `factory/stations/free_gates.py`, `tests/test_factory_stations.py`.

`factory/stations/__init__.py`: a docstring and `build_handlers(root: Path | None = None) -> dict[Station, StationHandler]` that returns `{{Station.WORLD_NEED: world_need_handler(root), Station.FREE_GATES: free_gates_handler(root)}}`. `root` is the repository root (default: two parents above `factory/`); relative paths in a ticket payload are resolved against it. Add a one-line comment that stations 0, 1, 3, 4, 6, 7, 8 and 9 are built in later rounds.

`factory/stations/world_need.py`: `world_need_handler(root: Path | None = None) -> StationHandler`. Payload keys: `contract` (required, path to an act-contract JSON file) and `story_root` (optional, default `factory.checks.gap_delta.DEFAULT_ROOT`). The handler loads the contract and the story package (`storygame.story_package.loader.load_story_package`), runs `check_needs` and `tickets_for` from `factory/checks/world_need.py`, and keeps only the results whose `scene_id` equals `ticket.scene` (when `ticket.scene` names no scene in the contract, keep all). It passes when every kept need is `ok`. On failure it returns `StationResult(False, "world_need", output)` where `output` has one line per non-ok need: `<kind> <scene_id> <need_id>: <summary>` (the same lines the CLI prints). A missing payload key, an unreadable file or invalid JSON returns `StationResult(False, "world_need", "<plain reason>")`; never raise for those. The `worldkeeper_ticket` outcome means a Worldkeeper change is needed; creating those tickets is a later round, so the output only lists them.

`factory/stations/free_gates.py`: `free_gates_handler(root: Path | None = None, run: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> StationHandler`. Payload keys, all optional unless marked: `story_root` (default DEFAULT_ROOT), `source_root` (a story source tree; skip that gate when absent), `gap_baseline` (path to a gap-rule baseline; REQUIRED, a missing key fails with a plain reason), `anchors` (list of anchor ids for the gap snapshot; default all), `paths` (changed files; ruff checks the `.py` ones), `tests` (pytest files to run; skip when absent). Gates run cheapest first and the handler STOPS at the first failure, returning `StationResult(False, <gate name>, <the gate's printed output, at most 4000 characters, the tail kept>)`. Gate names and order: `source_tree` (call `storygame.story_source.check_source_tree(Path(source_root))` and fail on any diagnostic, printing each one; then `compile_source_tree` and fail on an exception), `gap_delta` (use `factory.checks.gap_delta` functions `snapshot`, `load_baseline`, `new_results`; fail when `new_results` is non-empty or the snapshot has `__errors__`; print `NEW <anchor> <result>` lines like its CLI), `ruff` (run `.venv/bin/python -m ruff check` then `ruff format --check` on the `.py` paths through `run`, cwd = root), `tests` (run pytest through `run` with the command from `factory/checks/library.py::pytest_check`'s command line, cwd = root, timeout 1200). When all pass: `StationResult(True, "free_gates", "all free gates passed")`. The plan also lists a carry-matrix gate (no stuck state); it is not built yet, so leave it out and say so in the module docstring. A `subprocess.TimeoutExpired` is a failed gate named for that gate.

TESTS (`tests/test_factory_stations.py`, hermetic, tmp_path only, no live worker, no network). Station 2: the valid fixture `tests/fixtures/factory_contracts/ok.json` against the real story gives a result you can compute by calling `check_needs` yourself; assert the handler's `passed` equals `not tickets_for(...)` for that scene and, for a copy of the contract edited so one need names an unproduced fact (use the edit that makes `check_needs` return a non-ok need; find it by experiment), a failing result whose output has the `<kind> <scene_id> <need_id>:` line; missing `contract` key, missing file and invalid JSON each fail with a plain reason and no raise. Station 5: use a fake `run` that records commands and returns scripted exit codes; assert gate order, that it stops at the first failure (later gates not called), that the output tail is capped at 4000 characters, that a missing `gap_baseline` fails with a reason, the `.py`-only filtering of ruff paths, a `subprocess.TimeoutExpired` becoming a failed gate, and the all-pass result. For the source and gap gates, use the real committed tree (`data/stories/continuity-initiative/source`) and a baseline recorded in tmp_path with `factory.checks.gap_delta.save_baseline(snapshot(DEFAULT_ROOT, ["<one anchor>"]), path)` and `anchors=["<that anchor>"]` so the test stays fast; also assert a baseline missing one result makes the gap gate fail with a `NEW` line. Finally one test that `build_handlers()` returns exactly the two stations and that a `FactoryLine` built with them and a ticket at `Station.WORLD_NEED` advances the ticket to `Station.PROSE` when the handler passes (copy the setup from `tests/test_factory_line.py`).

HARD LIMITS. Edit only the four files above. Never edit `factory/config/`, `factory/contracts/`, other factory modules, `bench/` or other tests. Do not add dependencies. Write NOTES_11a.txt (worktree root, never committed) listing every rule you found ambiguous and the choice you made.
"""

CHECK = f"""set -e
WORK={WORK}
mkdir -p "$WORK"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF -e factory/stations/__init__.py -e factory/stations/world_need.py -e factory/stations/free_gates.py -e tests/test_factory_stations.py || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
for f in factory/stations/__init__.py factory/stations/world_need.py factory/stations/free_gates.py tests/test_factory_stations.py; do [ -s "$f" ] || {{ echo "missing $f"; exit 1; }}; done
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_stations.py tests/test_factory_line.py tests/test_factory_world_need.py tests/test_factory_gap_delta.py tests/test_factory_frozen.py
.venv/bin/python -m ruff check factory/stations tests/test_factory_stations.py
.venv/bin/python -m ruff format --check factory/stations tests/test_factory_stations.py
# independent probe: the real handler on the real story, then a deliberately broken baseline
out="$WORK/probe.out"
.venv/bin/python - > "$out" 2>&1 <<'PY'
import json, sys, tempfile
from datetime import UTC, datetime
from pathlib import Path
from factory.stations import build_handlers
from factory.tickets import Station, Ticket
from factory.checks.gap_delta import DEFAULT_ROOT, snapshot, save_baseline

now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
def ticket(station, payload):
    return Ticket(id="t", scene="1A", station=station, token_budget=1, created_at=now, updated_at=now, payload=payload)

handlers = build_handlers(Path.cwd())
assert set(handlers) == {{Station.WORLD_NEED, Station.FREE_GATES}}, set(handlers)
r = handlers[Station.WORLD_NEED](ticket(Station.WORLD_NEED, {{"contract": "tests/fixtures/factory_contracts/ok.json"}}), datetime.now(UTC))
print("world_need:", r.passed, r.output[:200])
r = handlers[Station.WORLD_NEED](ticket(Station.WORLD_NEED, {{"contract": "does/not/exist.json"}}), datetime.now(UTC))
assert not r.passed and r.tokens == 0, r
snap = snapshot(DEFAULT_ROOT, None)
anchor = next(a for a, v in snap.items() if a != "__errors__")
d = Path(tempfile.mkdtemp())
save_baseline({{anchor: []}}, d / "good.json") if not snap[anchor] else save_baseline({{anchor: snap[anchor]}}, d / "good.json")
r = handlers[Station.FREE_GATES](ticket(Station.FREE_GATES, {{"gap_baseline": str(d / "good.json"), "anchors": [anchor]}}), datetime.now(UTC))
print("free_gates good baseline:", r.passed, r.check)
assert r.passed, r
if snap[anchor]:
    save_baseline({{anchor: snap[anchor][1:]}}, d / "bad.json")
    r = handlers[Station.FREE_GATES](ticket(Station.FREE_GATES, {{"gap_baseline": str(d / "bad.json"), "anchors": [anchor]}}), datetime.now(UTC))
    print("free_gates bad baseline:", r.passed, r.check)
    assert not r.passed and r.check == "gap_delta" and "NEW" in r.output, r
r = handlers[Station.FREE_GATES](ticket(Station.FREE_GATES, {{}}), datetime.now(UTC))
assert not r.passed, r
print("probe ok")
PY
cat "$out"
grep -q "probe ok" "$out" || {{ echo "probe failed"; exit 1; }}
git diff --cached > {WORK}/stations.patch
test -s {WORK}/stations.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-stations",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "stations-2-5",
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
                "verified": "Station tests plus the line, world-need, gap-delta and frozen suites green; probe runs the real handlers on the real story and a corrupted baseline fails the gap gate; ruff clean; only four files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round11a-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
