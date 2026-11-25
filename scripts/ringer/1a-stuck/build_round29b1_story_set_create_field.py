# ruff: noqa: E501
"""Round 29b1: `story set` may create a missing field on an existing record (round 29b was blocked: the CLI could not add
`delivers` to a beat). The source check still rejects unknown keys and restores the bytes. Free, no model."""

import json
from pathlib import Path

import build_round21b_evidence_cap_and_spend_cap as b

b.WORK = "/home/bcorfman/dev/ringer-work/factory-29"
PY = ".venv/bin/python"
OWNED = ["storygame/story_cmds/cmd_set.py", "tests/story_source/test_cli_set.py"]
OWNED_RE = "|".join(p.replace(".", r"\.") for p in OWNED)

SETUP = f"""set -eo pipefail
WORK={b.WORK}
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {b.REPO}/.venv .venv
git reset -q
"""

SPEC = b.COMMON + (
    "You may edit ONLY: storygame/story_cmds/cmd_set.py and tests/story_source/test_cli_set.py. Nothing else.\n\n"
    "PROBLEM (reproduced). `python -m storygame.story_cli set beat:<id>.delivers '[k_x]'` fails with 'unknown address or missing field' when the beat has no `delivers` key yet, "
    "because `_walk` in storygame/story_cmds/cmd_set.py raises `_AddressError` whenever the LAST field of the address is absent from its record. `delivers` is an optional beat key (the L1 source check accepts it). "
    "The project rule is that story source is edited only by the story CLI, and 'when the CLI cannot make an edit, add the missing command'. So the CLI must be able to create a missing optional field.\n\n"
    "CHANGE. In replacement mode only (a `yaml_value` argument; NOT --add/--drop), when every earlier segment of the address resolves to an existing dict record and only the LAST segment (a plain name with no `[index]` selector) is absent from that dict, `set` creates the key with the parsed YAML value. "
    "Implement it with a small `missing` marker on `_Location` (or an equivalent), keeping `value` safe to read only when present. Everything else is unchanged: `--add` and `--drop` on a missing field still exit 2 with the 'unknown address or missing field' message; an address whose record or earlier segment does not exist still exits 2; "
    "the `_refusal` rules (frozen ids, generated entry facts, lock files) still apply to a created field; and the existing check-and-restore step stays the safety net: after writing, run the existing diagnostics and, if the source check or compile reports a problem, restore the original bytes and exit 1 (that is what rejects a misspelled new key, because the L1 check rejects unknown keys). "
    "Use only the project's YAML loader (`load_document`, `dumps_document`) so comments and formatting survive. Do not touch other commands.\n\n"
    "TESTS, WRITE THEM FIRST in tests/story_source/test_cli_set.py (follow the file's helpers `_copy_source` and the monkeypatch.chdir pattern; read the existing tests first; hermetic): "
    "(1) on a copy of the real source, `main(['set', 'beat:inspection_window_2a.delivers', '[k_inspection_window_missed]'])` returns 0, the scene file's beat now has that list (load with the project's loader and assert), `main(['fmt', '--check'])` returns 0 afterwards, and a neighbouring comment in the file survives (insert a `# keep this comment` line the way the first test does); "
    "(2) a misspelled new key, `set beat:inspection_window_2a.delivrs '[k_x]'`, returns 1 and the scene file bytes are identical to before; "
    "(3) `set beat:inspection_window_2a.delivers --add k_x` on a beat with no `delivers` returns 2 and leaves bytes unchanged; "
    "(4) creating a field under a record that does not exist (`beat:no_such_beat.delivers`) still returns 2 with 'unknown address'; "
    "(5) after (1), a second `set beat:inspection_window_2a.delivers '[k_inspection_window_missed]'` (field now present) still works as a replacement and returns 0; "
    "(6) a frozen id field is still refused: `set beat:inspection_window_2a.id x` returns 1. "
    "Existing tests in that file must keep passing; run the whole file and tests/story_source."
)

CHECK = (
    SETUP
    + f"""git add -A -- storygame tests
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({OWNED_RE})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
out=$({PY} -m pytest -q -p no:cacheprovider -rs -n 4 tests/story_source tests/test_pacing_links.py 2>&1) || {{ echo "$out"; exit 1; }}
echo "$out" | tail -6
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 300 s)"
[ "$took" -le 300 ] || {{ echo "over the 300 s budget"; exit 1; }}
case "$out" in *skipped*) echo "tests were skipped"; exit 1;; esac
grep -c "def test_" tests/story_source/test_cli_set.py | {PY} -c "import sys; n=int(sys.stdin.read()); assert n >= 11, n"
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
[ -z "$PYFILES" ] || {PY} -m ruff check $PYFILES
[ -z "$PYFILES" ] || {PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/story-set-create.patch"
test -s "$WORK/out/story-set-create.patch"
"""
)

manifest = {
    "run_name": "factory-29b1-story-set-create-field",
    "workdir": b.WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": b.REPO,
    "tasks": [
        {
            "key": "story-set-create",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 500,
            "ownership": OWNED,
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "story set creates a missing field on an existing record; misspelled keys are rolled back; --add on a missing field and unknown records still exit 2.",
        }
    ],
}
Path(__file__).with_name("round29b1-story-set-create-field-manifest.json").write_text(
    json.dumps(manifest, indent=2) + "\n"
)
