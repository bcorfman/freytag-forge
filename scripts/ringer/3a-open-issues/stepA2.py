# ruff: noqa: E501
"""Step A leftover: offline audit of the authoritative state after the 3A->3B exit (c9) and the radio custody. Zero narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-open-issues-stepA2"

SPEC = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run`, `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the tests, see them fail for the right reason, then build.

ROLE: bench engineer. You may edit/create ONLY: bench/exit_audit.py (new) and tests/test_exit_audit.py (new).

PURPOSE: the saved bench turn records for scene 3A (bench/results/richer-3a-probe/candidate-run4/) hold only the SCOPED item map the narrator saw before the c9 exit ("Lead the prisoners upward toward the command levels."); a judge flagged c9 as a missed change because Kristin's place still reads "detention level" there. A scoped before/after map cannot show the real final location or custody. Build an offline audit that plays the nine-command script through the real engine and reads the AUTHORITATIVE world state after each command and after the exit, with no model call.

BUILD bench/exit_audit.py (importable, plus `python -m bench.exit_audit --variation bench/variations/richer-3a-d1-control.json --out REPORT.json`):
1. Reuse the helpers in bench/frozen_prompts.py (read it: `_script_inputs`, `_handoff_id`, and `_prefix_states`, which seeds the 3A entry state exactly as the live runs do through `bench.core.seeded_state_for_scene` and scripts earlier commands with each command's authored delivery). Write a similar loop of your own in bench/exit_audit.py (do not edit frozen_prompts.py): run ALL nine commands of the variation's 3A script through `RuntimeEngine`, using a scripted provider that returns, for each command, the authored delivery of the uniquely matched authored handoff (as frozen_prompts does), else a plain one-segment narration.
2. After EACH command record: the command, the engine's current scene id, whether the turn left the scene, the sorted set of true story fact ids, and the authoritative WORLD placements: for each of Kristin, Michelle, Brandon, the captives (find their world ids in data/stories/continuity-initiative/world.yaml and the 3A/3B placements in plot.md and the world model: read docs/world-model-grounding.md first), the stolen radio, and any radio-like thing the 3A script touches: their place and holder as the world model reports them. Find the correct accessors by reading storygame/runtime/world_model.py and packages/worldkeeper; do not read raw prose. State exactly which accessor you used.
3. After c9 additionally record what scene the engine entered (expected 3B) and the world placements there (where Kristin, Michelle, Brandon, the captives and the radio are, who holds the radio). Also record `radio_custody_by_command`: after every command, who holds the stolen radio (or its place), so custody changes are visible turn by turn.
4. Write REPORT.json: {{"variation", "package_hash", "commands": [...per-command records...], "exit": {{...}}, "findings": [plain sentences such as 'Kristin place after c9 is X in scene Y', 'the stolen radio is held by Z after c9'], "limits": plain sentences}}. `limits` must say that the narrator is scripted (no model item_facts), so only authored effects change the world, and that live narrator item_facts proposals are not exercised.

TESTS (first, offline, fast): the report builds from the checked-in variation bench/variations/richer-3a-d1-control.json (it points at bench/frozen/continuity-pre-3a-d1v which exists at HEAD; if the file is missing use bench/variations/richer-3a-c.json and say so); it has nine command records; the exit record names a scene different from 3A; custody-by-command has nine entries; running twice gives identical JSON; the CLI writes REPORT.json. Assert structure and internal consistency (for example, a thing recorded as held by Kristin has the holder field set), and do NOT hard-code facts you have not read from the world. Run tests/test_exit_audit.py tests/test_frozen_prompts.py tests/test_bench.py.
Then RUN the CLI and write {OUT}/exit-audit-control.json for `bench/variations/richer-3a-d1-control.json` and {OUT}/exit-audit-current.json for `bench/variations/richer-3a-d1v.json`.

FINAL MESSAGE: the findings sentences of both reports verbatim, the accessor used, and any limit.
"""

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s REPO/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in bench/exit_audit.py|tests/test_exit_audit.py) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
grep -n "urlopen(\|requests\.\|httpx\.\|openai" bench/exit_audit.py | grep -v "^[0-9]*:\s*#" && { echo "WHY: module must not touch the network"; exit 1; }
$PY -m pytest -q -p no:cacheprovider tests/test_exit_audit.py tests/test_frozen_prompts.py tests/test_bench.py > /tmp/ta2.out 2>&1; rc=$?; tail -15 /tmp/ta2.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
for n in control current; do test -s OUTDIR/exit-audit-$n.json || { echo "WHY: OUTDIR/exit-audit-$n.json missing; run the CLI"; exit 1; }; done
$PY - <<'E' || exit 1
import json
for n in ('control','current'):
    r=json.load(open(f'OUTDIR/exit-audit-{n}.json'))
    assert len(r['commands'])==9, (n,'need nine command records')
    assert r['exit'] and r['findings'] and r['limits'], (n,'exit, findings and limits required')
    assert len(r.get('radio_custody_by_command', r['exit'].get('radio_custody_by_command', [])))==9 or any('radio' in f.lower() for f in r['findings']), (n,'radio custody missing')
    assert any('scripted' in str(l).lower() for l in (r['limits'] if isinstance(r['limits'],list) else [r['limits']])), 'limits must say the narrator is scripted'
print('reports ok')
E
PYF=$(echo "$CH" | grep '\.py$')
$PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
$PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
git add bench/exit_audit.py tests/test_exit_audit.py && git diff --cached > OUTDIR/stepA2.patch && wc -l OUTDIR/stepA2.patch && git diff --cached --stat | tail -4
""".replace("OUTDIR", OUT).replace("REPO", REPO)

manifest = {
    "run_name": "3a-open-issues-stepA2",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "exit-audit",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": ["bench/exit_audit.py", "tests/test_exit_audit.py"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests added first, audit reports written for both variations, patch exported",
        }
    ],
}
Path(__file__).with_name("stepA2-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
