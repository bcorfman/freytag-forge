# ruff: noqa: E501
"""Gate-proving ladder R1e-2. No model calls inside the tasks, no network.

r1e2-station5-snapshots: station 5 (factory/stations/free_gates.py) regenerates the scene-entry snapshots in the
    ticket tree after the source checks pass, then checks them; owner's decision 2026-11-24.
r1e2-variants-remeasure: rerun R1e's four meaning-preserving variants with the story CLI's canonical format and
    regenerated entry snapshots applied after each variant, with the failure labels fixed.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_r1e import COMMON, CPU_PY, R1C_FILES, REPO, STORY, WORK, cpu_rules  # noqa: E402,F401

PRIOR = f"{WORK}/out/r1e-variants"
S_CORES = 4
V_CORES = 10


def sampler(key, limit):
    return f"""cat > /tmp/r1e2_cpu_{key}.py <<'CPUPY'
{CPU_PY}CPUPY
echo "0.00 0 0" > /tmp/r1e2_cpu_{key}.txt
python3 /tmp/r1e2_cpu_{key}.py "$PWD" /tmp/r1e2_cpu_{key}.txt {limit} &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true' EXIT
"""


def sampler_end(key, limit):
    return f"""kill $SAMPLER 2>/dev/null || true
read peak over windows < /tmp/r1e2_cpu_{key}.txt
echo "cores used by this worktree: peak $peak over 5 s windows, $over of $windows windows above {limit}"
[ "$over" -eq 0 ] || {{ echo "CPU budget exceeded: peak $peak cores, limit {limit}; $over windows over"; exit 1; }}
"""


# ---------------------------------------------------------------- station 5

S_TESTS = "tests/test_factory_stations.py tests/test_entry_snapshots.py tests/test_entry_snapshot_errors.py tests/test_factory_deliver.py tests/test_factory_guard.py tests/test_factory_probe_routing.py"
S_SPEC = (
    "You are a careful Python engineer on a story game's software factory. Your current working directory IS a git worktree of /home/bcorfman/dev/freytag-forge (detached at HEAD); edit files here directly. "
    "You own ONLY these files: factory/stations/free_gates.py and tests/test_factory_stations.py. NEVER edit any other file (in particular nothing under factory/checks/, factory/config/, storygame/ or data/), "
    "never git commit, never touch /home/bcorfman/dev/freytag-forge itself, never run `uv`, never call a model, never use the network, never pass --cov to pytest. "
    "FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv . Python: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp` and `.venv/bin/python`. "
    "Ruff-clean (line length 120; run `.venv/bin/python -m ruff check` and `ruff format` on both files). Write NOTES.txt in the worktree root listing every interpretation you made. Leave your changes uncommitted.\n\n"
    + cpu_rules(S_CORES)
    + "BACKGROUND. Each story package keeps scene-entry snapshots in <story_root>/entry/<scene>.json. Each records a `source_fingerprint`: a hash of every file in the story package except entry/ "
    "(storygame/runtime/entry_snapshots.py: _source_fingerprint, write_entry_snapshots, check_entry_snapshots; read the whole file). Any change to the story's source therefore makes every snapshot stale, and about 20 tests "
    "in the PR suite then fail. The factory's station 5 (factory/stations/free_gates.py, free_gates_handler) runs the free deterministic gates on a candidate repair tree; nothing in the factory regenerates the snapshots, "
    "so every factory story repair would fail CI. The owner has decided that station 5 regenerates them.\n\n"
    "WHAT TO BUILD, in factory/stations/free_gates.py:\n"
    "1. Import by name at module level: `from storygame.runtime.entry_snapshots import check_entry_snapshots, write_entry_snapshots` and call them through those module-level names (tests monkeypatch them there).\n"
    "2. Add an entry-snapshot step that runs AFTER the source_tree checks (or straight away when the payload has no source_root) and BEFORE the gap-delta step, so the gap rules, carry matrix and tests all see fresh snapshots. "
    "It resolves story_root exactly as the gap step does today (payload `story_root`, default DEFAULT_ROOT, through _resolve); move that resolution up so both steps share it.\n"
    "3. The step is skipped when the payload has `entry_snapshots: false` (the same pattern as `carry_matrix`); default on.\n"
    "4. When the ticket has its own tree (ticket_tree returned a path) AND the resolved story_root lies inside that tree, call write_entry_snapshots(story_root). When there is no ticket tree, or story_root lies outside it, "
    "NEVER write: the station must not modify the main checkout. In every case then call check_entry_snapshots(story_root).\n"
    '5. If write_entry_snapshots raises (any Exception), or check_entry_snapshots returns any problems, return StationResult(False, "entry_snapshots", <text>), where text is the problems joined by newlines (or the error '
    "text), passed through _tail. With no tree, stale snapshots therefore fail with check_entry_snapshots' own 'stale fingerprint for scene ...' lines, which is right: they can only be regenerated in a ticket tree.\n"
    '6. Keep the success result exactly as it is today: StationResult(True, "free_gates", "all free gates passed"). Update the module and handler docstrings to name the new step. Change nothing else in the station\'s behaviour.\n\n'
    'TESTS, in tests/test_factory_stations.py. Existing tests that call the handler with the real repository root must not start writing or slowing down: pass `"entry_snapshots": False` in their payloads where the step '
    "is not what they test (you may edit those payload dicts; do not weaken any existing assertion). Add focused tests: (a) in a ticket tree (monkeypatch ticket_tree to return a tmp_path tree holding a copy of the story "
    "package at the same relative path as DEFAULT_ROOT, with one byte added to a source file, for example a trailing YAML comment), the station passes, every entry json in the copy now carries the new fingerprint, "
    "check_entry_snapshots on the copy is empty, and the real DEFAULT_ROOT/entry files are byte-for-byte unchanged; (b) with no ticket tree and the same stale copy as the handler's root, the station fails with check "
    '"entry_snapshots" and output naming a stale fingerprint, and no file in the copy changed; (c) with check_entry_snapshots monkeypatched to return a carry-in gate problem line, the station fails with that line; '
    "(d) `entry_snapshots: false` skips the step even when snapshots are stale. Stub the gap-delta functions (snapshot, load_baseline, new_results) and pass `carry_matrix: False` where a test does not need them, as the "
    "existing tests do, so the new tests stay fast (under 20 seconds together).\n\n"
    f"HOW TO TEST: `PYTEST_XDIST_AUTO_NUM_WORKERS={S_CORES} timeout 900 .venv/bin/python -m pytest -q -n {S_CORES} -p no:cacheprovider {S_TESTS}`. All must pass. "
    "TIME. That command must finish within 600 seconds; the check runs it and an independent probe of the four behaviours above, and fails if anything under data/ changed in the worktree."
)
S_PROBE = r"""
import shutil
import tempfile
from pathlib import Path

import factory.stations.free_gates as fg
from factory.checks.gap_delta import DEFAULT_ROOT
from factory.line import Station
from storygame.runtime.entry_snapshots import _source_fingerprint, check_entry_snapshots
from tests.test_factory_stations import NOW, make_ticket

here = Path.cwd().resolve()
rel = DEFAULT_ROOT.resolve().relative_to(here)
real_entry = {p.name: p.read_bytes() for p in (DEFAULT_ROOT / "entry").glob("*.json")}
assert real_entry, "no committed entry snapshots"
fg.snapshot = lambda root, anchors=None: {}
fg.load_baseline = lambda path: {}
fg.new_results = lambda baseline, current: {}


def stale_copy(base):
    story = base / rel
    shutil.copytree(DEFAULT_ROOT, story)
    src = story / "source" / "story.yaml"
    src.write_text(src.read_text(encoding="utf-8") + "# r1e2 probe edit\n", encoding="utf-8")
    return story


def entry_bytes(story):
    return {p.name: p.read_bytes() for p in (story / "entry").glob("*.json")}


tmp = Path(tempfile.mkdtemp(prefix="r1e2_s5_"))
payload = {"gap_baseline": "unused.json", "carry_matrix": False, "story_root": str(rel)}

# (a) ticket tree: regenerate, pass
tree = tmp / "tree"
story = stale_copy(tree)
before = entry_bytes(story)
fg.ticket_tree = lambda *args: tree
result = fg.free_gates_handler(here)(make_ticket(dict(payload), station=Station.FREE_GATES), NOW)
assert result.passed, f"(a) station failed in a ticket tree: {result.check}: {result.output[:600]}"
assert result.output == "all free gates passed", result.output
after = entry_bytes(story)
assert after.keys() == before.keys() and after != before, "(a) snapshots were not rewritten"
fingerprint = _source_fingerprint(story)
import json
for name, data in after.items():
    assert json.loads(data)["source_fingerprint"] == fingerprint, f"(a) {name} has a stale fingerprint"
assert check_entry_snapshots(story) == [], "(a) snapshots still have problems after regeneration"
print("(a) ticket tree: regenerated", len(after), "snapshots, station passed")

# (b) no ticket tree: never write, fail on stale
base = tmp / "plain"
story_b = stale_copy(base)
before_b = entry_bytes(story_b)
fg.ticket_tree = lambda *args: None
result = fg.free_gates_handler(base)(make_ticket(dict(payload), station=Station.FREE_GATES), NOW)
assert not result.passed and result.check == "entry_snapshots", f"(b) expected entry_snapshots failure, got {result}"
assert "stale fingerprint" in result.output, f"(b) output does not name a stale fingerprint: {result.output[:400]}"
assert entry_bytes(story_b) == before_b, "(b) station wrote snapshots without a ticket tree"
print("(b) no tree: failed on stale fingerprints, wrote nothing")

# (c) carry-in problem surfaces
real_check = fg.check_entry_snapshots
fg.check_entry_snapshots = lambda root: ["carry-in gate problem: scene 9Z fact probe consumer probe is not supplied"]
fg.ticket_tree = lambda *args: tree
result = fg.free_gates_handler(here)(make_ticket(dict(payload), station=Station.FREE_GATES), NOW)
assert not result.passed and result.check == "entry_snapshots" and "carry-in gate problem" in result.output, f"(c) {result}"
fg.check_entry_snapshots = real_check
print("(c) carry-in problem fails the station")

# (d) skip flag
fg.ticket_tree = lambda *args: None
result = fg.free_gates_handler(base)(make_ticket(dict(payload, entry_snapshots=False), station=Station.FREE_GATES), NOW)
assert result.passed, f"(d) entry_snapshots: false did not skip the step: {result}"
print("(d) skip flag honoured")

assert {p.name: p.read_bytes() for p in (DEFAULT_ROOT / "entry").glob("*.json")} == real_entry, "real entry snapshots changed"
shutil.rmtree(tmp)
print("station 5 probe ok")
"""
S_CHECK = (
    f"""set -eo pipefail
WORK={WORK}
OUT="$WORK/out/r1e2-station5"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
changed=$(git status --porcelain --untracked-files=all | sed 's/^...//' | grep -vE '^(\\.venv|NOTES\\.txt)$' || true)
echo "changed files: $changed"
bad=$(printf '%s\\n' "$changed" | grep -vE '^(factory/stations/free_gates\\.py|tests/test_factory_stations\\.py)?$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership changed: $bad"; exit 1; }}
printf '%s\\n' "$changed" | grep -qx factory/stations/free_gates.py || {{ echo "free_gates.py not changed"; exit 1; }}
.venv/bin/python -m ruff check factory/stations/free_gates.py tests/test_factory_stations.py
.venv/bin/python -m ruff format --check factory/stations/free_gates.py tests/test_factory_stations.py
grep -q 'write_entry_snapshots' factory/stations/free_gates.py || {{ echo "free_gates.py does not call write_entry_snapshots"; exit 1; }}
"""
    + sampler("s5", S_CORES + 2)
    + f"""start=$(date +%s)
PYTEST_XDIST_AUTO_NUM_WORKERS={S_CORES} timeout 900 .venv/bin/python -m pytest -q -n {S_CORES} -p no:cacheprovider {S_TESTS}
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 600 s)"
[ "$took" -le 600 ] || {{ echo "over the 600 s budget"; exit 1; }}
.venv/bin/python - <<'PYS'
{S_PROBE}
PYS
"""
    + sampler_end("s5", S_CORES + 2)
    + """git diff --quiet -- data || { echo "something under data/ changed"; git diff --stat -- data; exit 1; }
git add -- factory/stations/free_gates.py tests/test_factory_stations.py
git diff --cached > "$OUT/station5.patch"
git reset -q
[ -s "$OUT/station5.patch" ] || { echo "empty patch"; exit 1; }
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
wc -l "$OUT/station5.patch"
"""
)

# ---------------------------------------------------------------- variants remeasure

V_DIR = "tools_gates_r1e2_variants"
V_SPEC = (
    COMMON
    + cpu_rules(V_CORES)
    + (
        f"Create files ONLY in ./{V_DIR}/ .\n\n"
        "GOAL. Round R1e measured how often the full PR test suite blocks story changes that keep the story's meaning. It built four rule-made variants of the story source (layout, contractions, synonyms, reorder), "
        "and the suite failed every one: 34, 34, 39 and 40 tests, against 0 of 5,096 on the original. The same 34 failed on all four, even the pure layout variant, for two reasons a real factory edit would not hit: "
        "(1) the scene-entry snapshots ("
        + STORY
        + "/entry/*.json) record a source_fingerprint of the package files and were not regenerated, so about 20 snapshot tests failed; the factory's station 5 will now regenerate "
        "them; (2) the variants were not saved in the story CLI's canonical YAML format, so about 10 format tests failed (tests/story_source/test_cmd_fmt.py, test_cmd_new.py, test_cli_set.py, test_yamlio.py). "
        "Remeasure with both fixed, to find the tests that truly pin wording or order. R1e estimated about 5 such tests for synonyms, 6 for reorder and 0 for contractions.\n\n"
        f"START FROM R1e's TOOLS. Copy {PRIOR}/variants.py and {PRIOR}/measure.py into ./{V_DIR}/ (read {PRIOR}/report.md and NOTES.txt too) and change them as follows; keep the four variant rules exactly as they are.\n"
        "1. After each variant rule is applied in place to "
        + STORY
        + "/source, and before any gate runs: (a) format the source with the story CLI's own fmt code (storygame/story_cmds/cmd_fmt.py; reuse its functions or "
        "run it the way `story fmt` does; never write your own formatter), recording the files it reformatted and any file it refused ('value changed, not written', which is a finding); then (b) regenerate the entry "
        "snapshots with storygame.runtime.entry_snapshots.write_entry_snapshots on the story root, last, because the fingerprint covers every non-entry file; then (c) run check_entry_snapshots and record its problems "
        "(expected none). Do the same three steps on the original tree too, as a control: there fmt should change nothing and regeneration should change no snapshot byte; record both.\n"
        "2. The meaning check (compiled-package diff against the original) runs after fmt. The layout variant may become byte-identical to the original after canonical formatting; that is allowed and worth reporting.\n"
        "3. FIX THE LABEL BUG. R1e's measure.py swapped two labels (around its lines 335-340): a test that failed on the variant, failed again on the variant rerun and PASSED on the original rerun was filed as an env failure. "
        "The rules are: flaky = passed when rerun on the variant; real = failed on the variant rerun AND passed on the original rerun; env = failed on both reruns. For every failing test record "
        "{nodeid, variant_rerun_passed, original_rerun_passed, label} in a `failures` list in suite.json, beside the existing real_failures, flaky and env_failures lists, which must agree with it.\n"
        f"4. Write each tree's JUnit XML to ./{V_DIR}/junit/<tree>.xml (tree = original, layout, contractions, synonyms, reorder).\n"
        "5. In gates.json add per tree: fmt_changed (list of files), fmt_refused (list of files), snapshots_changed (number of entry files whose bytes changed on regeneration), entry_problems (list).\n"
        "6. report.md: the same summary as R1e plus a table comparing R1e and this round per variant (failing tests, real failures), the full list of remaining real failures with cause, and a plain answer to: after "
        "regeneration and canonical format, how many tests pin wording, how many pin order, and what this means for a factory repair that rewrites prose.\n\n"
        f"DELIVERABLES in ./{V_DIR}/ : variants.py, measure.py, meaning.json, gates.json, suite.json, junit/, report.md (same shapes as R1e plus the additions above). `.venv/bin/python ./{V_DIR}/measure.py` from the worktree "
        "root does everything; it MUST restore the story directory (source AND entry/) at exit, also on error. The full PR suite command per tree stays "
        f"`PYTEST_XDIST_AUTO_NUM_WORKERS={V_CORES} .venv/bin/python -m pytest -q -n {V_CORES} -p no:cacheprovider --junitxml=<file> tests`. "
        f"TIME. The whole measure.py run must finish within 2400 seconds using your {V_CORES}-core share (R1e's took about 15 minutes). Run the full measurement at most once yourself; the check runs it again as the authoritative run."
    )
)
V_CHECK = (
    f"""set -eo pipefail
WORK={WORK}
OUT="$WORK/out/r1e2-variants"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
dirty() {{ git status --porcelain --untracked-files=all | grep -vE '^\\?\\? ({V_DIR}/|NOTES\\.txt$|\\.venv$)' || true; }}
changed=$(dirty)
[ -z "$changed" ] || {{ echo "tracked files changed or stray files before the run: $changed"; exit 1; }}
.venv/bin/python -m ruff check ./{V_DIR}/*.py
.venv/bin/python -m ruff format --check ./{V_DIR}/*.py
rm -rf /tmp/r1e2_v_a /tmp/r1e2_v_b
.venv/bin/python ./{V_DIR}/variants.py /tmp/r1e2_v_a
.venv/bin/python ./{V_DIR}/variants.py /tmp/r1e2_v_b
diff -r /tmp/r1e2_v_a /tmp/r1e2_v_b > /tmp/r1e2_v_diff.txt || {{ echo "variants.py is not deterministic:"; head -40 /tmp/r1e2_v_diff.txt; exit 1; }}
for v in layout contractions synonyms reorder; do
  [ -d /tmp/r1e2_v_a/$v/source ] || {{ echo "variant $v not written"; exit 1; }}
done
"""
    + sampler("v2", V_CORES + 2)
    + f"""start=$(date +%s)
PYTEST_XDIST_AUTO_NUM_WORKERS={V_CORES} .venv/bin/python ./{V_DIR}/measure.py
took=$(( $(date +%s) - start ))
echo "measurement took $took s (budget 2400 s)"
[ "$took" -le 2400 ] || {{ echo "over the 2400 s budget"; exit 1; }}
"""
    + sampler_end("v2", V_CORES + 2)
    + f"""changed=$(dirty)
[ -z "$changed" ] || {{ echo "measure.py did not restore the story directory: $changed"; exit 1; }}
.venv/bin/python - <<'PYV'
import json
import xml.etree.ElementTree as ET
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
assert o["fmt_changed"] == [] and o["fmt_refused"] == [], f"original is not canonical: {{o['fmt_changed']}} {{o['fmt_refused']}}"
assert o["snapshots_changed"] == 0, f"regenerating the original changed {{o['snapshots_changed']}} snapshots"
for t in ["original", *names]:
    assert gates[t]["entry_problems"] == [], f"{{t}}: entry snapshot problems after regeneration: {{gates[t]['entry_problems'][:5]}}"
so = suite["original"]
assert so["passed"] > 3000 and so["failed"] == 0 and so["errors"] == 0, f"original suite not clean: {{so['passed']}} passed, {{so['failed']}} failed, {{so['errors']}} errors"
files = json.loads(Path("{R1C_FILES}").read_text())
for t in ["original", *names]:
    root = ET.parse(d / "junit" / f"{{t}}.xml").getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    jf = sum(int(s.get("failures", 0)) for s in suites)
    je = sum(int(s.get("errors", 0)) for s in suites)
    assert (jf, je) == (suite[t]["failed"], suite[t]["errors"]), f"{{t}}: suite.json says {{suite[t]['failed']}}/{{suite[t]['errors']}} failed/errors, junit says {{jf}}/{{je}}"
for n in names:
    s = suite[n]
    assert s["passed"] + s["failed"] + s["errors"] > 3000, f"variant {{n}} suite ran too few tests"
    rows = s["failures"]
    assert len(rows) == s["failed"] + s["errors"], f"{{n}}: {{len(rows)}} failure rows for {{s['failed'] + s['errors']}} failures"
    for r in rows:
        want = "flaky" if r["variant_rerun_passed"] else ("real" if r["original_rerun_passed"] else "env")
        assert r["label"] == want, f"{{n}} {{r['nodeid']}}: label {{r['label']}}, rerun results say {{want}}"
    real = sorted(r["nodeid"] for r in rows if r["label"] == "real")
    assert sorted(f["nodeid"] for f in s["real_failures"]) == real, f"{{n}}: real_failures disagree with the failures labels"
    assert sorted(s["flaky"]) == sorted(r["nodeid"] for r in rows if r["label"] == "flaky"), f"{{n}}: flaky list disagrees"
    assert sorted(s["env_failures"]) == sorted(r["nodeid"] for r in rows if r["label"] == "env"), f"{{n}}: env list disagrees"
    for f in s["real_failures"]:
        assert f["cause"] in ("pins_authored_text", "pins_order", "pins_layout", "checks_a_real_rule", "other"), f"bad cause {{f['cause']}}"
        path = f["nodeid"].split("::")[0]
        assert Path(path).exists(), f"failure names a missing file {{path}}"
        key = path if path in files else "tests/" + Path(path).name
        if key in files:
            assert f["file_class"] == files[key]["class"], f"{{path}} file_class {{f['file_class']}} vs r1c {{files[key]['class']}}"
    print(n, "fmt_changed", len(gates[n]["fmt_changed"]), "refused", len(gates[n]["fmt_refused"]), "failed", s["failed"], "errors", s["errors"], "real", len(real), "env", len(s["env_failures"]), "flaky", len(s["flaky"]))
rep = (d / "report.md").read_text().lower()
for word in ("r1e", "34", "regenerat", "canonical", "synonym", "reorder"):
    assert word in rep, f"report.md lacks {{word!r}}"
print("r1e2 variants checks ok")
PYV
cp -r ./{V_DIR}/* "$OUT"/
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
ls -l "$OUT"
"""
)


def task(key, spec, check, owned, verified, task_type, timeout_s, check_timeout):
    return {
        "key": key,
        "task_type": task_type,
        "engine": "codex",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "max_attempts": 2,
        "ownership": owned,
        "spec": spec,
        "check": check,
        "expect_files": [],
        "timeout_s": timeout_s,
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
            "r1e2-station5-snapshots",
            S_SPEC,
            S_CHECK,
            ["factory/stations/free_gates.py", "tests/test_factory_stations.py"],
            "station tests pass in budget; an independent probe shows regeneration in a ticket tree, no write and a stale failure without one, carry-in problems surfaced, and the skip flag; nothing under data/ changed",
            "code-feature",
            3600,
            1200,
        ),
        task(
            "r1e2-variants-remeasure",
            V_SPEC,
            V_CHECK,
            [f"{V_DIR}/variants.py", f"{V_DIR}/measure.py"],
            "original stays canonical with current snapshots and a clean suite; every variant regenerates cleanly; failure labels follow the rerun results; counts match the JUnit files",
            "probe",
            5400,
            3000,
        ),
    ],
}

out = Path(__file__).with_name("r1e2-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
