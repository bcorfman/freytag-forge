# ruff: noqa: E501
"""Gate-proving ladder R1e. No model, no network, no repository change.

r1e-variants-suite: meaning-preserving story variants (V), built by rule; gates 1 to 5 and the full PR suite (gate 11) run on each.
r1e-seeded-faults: the good story (G) and one seeded fault per deterministic authoring gate (B); every gate in the set runs on each.
Gates 12 to 15 are out of scope: no scene contracts exist yet, and 14 and 15 judge planned repairs, not story.
"""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/gates-r1"
REPO = "/home/bcorfman/dev/freytag-forge"
STORY = "data/stories/continuity-initiative"
R1C_FILES = "/home/bcorfman/dev/ringer-work/qual-20261122/gates/r1c/files.json"

# The machine has 16 cores and two tasks run at once. The first launch swamped it (load 32): pyproject's
# addopts give pytest `-n auto` (16), carry_matrix() defaults to a 16-process pool, and workers left earlier
# runs going in other shells. Each task gets a fixed share of cores, and its check measures the cores its
# worktree's processes actually use (CPU-time delta per 5-second window) while measure.py runs.
V_CORES = 10
F_CORES = 4


def cpu_rules(cores):
    return (
        f"CPU BUDGET (hard rule). This machine has 16 cores and another task runs beside you. Your share is {cores} cores at every moment. "
        f"So: every pytest call passes `-n {cores}` or fewer explicitly (pyproject.toml's addopts say `-n auto`, which means 16, so never rely "
        f"on the default) and sets `PYTEST_XDIST_AUTO_NUM_WORKERS={cores}` in its environment; every carry_matrix() call passes `workers=` "
        f"with at most {cores} (its default is a 16-process pool, and station 5 does not pass it); never run two heavy commands at the same "
        "time; never start a command in the background or with `&`, `nohup` or `setsid`; never add multiprocessing or process pools of your "
        "own. Wrap each long command in `timeout`, and if one is killed or interrupted, make sure none of its processes is left running "
        "(`pgrep -af python`) before you start another. While the check runs measure.py it measures the cores used by all processes whose "
        f"working directory is your worktree, averaged over 5-second windows, and fails if any window exceeds {cores + 2} cores.\n\n"
    )


CPU_PY = """import os, sys, time
root, out, limit = sys.argv[1], sys.argv[2], float(sys.argv[3])
tick = os.sysconf("SC_CLK_TCK")
tracked = {}  # pid -> cpu ticks; a pid stays tracked after it leaves the worktree (tests chdir out and back)
def sample():
    seen = {}
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            if pid not in tracked:
                cwd = os.readlink("/proc/" + pid + "/cwd")
                if cwd != root and not cwd.startswith(root + "/"):
                    continue
            parts = open("/proc/" + pid + "/stat").read().rsplit(")", 1)[1].split()
            seen[pid] = int(parts[11]) + int(parts[12])
        except OSError:
            continue
    return seen
peak, over, windows = 0.0, 0, 0
tracked, t0 = sample(), time.monotonic()
while True:
    time.sleep(5)
    cur, t1 = sample(), time.monotonic()
    # only pids seen in both samples count; a new pid's earlier CPU is not charged to this window
    used = sum(max(0, ticks - tracked[pid]) for pid, ticks in cur.items() if pid in tracked)
    cores = used / tick / (t1 - t0)
    tracked, t0 = cur, t1
    windows += 1
    peak = max(peak, cores)
    over += cores > limit
    open(out, "w").write("%.2f %d %d\\n" % (peak, over, windows))
"""


def sampler(key, limit):
    return f"""cat > /tmp/r1e_cpu_{key}.py <<'CPUPY'
{CPU_PY}CPUPY
echo "0.00 0 0" > /tmp/r1e_cpu_{key}.txt
python3 /tmp/r1e_cpu_{key}.py "$PWD" /tmp/r1e_cpu_{key}.txt {limit} &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true' EXIT
"""


def sampler_end(key, limit):
    return f"""kill $SAMPLER 2>/dev/null || true
read peak over windows < /tmp/r1e_cpu_{key}.txt
echo "cores used by this worktree: peak $peak over 5 s windows, $over of $windows windows above {limit}"
[ "$over" -eq 0 ] || {{ echo "CPU budget exceeded: peak $peak cores, limit {limit}; $over windows over"; exit 1; }}
"""


COMMON = (
    "You are a measurement engineer for a story game's quality gates. Your current working directory IS a git worktree of /home/bcorfman/dev/freytag-forge (detached at HEAD). "
    "NEVER modify any tracked file except temporarily inside the story directory "
    + STORY
    + "/ as described below, and your tools must always restore it with `git checkout -- "
    + STORY
    + "` "
    "(and remove untracked files they created there) before they exit, also on error (use try/finally). Create new files ONLY inside the new directory named below. "
    "NEVER git commit, never touch /home/bcorfman/dev/freytag-forge itself, never write anywhere under /home/bcorfman/dev/ringer-work except reading, never run `uv`, NEVER call a model (not claude, not codex), "
    "never use the network, never run `python -m bench run`, never pass --cov or --run-nightly to pytest. "
    "FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv . Python: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp` and `.venv/bin/python`. "
    "Ruff-clean Python (line length 120). Write NOTES.txt in the worktree root listing every interpretation you made. Measurement only: do not fix any gate, test or story problem you find; report it.\n\n"
    "BACKGROUND. The story is authored as YAML under "
    + STORY
    + "/source/ (story.yaml, catalog.yaml, scenes/<ID>.yaml and scenes/<ID>.match.yaml) and compiled at load time; "
    ""
    + STORY
    + "/ownership.yaml and "
    + STORY
    + "/entry/*.json (scene-entry snapshots) sit beside it. Read storygame/story_source/compiler.py, checks.py (run_layer1, run_layer2), lock.py, l2_lock.py and storygame/story_cli.py "
    "to learn how the source is checked, compiled and locked, and storygame/story_package/loader.py (load_story_package) for load validation. If editing source makes a lock or a derived file stale, regenerate it "
    "with the repository's own code exactly as the story CLI does after a write, and record that in NOTES.txt; never hand-edit a lock. "
    "Gate numbers follow .plans/qualification/gate-inventory.md (read it): 1 source layer 1, 2 source layer 2, 3 compile, 4 package load validators, 5 gap rules (a ratchet: only NEW results against the baseline block), "
    "6 carry matrix one branch (factory/checks/carry_matrix.py), 8 prompt size cap (tests/test_prompt_budget.py, tests/test_audit_budget.py), 9 leak and disclosure tests (tests/test_leak_terms_enforced.py, "
    "tests/test_disclosure_guards.py, tests/test_knowledge_leakage_matrix.py), 10 unreachable ratchet (tests/test_known_unreachable_ratchet.py), 11 the full PR test suite. "
    "factory/stations/free_gates.py shows how the factory's station 5 runs gates 1 to 6 on a candidate tree; reuse its functions where you can rather than reimplementing a gate.\n\n"
)

V_DIR = "tools_gates_r1e_variants"
V_SPEC = (
    COMMON
    + cpu_rules(V_CORES)
    + (
        f"Create files ONLY in ./{V_DIR}/ .\n\n"
        "GOAL. The full PR test suite (about 400 files) runs before any story change can merge. Measure how often it blocks a story change that keeps the story's meaning. Build meaning-preserving variants of the story source "
        "by fixed, deterministic rules (no model, no randomness without a fixed seed), and run gates 1 to 5 and the full suite on each. A gate or test that fails on a variant but passes on the original is reacting to surface "
        "wording or order, not to a defect.\n\n"
        "VARIANTS. Build exactly these four, each applied to the whole source tree:\n"
        "- V1 `layout`: rewrite every source YAML file with different but equivalent YAML formatting (for example block scalars instead of quoted strings, different line wrapping, different indentation of lists). "
        "The parsed data must be identical; key order must stay as it is if any code depends on it.\n"
        "- V2 `contractions`: in player- or narrator-facing prose only, expand contractions (it's to it is, don't to do not, let's to let us, and so on) and contract their expanded forms where a fixed table allows (it is to it's). "
        "Use one fixed table of at least 12 pairs, written in variants.py.\n"
        "- V3 `synonyms`: in the same prose fields, replace words from one fixed table of at least 15 context-safe synonym pairs (for example 'quickly' to 'fast', 'begins' to 'starts'). Never change a word that is, or is part of, "
        "an id, a declared name, a lexicon entry, a leak term, a matcher phrase or a quoted dialogue line the code matches verbatim.\n"
        "- V4 `reorder`: reorder list entries that the compiler and runtime treat as unordered (for example a scene's items or participants list), reversing each such list. Prove from the code, in NOTES.txt and report.md, "
        "that order is ignored for each list kind you reorder; do not reorder any list where order matters (pacing events, transitions, storylet priority, turn order).\n"
        "PROSE FIELDS. Decide from the code which source fields hold prose and which are matched against other text. Where the loader requires one text to contain or equal another (for example a delivery text, a must-convey "
        "phrase, a speaker line quoted elsewhere), apply the same change to every copy, or skip that field and say so. Every skipped field kind goes in report.md.\n"
        "MEANING CHECK. For each variant, compile both trees and compare the compiled packages (model_dump or equivalent). Every difference must lie in a field the rule is allowed to change (prose text for V2 and V3, "
        "list order for V4, nothing at all for V1). Write the differing field paths per variant. A variant whose compiled package differs elsewhere is a broken variant: fix the rule, do not report it as a gate result.\n\n"
        "WHAT TO RUN, per tree (the original first, then each variant applied in place to "
        + STORY
        + "/source, then restored): gate 1 and gate 2 (diagnostics by code), gate 3 (compile ok), gate 4 (load ok, error text if not), "
        "gate 5 (gap rule results, and which are new against the original), then the full PR suite: `PYTEST_XDIST_AUTO_NUM_WORKERS=10 .venv/bin/python -m pytest -q -n 10 -p no:cacheprovider --junitxml=<file> tests` (nightly tests are skipped by default). "
        "Rerun every test that failed on a variant once more on that variant (by node id) and once on the original, to separate flaky and environment failures from real variant failures. "
        f"For each real variant failure, record the test node id, its file's class from the static parse at {R1C_FILES} (pins_story, loads_story, story_free), and the first 400 characters of the assertion message, and "
        "classify the cause as one of: `pins_authored_text`, `pins_order`, `pins_layout`, `checks_a_real_rule` (the test enforces a rule the variant broke, so the variant was not meaning-preserving after all; explain), or `other`.\n\n"
        f"DELIVERABLES in ./{V_DIR}/ : variants.py (the four rules; `.venv/bin/python ./{V_DIR}/variants.py OUTDIR` writes each variant's full source tree to OUTDIR/<name>/source and is deterministic), "
        f"measure.py (`.venv/bin/python ./{V_DIR}/measure.py` from the worktree root does everything above and writes the json files below; it MUST restore the story directory at exit; `--quick` may run a small test subset "
        "for your own development, but the full run is the deliverable), meaning.json ({variant: {changed_field_paths: [...], changed_values: int, allowed: bool}}), gates.json ({tree: {L1: {code: count}, L2: {code: count}, "
        "compile_ok, load_ok, load_error, gap_results: int, gap_new: [...]}} for 'original' and each variant), suite.json ({tree: {passed, failed, errors, skipped, real_failures: [{nodeid, file_class, message, cause}], "
        "flaky: [nodeid], env_failures: [nodeid], seconds}}), and report.md: a short plain-English summary: the rules and skipped fields, per variant the gate verdicts and suite failures, the false-block rate (variants "
        "blocked by any gate or test, and failing tests per variant), which tests pin wording versus order, and what a factory repair that rewrites prose would face. "
        "TIME. The whole measure.py run must finish within 2400 seconds using your 10-core share. Run the full measurement at most once yourself; the check runs it again as the authoritative run."
    )
)
V_CHECK = (
    f"""set -eo pipefail
WORK={WORK}
OUT="$WORK/out/r1e-variants"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
dirty() {{ git status --porcelain --untracked-files=all | grep -vE '^\\?\\? ({V_DIR}/|NOTES\\.txt$|\\.venv$)' || true; }}
changed=$(dirty)
[ -z "$changed" ] || {{ echo "tracked files changed or stray files before the run: $changed"; exit 1; }}
.venv/bin/python -m ruff check ./{V_DIR}/*.py
.venv/bin/python -m ruff format --check ./{V_DIR}/*.py
rm -rf /tmp/r1e_v_a /tmp/r1e_v_b
.venv/bin/python ./{V_DIR}/variants.py /tmp/r1e_v_a
.venv/bin/python ./{V_DIR}/variants.py /tmp/r1e_v_b
diff -r /tmp/r1e_v_a /tmp/r1e_v_b > /tmp/r1e_v_diff.txt || {{ echo "variants.py is not deterministic:"; head -40 /tmp/r1e_v_diff.txt; exit 1; }}
for v in layout contractions synonyms reorder; do
  [ -d /tmp/r1e_v_a/$v/source ] || {{ echo "variant $v not written"; exit 1; }}
  diff -rq {STORY}/source /tmp/r1e_v_a/$v/source > /dev/null && {{ echo "variant $v is identical to the original source"; exit 1; }} || true
done
"""
    + sampler("v", V_CORES + 2)
    + f"""start=$(date +%s)
PYTEST_XDIST_AUTO_NUM_WORKERS={V_CORES} .venv/bin/python ./{V_DIR}/measure.py
took=$(( $(date +%s) - start ))
echo "measurement took $took s (budget 2400 s)"
[ "$took" -le 2400 ] || {{ echo "over the 2400 s budget"; exit 1; }}
"""
    + sampler_end("v", V_CORES + 2)
    + f"""changed=$(dirty)
[ -z "$changed" ] || {{ echo "measure.py did not restore the story directory: $changed"; exit 1; }}
.venv/bin/python - <<'PYV'
import json
from pathlib import Path
d = Path("{V_DIR}")
names = ["layout", "contractions", "synonyms", "reorder"]
meaning = json.loads((d / "meaning.json").read_text())
gates = json.loads((d / "gates.json").read_text())
suite = json.loads((d / "suite.json").read_text())
for n in names:
    assert n in meaning and n in gates and n in suite, f"variant {{n}} missing from a result file"
    assert meaning[n]["allowed"] is True, f"variant {{n}} changes fields outside its rule: {{meaning[n]['changed_field_paths'][:10]}}"
assert meaning["layout"]["changed_values"] == 0, "layout variant changed compiled values"
for n in ("contractions", "synonyms", "reorder"):
    assert meaning[n]["changed_values"] > 0, f"variant {{n}} changed nothing in the compiled package"
o = gates["original"]
assert o["compile_ok"] and o["load_ok"], f"original story does not compile or load: {{o.get('load_error')}}"
so = suite["original"]
assert so["passed"] > 3000, f"original suite ran too few tests: {{so['passed']}}"
files = json.loads(Path("{R1C_FILES}").read_text())
for n in names:
    s = suite[n]
    assert s["passed"] + s["failed"] + s["errors"] > 3000, f"variant {{n}} suite ran too few tests"
    for f in s["real_failures"]:
        assert f["cause"] in ("pins_authored_text", "pins_order", "pins_layout", "checks_a_real_rule", "other"), f"bad cause {{f['cause']}}"
        path = f["nodeid"].split("::")[0]
        assert Path(path).exists(), f"failure names a missing file {{path}}"
        key = path if path in files else "tests/" + Path(path).name
        if key in files:
            assert f["file_class"] == files[key]["class"], f"{{path}} file_class {{f['file_class']}} vs r1c {{files[key]['class']}}"
    assert len(s["real_failures"]) <= s["failed"] + s["errors"], f"{{n}}: more real failures than failures"
    print(n, "failed", s["failed"], "errors", s["errors"], "real", len(s["real_failures"]), "flaky", len(s["flaky"]))
rep = (d / "report.md").read_text().lower()
for word in ("skip", "false-block", "reorder", "synonym"):
    assert word in rep, f"report.md lacks {{word!r}}"
print("r1e variants checks ok")
PYV
cp -r ./{V_DIR}/* "$OUT"/
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
ls -l "$OUT"
"""
)

F_DIR = "tools_gates_r1e_faults"
F_GATES = [
    "g1_layer1",
    "g2_layer2",
    "g3_compile",
    "g4_load",
    "g5_gap_new",
    "g6_carry_branch",
    "g8_prompt_cap",
    "g9_leak_tests",
    "g10_unreachable_ratchet",
]
F_SPEC = (
    COMMON
    + cpu_rules(F_CORES)
    + (
        f"Create files ONLY in ./{F_DIR}/ .\n\n"
        "GOAL. Prove each deterministic authoring gate the way a classifier is proven: it must pass the good story (G, the story as it is at HEAD) and block its own seeded fault (B). Record which OTHER gates also fire on "
        "each fault: a fault caught by several gates shows overlap, and a fault caught by none of the intended gate shows a miss.\n\n"
        f"THE GATE BATTERY (run every gate on every tree, no fail-fast; a gate that cannot run because an earlier one broke the package records `not_reached`, not pass or fail): {', '.join(F_GATES)}. "
        "g1 and g2: diagnostics from run_layer1 and run_layer2 (blocks if any). g3: compile. g4: load_story_package. g5: gap rule results that are new against the G tree's results (blocks if any new). "
        "g6: the carry matrix one-branch check as station 5 runs it, but with `workers=4` passed to carry_matrix() (blocks on a stuck or unreachable state; record its run time). "
        "g8, g9, g10: run those test files with `PYTEST_XDIST_AUTO_NUM_WORKERS=4 .venv/bin/python -m pytest -q -n 4 -p no:cacheprovider <files>` (blocks if any test fails or errors). Record per gate: verdict (pass, block, not_reached, error), the rule codes or "
        "failing test ids, and seconds.\n\n"
        "SEEDED FAULTS. One minimal source edit per gate, each meant to trip that gate and, ideally, only that gate. Write each as a function in faults.py with a one-line label naming the failure it stands for. Use these purposes:\n"
        "- F1 (g1): a scene file gains an unknown key.\n"
        "- F2 (g2): a scene lists an item id that is declared nowhere (a dangling reference).\n"
        "- F3 (g3): a source tree that passes layers 1 and 2 but fails to compile. If you find no such edit after reading the compiler, write the function to raise NotImplementedError and explain in NOTES.txt and report.md; that is a finding.\n"
        "- F4 (g4): a fault only a load validator catches (for example a disclosure guard or narration term trap broken), chosen by reading loader.py and models.py.\n"
        "- F5 (g5): remove the only producer of a fact some later record reads (no_producer), or strand a scene exit (no_strand).\n"
        "- F6 (g6): a carry-matrix stuck state: a branch of play after which the scene's exit can no longer be reached.\n"
        "- F8 (g8): one scene's narration context pushed past the 6,500-character cap by lengthening authored prose with plausible sentences that fit the scene.\n"
        "- F9 (g9): a later-scene declared thing named in an earlier scene's narration prose.\n"
        "- F10 (g10): make a storylet or fact that journeys reach today unreachable, without breaking load.\n"
        "Each fault must be minimal (state the edit: file, field, before, after) and must leave the YAML parseable. Do not invent new gates. Apply each fault in place to "
        + STORY
        + "/source, run the battery, restore.\n\n"
        f"DELIVERABLES in ./{F_DIR}/ : faults.py (the fault functions, each taking the source directory path and editing it in place), measure.py (`.venv/bin/python ./{F_DIR}/measure.py` from the worktree root runs the battery "
        "on G and on each fault and writes the files below; it MUST restore the story directory at exit, also on error), matrix.json ({tree: {gate: {verdict, codes: [...], seconds}}} for 'G' and F1 to F10; F7 does not exist), "
        "faults.json ({fault: {intended_gate, label, edit: {file, field, before, after}}}), and report.md: a short plain-English summary: whether G passes every gate (any G block is a false block: name it), per fault the "
        "intended gate's verdict and every other gate that fired, the overlap table (which gates catch which faults), misses, the slowest gates, and what this rung cannot test (gates 12 to 15, gate 7, model gates). "
        "TIME. The whole measure.py run must finish within 2400 seconds using your 4-core share."
    )
)
F_CHECK = (
    f"""set -eo pipefail
WORK={WORK}
OUT="$WORK/out/r1e-faults"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
dirty() {{ git status --porcelain --untracked-files=all | grep -vE '^\\?\\? ({F_DIR}/|NOTES\\.txt$|\\.venv$)' || true; }}
changed=$(dirty)
[ -z "$changed" ] || {{ echo "tracked files changed or stray files before the run: $changed"; exit 1; }}
.venv/bin/python -m ruff check ./{F_DIR}/*.py
.venv/bin/python -m ruff format --check ./{F_DIR}/*.py
"""
    + sampler("f", F_CORES + 2)
    + f"""start=$(date +%s)
PYTEST_XDIST_AUTO_NUM_WORKERS={F_CORES} .venv/bin/python ./{F_DIR}/measure.py
took=$(( $(date +%s) - start ))
echo "measurement took $took s (budget 2400 s)"
[ "$took" -le 2400 ] || {{ echo "over the 2400 s budget"; exit 1; }}
"""
    + sampler_end("f", F_CORES + 2)
    + f"""changed=$(dirty)
[ -z "$changed" ] || {{ echo "measure.py did not restore the story directory: $changed"; exit 1; }}
.venv/bin/python - <<'PYV'
import json
from pathlib import Path
d = Path("{F_DIR}")
gates = {F_GATES!r}
intended = {{"F1": "g1_layer1", "F2": "g2_layer2", "F3": "g3_compile", "F4": "g4_load", "F5": "g5_gap_new", "F6": "g6_carry_branch", "F8": "g8_prompt_cap", "F9": "g9_leak_tests", "F10": "g10_unreachable_ratchet"}}
matrix = json.loads((d / "matrix.json").read_text())
faults = json.loads((d / "faults.json").read_text())
assert "G" in matrix, "no G row"
for g in gates:
    for t in ["G", *intended]:
        assert g in matrix.get(t, {{}}), f"matrix lacks {{t}}/{{g}}"
        assert matrix[t][g]["verdict"] in ("pass", "block", "not_reached", "error"), f"bad verdict {{t}}/{{g}}"
print("G:", {{g: matrix["G"][g]["verdict"] for g in gates}})
for f, g in intended.items():
    assert faults[f]["intended_gate"] == g, f"{{f}} intended gate {{faults[f]['intended_gate']}} vs {{g}}"
    row = matrix[f]
    fired = [x for x in gates if row[x]["verdict"] == "block"]
    print(f, "intended", g, row[g]["verdict"], "fired", fired)
    if f == "F3" and row[g]["verdict"] != "block":
        continue
    assert fired, f"{{f}} tripped no gate at all: the fault is not a fault"
    e = faults[f]["edit"]
    assert e.get("before") != e.get("after"), f"{{f}} edit before equals after"
rep = (d / "report.md").read_text().lower()
for word in ("overlap", "miss", "false block", "12"):
    assert word in rep, f"report.md lacks {{word!r}}"
print("r1e faults checks ok")
PYV
cp -r ./{F_DIR}/* "$OUT"/
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
ls -l "$OUT"
"""
)


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
        "timeout_s": 5400,
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
            "r1e-variants-suite",
            V_SPEC,
            V_CHECK,
            [f"{V_DIR}/variants.py", f"{V_DIR}/measure.py"],
            "four rule-built variants are deterministic and meaning-preserving by compiled diff; gates 1 to 5 and the full suite rerun by the check; failures classed against the r1c parse",
            3000,
        ),
        task(
            "r1e-seeded-faults",
            F_SPEC,
            F_CHECK,
            [f"{F_DIR}/faults.py", f"{F_DIR}/measure.py"],
            "the gate battery is rerun by the check on G and nine seeded faults; every fault trips at least one gate; the full verdict matrix is recorded",
            3000,
        ),
    ],
}

out = Path(__file__).with_name("r1e-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
