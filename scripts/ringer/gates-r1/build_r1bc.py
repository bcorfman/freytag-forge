# ruff: noqa: E501
"""Gate-proving ladder R1b and R1c. No model, no network, no repository change.

R1b: how often the runtime narration validators (gate 16) reject narration, from saved bench and hosted records.
R1c: how many test files pin real-story behaviour (gate 11), by a static parse against the compiled package's ids.
"""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/gates-r1"
REPO = "/home/bcorfman/dev/freytag-forge"

COMMON = (
    "You are a measurement engineer for a story game's quality gates. Your current working directory IS a git worktree of /home/bcorfman/dev/freytag-forge (detached at HEAD). "
    "NEVER modify, add or delete any tracked file; create files ONLY inside the new directory named below. NEVER git commit, never touch /home/bcorfman/dev/freytag-forge itself, "
    "never write anywhere under /home/bcorfman/dev/ringer-work except reading, never run `uv`, NEVER call a model (not claude, not codex), never use the network, never run `python -m bench run`, never run pytest. "
    "FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv . Python: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp` and `.venv/bin/python`. "
    "Ruff-clean Python (line length 120). Write NOTES.txt in the worktree root listing every interpretation you made. Measurement only: do not fix anything you find; report it.\n\n"
)

CODES = [
    "canonical_fact_mutation",
    "dialogue_grounding_not_sayable",
    "dialogue_speaker_missing",
    "disclosure_guard_leak",
    "embellishment_diverged",
    "embellishment_malformed",
    "embellishment_rejected",
    "inactive_storylet_event",
    "ineligible_selection",
    "invalid_grounding_reference",
    "invalid_storylet_realization",
    "invalid_transition",
    "invisible_grounding_reference",
    "missing_knowledge_content",
    "missing_package_source",
    "multiple_knowledge_selection",
    "narration_known_term_leak",
    "observation_diverged",
    "observation_preview_failed",
    "observation_unverified",
    "protected_knowledge_mutation",
    "protected_narration_leak",
    "selection_source_mismatch",
    "storylet_operation_mismatch",
    "unavailable_storylet",
    "uncited_knowledge",
    "ungrounded_selection",
    "unknown_dialogue_speaker",
    "unknown_grounding_reference",
    "unsatisfied_transition_triggers",
    "world_fact_mutation",
]

R1B_DIR = "tools_gates_r1b"
R1B_SPEC = COMMON + (
    f"Create files ONLY in ./{R1B_DIR}/ .\n\n"
    "GOAL. Measure how often the game's runtime narration validators reject narration, using records already saved on disk. When the narration model's reply fails a validator, the engine "
    "retries inside the same turn (a 'guard retry'); if the retries also fail, the player sees a rejected turn. The station 7 live gate fails a whole scene if any replicate has one player-visible rejected turn. "
    "Read bench/core.py around lines 990 to 1090 and 1320 to 1345 to see how bench turn records store `guard_retry_used` and `guard_rejections` per turn; read the shape of one rejection entry from the code and from real files.\n\n"
    "SOURCES. (a) Every *.json file under /home/bcorfman/dev/ringer-work (recursively) and /home/bcorfman/dev/freytag-forge/artifacts that contains bench turn records: dicts with a `turns` list whose items "
    "carry the key `guard_rejections`. Skip Ringer manifests and anything else. Deduplicate by file sha256, and inside the kept files skip a run whose turns are byte-identical (after json.dumps with sort_keys) to an already counted run. "
    "(b) The hosted blind-player reports /home/bcorfman/dev/ringer-work/qual-20261122/reports/*.json: they have `replicates[].turns[]` with `rejected` (bool) and `rejection` (text); they have no in-turn retry data. "
    "Do not load any file over 200 MB; list it as skipped.\n\n"
    "WHAT TO COMPUTE. Per source file: path, sha256, file modification date, number of runs and turns counted, and any commit, story or scene field you can find. Totals: turns; turns with at least one guard rejection; "
    "guard rejections by code (the code field of each rejection entry; if an entry has no code, use its message's first 60 characters prefixed 'message:'); player-visible rejected turns by code or message; "
    "the largest number of guard rejections in one turn; per code, the share of its retries that were followed by an accepted turn. "
    f"Mark each code as 'current' if it is in this list of 31 codes the runtime raises today, else 'legacy_or_other': {', '.join(CODES)}. "
    "Say whether the rejected narration text itself is recorded, and under which field. Then write a sample of up to 40 rejections, spread across codes (at most 4 per code), each with source path, run index, turn, "
    "code, player input, the rejected narration text excerpt (up to 600 characters, if recorded) and the accepted narration excerpt of the same turn (up to 600 characters, if any). The sample is for a later true/false "
    "adjudication; do not judge them yourself.\n\n"
    f"DELIVERABLES in ./{R1B_DIR}/ : measure.py (does all of the above, run as `.venv/bin/python ./{R1B_DIR}/measure.py` from the worktree root, under 120 seconds), sources.json (list of per-source objects with keys path, sha256, runs, turns, skipped_reason or null), "
    "totals.json (keys turns, turns_with_guard_rejection, guard_rejections_by_code {code: count}, visible_rejections_by_code {code: count}, max_guard_rejections_in_one_turn, recovered_share_by_code {code: float}, code_status {code: 'current' or 'legacy_or_other'}, "
    "rejected_text_field (string or null)), sample.json (list), and report.md: a short plain-English summary: data covered and its dates, the overall rates, the top codes, legacy codes, gaps in the data, and what a true/false adjudication would need."
)
R1B_CHECK = f"""set -eo pipefail
WORK={WORK}
OUT="$WORK/out/r1b"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
changed=$(git status --porcelain --untracked-files=all | grep -vE '^\\?\\? ({R1B_DIR}/|NOTES\\.txt$|\\.venv$)' || true)
[ -z "$changed" ] || {{ echo "tracked files changed or stray files: $changed"; exit 1; }}
start=$(date +%s)
.venv/bin/python ./{R1B_DIR}/measure.py
took=$(( $(date +%s) - start ))
echo "measurement took $took s (budget 120 s)"
[ "$took" -le 120 ] || {{ echo "over the 120 s budget"; exit 1; }}
.venv/bin/python -m ruff check ./{R1B_DIR}/*.py
.venv/bin/python -m ruff format --check ./{R1B_DIR}/*.py
.venv/bin/python - <<'PYV'
import hashlib, json
from pathlib import Path
d = Path("{R1B_DIR}")
sources = json.loads((d / "sources.json").read_text())
totals = json.loads((d / "totals.json").read_text())
sample = json.loads((d / "sample.json").read_text())
kept = [s for s in sources if not s.get("skipped_reason")]
assert kept, "no sources counted"
for s in kept:
    p = Path(s["path"])
    assert p.exists(), f"source does not exist: {{p}}"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == s["sha256"], f"sha256 mismatch: {{p}}"
# Independent count of bench turns carrying guard_rejections, over the kept bench sources.
def walk(o, acc):
    if isinstance(o, dict):
        t = o.get("turns")
        if isinstance(t, list) and t and all(isinstance(x, dict) for x in t) and any("guard_rejections" in x for x in t):
            rej = o.get("rejected_turns")
            acc.append((t, [x for x in rej if isinstance(x, dict)] if isinstance(rej, list) else []))
            return
        for v in o.values():
            walk(v, acc)
    elif isinstance(o, list):
        for v in o:
            walk(v, acc)
seen, n_turns_with, n_rej = set(), 0, 0
for s in kept:
    if "/qual-20261122/reports/" in s["path"]:
        continue
    acc = []
    walk(json.loads(Path(s["path"]).read_text()), acc)
    for turns, rejected in acc:
        key = json.dumps(turns, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        for t in turns + rejected:
            g = t.get("guard_rejections") or []
            if g:
                n_turns_with += 1
                n_rej += len(g)
print("independent: turns with guard rejection", n_turns_with, "guard rejections", n_rej)
assert totals["turns_with_guard_rejection"] == n_turns_with, f"turns_with_guard_rejection {{totals['turns_with_guard_rejection']}} vs independent {{n_turns_with}}"
assert sum(totals["guard_rejections_by_code"].values()) == n_rej, f"guard rejections {{sum(totals['guard_rejections_by_code'].values())}} vs independent {{n_rej}}"
assert set(totals["code_status"]) >= set(totals["guard_rejections_by_code"]), "code_status missing codes"
assert len(sample) <= 40, "sample too large"
rep = (d / "report.md").read_text().lower()
for word in ("rate", "code", "legacy"):
    assert word in rep, f"report.md lacks {{word!r}}"
print("r1b checks ok:", len(kept), "sources,", totals["turns"], "turns")
PYV
cp ./{R1B_DIR}/* "$OUT"/
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
ls -l "$OUT"
"""

R1C_DIR = "tools_gates_r1c"
R1C_SPEC = COMMON + (
    f"Create files ONLY in ./{R1C_DIR}/ .\n\n"
    "GOAL. The repository's full test suite (tests/test_*.py, about 400 files) runs in CI before any story change can merge, so a test that asserts on the real story's current content blocks a correct story change. "
    "Classify every test file by how it depends on the real story (data/stories/continuity-initiative), using a static parse. Do not run any test.\n\n"
    "STORY IDS. Load the compiled package: `from storygame.story_package.loader import load_story_package; p = load_story_package(Path('data/stories/continuity-initiative'))`. Collect the set of real-story ids: "
    "scene ids (p.scenes[*].metadata.scene_id), storylet ids (p.storylet_routes.storylets[*].id), knowledge ids (p.knowledge.knowledge[*].id), fact ids (p.fact_ids), entity ids (p.world.locations, npcs, groups, items, each .id), "
    "pacing event ids (p.pacing.events[*].id), transition ids (p.pacing.transitions[*].id), delivery fact ids (p.deliveries[*].fact_id). Explore the package object if a field name differs and say so in NOTES.txt. "
    "Split them into LONG ids (6 or more characters) and SHORT ids (scene ids such as '1A', and any other id under 6 characters).\n\n"
    "CLASSIFY each tests/test_*.py by parsing it with `ast` (a file that fails to parse is class 'unparsed'):\n"
    "- 'pins_story': a string constant that equals a LONG id, or a SHORT id, or contains a LONG id as a whole word, appears inside an `assert` statement, inside the arguments of a `pytest.mark.parametrize` decorator, "
    "or inside a module-level or function-level assignment whose target name is later read inside an assert in the same file.\n"
    "- 'loads_story': not pins_story, but the file mentions the story in any way: a string constant containing 'continuity-initiative' or any LONG id, or it calls load_story_package / imports a module-level PACKAGE or DEFAULT_ROOT from storygame or from another test.\n"
    "- 'story_free': neither.\n"
    "Per file record: class, count of asserts that reference story ids, the first 5 matched ids, and whether it is marked nightly (a `nightly` mark anywhere in the file).\n\n"
    f"DELIVERABLES in ./{R1C_DIR}/ : classify.py (run as `.venv/bin/python ./{R1C_DIR}/classify.py` from the worktree root, under 60 seconds), files.json ({{path: {{class, story_asserts, ids, nightly}}}} for every tests/test_*.py), "
    "totals.json ({{files, pins_story, loads_story, story_free, unparsed, pins_story_not_nightly, story_ids_long, story_ids_short}}), and report.md: a short plain-English summary with the counts, the 20 files with the most story-id asserts, "
    "which story records are pinned most often, and the limits of a static parse (what it over- or under-counts)."
)
GREP_RE = "SL-[0-9][A-C]-|k_sl_[0-9][a-c]_|continuity-initiative"
COPIED = ["tests/test_factory_wiring.py", "tests/test_2a_supervisor_impatience.py", "tests/test_3c_recall_live.py"]
R1C_CHECK = f"""set -eo pipefail
WORK={WORK}
OUT="$WORK/out/r1c"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
changed=$(git status --porcelain --untracked-files=all | grep -vE '^\\?\\? ({R1C_DIR}/|NOTES\\.txt$|\\.venv$)' || true)
[ -z "$changed" ] || {{ echo "tracked files changed or stray files: $changed"; exit 1; }}
start=$(date +%s)
.venv/bin/python ./{R1C_DIR}/classify.py
took=$(( $(date +%s) - start ))
echo "classification took $took s (budget 60 s)"
[ "$took" -le 60 ] || {{ echo "over the 60 s budget"; exit 1; }}
.venv/bin/python -m ruff check ./{R1C_DIR}/*.py
.venv/bin/python -m ruff format --check ./{R1C_DIR}/*.py
grep -lE '{GREP_RE}' tests/test_*.py > /tmp/r1c_grep.txt || true
echo "grep-named files: $(wc -l < /tmp/r1c_grep.txt)"
.venv/bin/python - <<'PYV'
import glob, json
from pathlib import Path
d = Path("{R1C_DIR}")
files = json.loads((d / "files.json").read_text())
totals = json.loads((d / "totals.json").read_text())
all_tests = sorted(glob.glob("tests/test_*.py"))
keys = sorted(k if k.startswith("tests/") else "tests/" + Path(k).name for k in files)
assert keys == all_tests, f"classified set differs: missing {{sorted(set(all_tests) - set(keys))[:5]}} extra {{sorted(set(keys) - set(all_tests))[:5]}}"
norm = {{(k if k.startswith("tests/") else "tests/" + Path(k).name): v for k, v in files.items()}}
classes = [v["class"] for v in norm.values()]
for c in ("pins_story", "loads_story", "story_free", "unparsed"):
    assert totals[c] == classes.count(c), f"totals[{{c}}] {{totals[c]}} vs files {{classes.count(c)}}"
assert totals["files"] == len(all_tests), "files total"
grep = [l.strip() for l in Path("/tmp/r1c_grep.txt").read_text().splitlines() if l.strip()]
free = [g for g in grep if norm[g]["class"] == "story_free"]
assert not free, f"files that name the story by grep but were classed story_free: {{free[:10]}}"
for f in {COPIED!r}:
    assert norm[f]["class"] == "pins_story", f"{{f}} copies authored story sentences but is classed {{norm[f]['class']}}"
assert totals["story_ids_long"] > 100, f"too few story ids: {{totals['story_ids_long']}}"
rep = (d / "report.md").read_text().lower()
for word in ("pins_story", "loads_story", "limit"):
    assert word in rep, f"report.md lacks {{word!r}}"
print("r1c checks ok:", {{c: classes.count(c) for c in set(classes)}})
PYV
cp ./{R1C_DIR}/* "$OUT"/
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
ls -l "$OUT"
"""


def task(key, spec, check, owned, verified, check_timeout):
    return {
        "key": key,
        "task_type": "probe",
        "engine": "codex",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "max_attempts": 2,
        "ownership": owned,
        "spec": spec,
        "check": check,
        "expect_files": [],
        "timeout_s": 1800,
        "check_timeout_s": check_timeout,
        "verified": verified,
    }


manifest = {
    "run_name": "gate-ladder-r1",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        task(
            "r1b-runtime-rejections",
            R1B_SPEC,
            R1B_CHECK,
            [f"{R1B_DIR}/measure.py"],
            "saved rejection records are counted, deduplicated, matched by an independent recount, split by code and sampled for later adjudication",
            300,
        ),
        task(
            "r1c-test-pinning",
            R1C_SPEC,
            R1C_CHECK,
            [f"{R1C_DIR}/classify.py"],
            "every test file is classed by how it depends on the real story; totals reconcile; every grep-named and copied-prose file is caught",
            180,
        ),
    ],
}

out = Path(__file__).with_name("r1bc-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
