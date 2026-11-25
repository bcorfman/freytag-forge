# ruff: noqa: E501
"""Gate-proving ladder R1a: measure the two live stuck measures against the frozen outcome-contract examples. No model.

Gate 18 is the hosted stuck heuristic (frontend/e2e/blind-player.js analyseRun, read by the station 7 live gate).
Gate 20 is the probe stuck measure (factory/stations/probe.py summarize_arm, read by the station 12 keep rule).
The 27 frozen examples in tests/fixtures/outcome_contract/cases.json carry the right answer by construction.
Measurement only: no repository file changes; scripts and results are exported to WORK/out.
"""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/gates-r1"
REPO = "/home/bcorfman/dev/freytag-forge"
OUTDIR = "tools_gates_r1"

MAPPING = (
    "TURN MAPPING (use exactly this; the same mapping for both gates; record it in the report). For each case in cases.json, walk run.turns in order and keep two running values: "
    "`fired` (list of every non-null matched_candidate so far, in order) and `left` (false until a turn whose transition_cause is not 'none'). For each fixture turn t build a hosted turn: "
    "first append t.matched_candidate to fired if it is a string; then if t.transition_cause is a string other than 'none' set left = true; then "
    "{turn: t.turn, input: t.input, text: t.text or '', profile: 'canonical', rejected: t.rejected === true or t.outcome === 'rejected', game_break: t.game_break ?? null, "
    "question_turn: (t.outcome !== 'committed' and not rejected and game_break is null), story_complete: t.story_complete === true, grounding_ids: t.grounding_ids or [], "
    "state: {scene_id: left ? 'NEXT' : case.scene.id, fired_storylet_ids: copy of fired, fired_pacing_event_ids: ['pe_' + turn number for every turn so far, this one included, whose pressure_event is true'], story_complete: t.story_complete === true}}. "
    "Rejected turns keep state (analyseRun filters them itself). Affordances (analyseRun's firstStep; `later` stays []): one item per distinct grounding id starting with 'g_' anywhere in the case, "
    "{entity_id: id, name: id without the 'g_' prefix}. sceneEntry = {scene_id: case.scene.id}. Call analyseRun({sceneEntry, turns, firstStep: affordances}). "
    "For gate 20 build one bench run per case: {status: 'ok', completed: true, turns: [...]} where each turn is {turn, rejected (as above), game_break (as above), grounding_ids (as above), "
    'selected_knowledge_ids: [matched_candidate] if it is a string else [], left_scene: true only on the first turn where left became true}. Write it as {"runs": [run]} to a temp file and call '
    "factory.stations.probe.summarize_arm([path]). Gate 20 reports counts only; ALSO compute its per-turn flags by applying its rule as written in summarize_arm (not rejected, no selected ids, no grounding id new versus all earlier turns) and assert your per-turn count equals summarize_arm's stuck_turns."
)

TRUTH = (
    "GROUND TRUTH per case: if case.expected has the key confirmed_stuck, the expected stuck turns are that list and the unresolved turns are case.expected.unresolved (or [] if absent); "
    "else if case.expected.status is 'healthy' or 'flagged', expected stuck = [] and unresolved = []; otherwise the case has no per-turn truth and is listed as 'no_truth' (still run both gates and record their flags). "
    "Per case and per gate compute: flagged (sorted turn numbers), false_blocks = flagged minus expected minus unresolved, misses = expected minus flagged, and run_verdict_wrong = (flagged non-empty) != (expected non-empty) "
    "(this is what the live gate's stuck == 0 rule would get wrong for the whole run). Turns in unresolved never count either way."
)

SPEC = (
    "You are a measurement engineer for a story game's quality gates. Your current working directory IS a git worktree of /home/bcorfman/dev/freytag-forge (detached at HEAD). "
    f"NEVER modify, add or delete any tracked file; create files ONLY inside a new directory ./{OUTDIR}/ . NEVER git commit, never touch /home/bcorfman/dev/freytag-forge itself, never run `uv`, "
    "NEVER call a model (not claude, not codex), never use the network, never run `python -m bench run`. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv . "
    "Python environment: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp` and use `.venv/bin/python`. Node is on PATH (v26).\n\n"
    "GOAL. Measure how often two existing stuck detectors block good play or miss real stuck turns, on 27 frozen examples whose right answers are known by construction. "
    "Gate 18 = `analyseRun` exported by frontend/e2e/blind-player.js (its `stuck_turns` output; the live playtest gate fails a run when any turn is stuck). "
    "Gate 20 = `summarize_arm` in factory/stations/probe.py (its `stuck_turns` count; the probe keep rule reads it). The examples: tests/fixtures/outcome_contract/cases.json "
    "(fields documented in tests/fixtures/outcome_contract/README.md). Do NOT change either gate; you are measuring them as they are.\n\n"
    + MAPPING
    + "\n\n"
    + TRUTH
    + "\n\n"
    f"DELIVERABLES, all inside ./{OUTDIR}/ : (1) measure_gate18.mjs: a Node ES module that imports analyseRun from ../frontend/e2e/blind-player.js, applies the mapping and writes gate18.json. "
    "(2) measure_gate20.py: applies the mapping, calls summarize_arm, writes gate20.json. (3) combine.py: reads both and writes results.json and report.md. "
    'gate18.json and gate20.json: {"gate": "18" or "20", "cases": {case_id: {"flagged": [...], "expected": [...] or null, "unresolved": [...], "false_blocks": [...], "misses": [...], "run_verdict_wrong": bool or null}}} with all 27 case ids (null fields for no_truth cases). '
    'results.json: {"cases_total": 27, "cases_with_truth": n, "gates": {"18": {...}, "20": {...}}} where each gate has false_block_turns, missed_turns, runs_wrongly_blocked (expected empty, flagged non-empty), '
    "runs_wrongly_passed (expected non-empty, flagged empty), and lists of the case ids behind each. report.md: a short plain-English report: the mapping used, a table per gate, which named defect each wrong case shows "
    "(M2: a futile command that names an object evades the hosted flag; M3: a successful world action that reveals nothing is flagged; M4: a timed reveal masks a futile action), and anything in the mapping you had to interpret. "
    "Run: `node ./"
    + OUTDIR
    + "/measure_gate18.mjs && .venv/bin/python ./"
    + OUTDIR
    + "/measure_gate20.py && .venv/bin/python ./"
    + OUTDIR
    + "/combine.py` from the worktree root; it must finish in under 30 seconds. "
    "Ruff-clean Python (line length 120). Write NOTES.txt in the worktree root listing every interpretation you made."
)

CHECK = f"""set -eo pipefail
WORK={WORK}
OUT="$WORK/out"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
changed=$(git status --porcelain --untracked-files=all | grep -vE '^\\?\\? ({OUTDIR}/|NOTES\\.txt$|\\.venv$)' || true)
[ -z "$changed" ] || {{ echo "tracked files changed or stray files: $changed"; exit 1; }}
start=$(date +%s)
node ./{OUTDIR}/measure_gate18.mjs
.venv/bin/python ./{OUTDIR}/measure_gate20.py
.venv/bin/python ./{OUTDIR}/combine.py
took=$(( $(date +%s) - start ))
echo "measurement took $took s (budget 30 s)"
[ "$took" -le 30 ] || {{ echo "over the 30 s budget"; exit 1; }}
.venv/bin/python -m ruff check ./{OUTDIR}/*.py
.venv/bin/python -m ruff format --check ./{OUTDIR}/*.py
.venv/bin/python - <<'PYV'
import json
from pathlib import Path
d = Path("{OUTDIR}")
cases = json.loads(Path("tests/fixtures/outcome_contract/cases.json").read_text())
ids = {{c["id"] for c in cases}}
g18 = json.loads((d / "gate18.json").read_text())["cases"]
g20 = json.loads((d / "gate20.json").read_text())["cases"]
for name, g in (("18", g18), ("20", g20)):
    assert set(g) == ids, f"gate {{name}}: case ids differ: missing {{sorted(ids - set(g))}} extra {{sorted(set(g) - ids)}}"
# Known by hand (verified 2026-11-23 against analyseRun with this mapping): M3 and M2.
w = g18["world_action_without_reveal"]
assert w["flagged"] == [1, 2] and w["false_blocks"] == [1, 2] and w["run_verdict_wrong"] is True, f"gate 18 world_action_without_reveal: {{w}}"
f = g18["futile_named_object_repeated"]
assert f["flagged"] == [] and f["misses"] == [2, 3, 4] and f["run_verdict_wrong"] is True, f"gate 18 futile_named_object_repeated: {{f}}"
# Independent recomputation of gate 20's per-turn rule.
for c in cases:
    earlier, flags = set(), []
    for t in c["run"]["turns"]:
        g = {{x for x in (t.get("grounding_ids") or []) if isinstance(x, str)}}
        rejected = t.get("rejected") is True or t.get("outcome") == "rejected"
        sel = [t["matched_candidate"]] if isinstance(t.get("matched_candidate"), str) else []
        if not rejected and not sel and not (g - earlier):
            flags.append(t["turn"])
        earlier |= g
    assert g20[c["id"]]["flagged"] == flags, f"gate 20 {{c['id']}}: worker {{g20[c['id']]['flagged']}} vs rule {{flags}}"
# Internal consistency of derived fields.
for name, g in (("18", g18), ("20", g20)):
    for cid, r in g.items():
        if r["expected"] is None:
            continue
        fl, ex, un = set(r["flagged"]), set(r["expected"]), set(r["unresolved"])
        assert set(r["false_blocks"]) == fl - ex - un, f"gate {{name}} {{cid}} false_blocks"
        assert set(r["misses"]) == ex - fl, f"gate {{name}} {{cid}} misses"
        assert r["run_verdict_wrong"] == (bool(fl) != bool(ex)), f"gate {{name}} {{cid}} run_verdict_wrong"
res = json.loads((d / "results.json").read_text())
assert res["cases_total"] == 27 and set(res["gates"]) == {{"18", "20"}}, res.keys()
rep = (d / "report.md").read_text().lower()
for word in ("mapping", "m2", "m3", "gate 18", "gate 20"):
    assert word in rep, f"report.md lacks {{word!r}}"
print("r1a checks ok")
PYV
cp ./{OUTDIR}/* "$OUT"/
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
ls -l "$OUT"
"""

manifest = {
    "run_name": "gate-ladder-r1",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "r1a-stuck-gates",
            "task_type": "probe",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "spec": SPEC,
            "check": CHECK,
            "max_attempts": 2,
            "ownership": [f"{OUTDIR}/measure_gate18.mjs", f"{OUTDIR}/measure_gate20.py", f"{OUTDIR}/combine.py"],
            "expect_files": [],
            "timeout_s": 1500,
            "check_timeout_s": 180,
            "verified": "both stuck gates are run on all 27 frozen examples; two documented defects reproduce; gate 20 matches an independent recomputation; results and report exported",
        }
    ],
}

out = Path(__file__).with_name("r1a-stuck-gates-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
