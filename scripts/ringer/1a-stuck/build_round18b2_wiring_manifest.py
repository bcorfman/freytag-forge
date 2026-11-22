# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18b-2: station 4, the wiring handler. FREE to test: no model call, no network, no real Ringer run in tests.

A lint-clean fix plan (round 18b-1) becomes one Ringer task whose check proves the change, a per-ticket git worktree
holds the patched tree, and stations 5 and 6 run on that tree (`payload` workspace, not the repository root).
One Codex task. Usage: build_round18b2_wiring_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-wiring-station"

OWNED = [
    "factory/stations/wiring.py",
    "factory/stations/tree.py",
    "factory/stations/free_gates.py",
    "factory/stations/prompt_snapshot.py",
    "factory/stations/__init__.py",
    "tests/test_factory_wiring.py",
    "tests/test_factory_stations.py",
    "tests/test_factory_prompt_snapshot.py",
    "tests/shard_durations.json",
]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run a real `ringer.py`, npm, playwright or the bench. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12, standard library plus what the repo already uses). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. The dark factory (`factory/`; read `factory/line.py`, `factory/tickets.py`, `factory/followups.py`, `factory/manifests.py` (`TaskSpec`, `build_manifest`, `lint_check`), `factory/stations/__init__.py`, `factory/stations/free_gates.py`, `factory/stations/prompt_snapshot.py` and the new `factory/stations/fix_plan.py` with `tests/test_factory_fix_plan.py` first) turns failing playtest turns into tickets. Round 18b-1 built `lint_plan` and `build_evidence`. A fix plan (format in `fix_plan.py`) is ONE of two kinds: `add_pacing_beat` (a new beat in a scene's `beats:` list) or `set_text` (change a `claim:<id>.text`). You now build station 4, the wiring handler, and the mechanism that lets stations 5 and 6 run on the patched tree. Station 4 uses NO model itself: a Codex worker (Luna) types the change inside a Ringer task, and a deterministic check decides.

BUILD.
(1) `factory/stations/tree.py`: `ticket_tree(payload: dict, ticket_id: str, root: Path) -> Path | None`. A ticket that went through station 4 has a tree at `<payload["workspace"]>/<safe ticket id>/tree` (same id sanitising as `factory/followups.py` `_safe_id`). Return that path when `payload` has a string `workspace` and the directory exists and is a git worktree, else None. Never return a path outside the workspace.
(2) `factory/stations/wiring.py`: `wiring_handler(root: Path | None = None, run_ringer=None, run=subprocess.run, now_fn=...) -> StationHandler` returning `StationResult`. Payload keys: `plan` (the fix plan dict, required), `workspace` (required, a directory outside the repository for Ringer files and trees), `ringer` (path to ringer.py; default `~/dev/ringer/ringer.py` expanded), plus the ticket's `failing_turns`. Behaviour, in order, stopping at the first failure: (a) load the default story package (`DEFAULT_ROOT` from `factory/checks/gap_delta.py`, resolved under `root`) and run `lint_plan`; any problems -> `StationResult(False, "wiring", <one problem per line>)` and nothing else is created; (b) clear any earlier work for this ticket id (remove its tree with `git worktree remove --force` and prune; remove its manifest and out directory) so a rerun is idempotent; (c) build the Ringer manifest with `factory.manifests.build_manifest` and write it to `<workspace>/<safe id>/manifest.json`: run name `factory-wiring-<safe id>`, workdir `<workspace>/<safe id>/ringer`, ONE task `wire` (task_type code-fix, engine codex, effort medium, 2 attempts) that owns exactly the plan scene's source files, `<story root>/source/scenes/<scene>.yaml` and `<story root>/source/scenes/<scene>.match.yaml` (only the ones that exist). The task spec is a self-contained brief written by a pure function `wiring_spec(plan, story_root_relative)` (so tests can read it): role and boundary, the plan's reason and its exact fields as a JSON block, and HOW: for `add_pacing_beat` use the story CLI (`.venv/bin/python -m storygame.story_cli new beat <scene> <id> --say '<text>'` then `story set beat:<id>.at_turn`, `.when`, `.sets`, `.trailing`, and the verbatim flag, reading `storygame/story_cmds/cmd_new.py` and `cmd_set.py` for the exact address forms; fall back to the smallest hand edit only if the CLI refuses a field), for `set_text` use `story set <address> <text>`; the text must be copied character for character from the plan, never re-worded; never edit tests or any other file; never touch other records. The plan's text and fields are given to the worker ONLY through a JSON file the handler writes at `<workspace>/<safe id>/plan.json` (the spec embeds the same JSON block) and the CHECK reads that same file with Python, so no story text is ever pasted into a shell command. The check (through `TaskSpec.check_extra` or a custom check, whichever `build_manifest` allows; it must pass `lint_check`) proves: only the owned files changed; the compiled package (`load_story_package`) contains the beat with the exact id, `at_turn`, `trailing`, `when`, `sets` and text (or the claim has the exact new text) by reading plan.json; `story fmt --check` passes; `storygame.story_source.check_source_tree` returns no diagnostics; `tests/test_game_path_completion.py` passes (it is parametrised over every pacing event, so it covers a new beat); a time budget of 300 s for the check's tests (use `date +%s`, never `$SECONDS`). The task exports its patch to `<workspace>/<safe id>/ringer/<key>.patch` via the manifest check (see how `build_check` writes it); the patch lives outside the worktree. (d) Run Ringer through the injectable `run_ringer(manifest_path, ringer_path) -> subprocess.CompletedProcess`-like (default: `subprocess.run([sys.executable or python3, ringer_path, "run", manifest_path, "--identity", "factory", "--no-dashboard"], ...)` with a generous timeout; never invoked by tests). Non-zero exit, or a missing or empty patch -> `StationResult(False, "wiring", <tail of output>)`. (e) Create the ticket tree: `git worktree add --detach <workspace>/<safe id>/tree HEAD` in `root`, symlink `.venv` into it, `git apply` the patch there; a failed apply -> StationResult(False, ...). (f) Success -> `StationResult(True, "wiring", "tree=<path> patch=<path>")`. Add an optional `guard_call` argument: a callable `(fn) -> result` the real factory will use to wrap the Ringer run in the spend guard; default None runs `fn` directly.
(3) `factory/stations/free_gates.py` and `factory/stations/prompt_snapshot.py`: when `ticket_tree(payload, ticket.id, repository_root)` returns a path, use that tree as the repository root for EVERY command and path in that handler (source tree check, story root, gap delta, carry matrix, Ruff, pytest, prompt capture and diff), and when it returns None behave exactly as today. Keep every existing test passing unchanged; add tests for both branches.
(4) `factory/stations/__init__.py`: register `Station.WIRING: wiring_handler(root)` in `build_handlers`; keep the comment about unbuilt stations accurate (stations 0, 1, 3 and 9 remain).

TESTS. New `tests/test_factory_wiring.py` (hermetic; no model, no network, no real Ringer; each test under a few seconds, the whole file under 20 s): `wiring_spec` and the manifest for each kind (owned files, the JSON block, no story text in the check script, `lint_check` clean); a lint-failing plan stops at (a) and creates nothing; the full happy path for BOTH kinds in a temporary git repository (git init, copy `data/stories/continuity-initiative` into it, commit) with a stub `run_ringer` that applies the change with the real story CLI to a scratch copy and writes the patch to the path the handler expects, then the handler creates the tree, applies the patch and returns passed, and `ticket_tree` finds it; a stub that exits non-zero fails the station; an empty patch fails; a patch that does not apply fails; a rerun on the same ticket id succeeds and leaves exactly one tree; `ticket_tree` returns None for a missing workspace key, a missing directory and a path outside the workspace. Extend `tests/test_factory_stations.py` and `tests/test_factory_prompt_snapshot.py` with the tree-branch tests. Update `tests/shard_durations.json` for the new test file by running `.venv/bin/python scripts/regen_shard_durations.py --missing-only` once at the end (read its usage first; keep the diff to the one new entry).

HARD LIMITS. Edit only the owned files: @OWNED@. Never edit `factory/config/`, `factory/checks/`, `factory/guard.py`, `factory/limits.py`, `factory/manifests.py`, `factory/line.py`, `factory/tickets.py`, story data, `storygame/` or any other test. The module must be story-agnostic (no character names, fact ids or scene ids in `wiring.py`/`tree.py`; the story root comes from `DEFAULT_ROOT`). No model client, no network. Write NOTES_18B2.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vxF @ALLOW_ARGS@ || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
n=$(git diff --cached -U0 -- tests/shard_durations.json | grep -E '^[+-][^+-]' | grep -vc 'test_factory_wiring' || true)
[ "${n:-0}" -le 2 ] || { echo "shard_durations diff is more than the one new entry"; exit 1; }
if grep -n -i -E "michelle|kristin|memory_card|laptop|continuity" factory/stations/wiring.py factory/stations/tree.py; then echo "story-specific word in wiring.py or tree.py"; exit 1; fi
if grep -n -i -E "import (openai|anthropic|requests|httpx)|from (openai|anthropic|requests|httpx)|urllib.request" factory/stations/wiring.py factory/stations/tree.py; then echo "no model client or network in the wiring modules"; exit 1; fi
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_wiring.py tests/test_factory_stations.py tests/test_factory_prompt_snapshot.py tests/test_factory_fix_plan.py tests/test_factory_line.py tests/test_factory_followups.py tests/test_factory_manifests.py tests/test_factory_frozen.py
took=$(( $(date +%s) - start ))
echo "factory station tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || { echo "over the 120 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python scripts/quick_suite.py
took=$(( $(date +%s) - start ))
echo "quick suite took $took s (baseline 157 s, budget 450 s)"
[ "$took" -le 450 ] || { echo "quick suite over the 450 s budget"; exit 1; }
.venv/bin/python -m ruff check factory/stations tests/test_factory_wiring.py tests/test_factory_stations.py tests/test_factory_prompt_snapshot.py
.venv/bin/python -m ruff format --check factory/stations tests/test_factory_wiring.py tests/test_factory_stations.py tests/test_factory_prompt_snapshot.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/wiring.patch"
test -s "$WORK/out/wiring.patch"
"""


def build() -> dict:
    allow_args = " ".join(f"-e {path}" for path in OWNED)

    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_ARGS@", allow_args)
        )

    return {
        "run_name": "factory-wiring-station",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "wiring-station",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "wiring_handler lints a plan, builds a one-task Ringer manifest whose check reads plan.json, creates a per-ticket worktree with the patch applied, and stations 5 and 6 use that tree when the ticket has one; tests hermetic (stub Ringer); module story-agnostic; quick suite green; ruff clean.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18b2-wiring-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
