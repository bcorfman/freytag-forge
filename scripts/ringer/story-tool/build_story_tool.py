# ruff: noqa: E501
"""Make the story CLI the only way story source reaches main (owner's decision 2026-11-24).

st-station5-format: station 5 applies the story CLI's canonical format in the ticket tree (before regenerating entry
    snapshots) and fails on a file the formatter refuses; never writes outside a ticket tree.
st-beat-placement: `story_cli new beat --at-turn N` places the beat itself, so the wiring worker no longer moves a beat
    by hand; the wiring worker logs every remaining hand edit to hand_edits.json and the station reports it.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "gates-r1"))
from build_r1e import CPU_PY, REPO  # noqa: E402

WORK = "/home/bcorfman/dev/ringer-work/story-tool"
CORES = 4


def cpu_rules(cores):
    return (
        f"CPU BUDGET (hard rule). This machine has 16 cores and another task runs beside you. Your share is {cores} cores at every moment. "
        f"Every pytest call passes `-n {cores}` explicitly and sets `PYTEST_XDIST_AUTO_NUM_WORKERS={cores}` (pyproject's addopts say `-n auto`, which means 16); "
        f"every carry_matrix() call passes `workers={cores}` or fewer; never run two heavy commands at once; never start a command in the background or with `&`, `nohup` or `setsid`; "
        "wrap long commands in `timeout`, and if one is killed, check `pgrep -af python` and stop leftovers before starting another. The check measures the cores used by processes whose "
        f"working directory is your worktree, averaged over 5-second windows, and fails above {cores + 2}.\n\n"
    )


def sampler(key, limit):
    return f"""cat > /tmp/st_cpu_{key}.py <<'CPUPY'
{CPU_PY}CPUPY
echo "0.00 0 0" > /tmp/st_cpu_{key}.txt
python3 /tmp/st_cpu_{key}.py "$PWD" /tmp/st_cpu_{key}.txt {limit} &
SAMPLER=$!
trap 'kill $SAMPLER 2>/dev/null || true' EXIT
"""


def sampler_end(key, limit):
    return f"""kill $SAMPLER 2>/dev/null || true
read peak over windows < /tmp/st_cpu_{key}.txt
echo "cores used by this worktree: peak $peak, $over of $windows windows above {limit}"
[ "$over" -eq 0 ] || {{ echo "CPU budget exceeded: peak $peak cores, limit {limit}"; exit 1; }}
"""


def common(owned):
    return (
        "You are a careful Python engineer on a story game's software factory. Your current working directory IS a git worktree of /home/bcorfman/dev/freytag-forge; edit files here directly. "
        f"You own ONLY these files: {', '.join(owned)}. NEVER edit any other file (in particular nothing under factory/checks/, factory/config/ or data/), never git commit, never touch "
        "/home/bcorfman/dev/freytag-forge itself, never run `uv`, never call a model, never use the network, never pass --cov to pytest. "
        "FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv . Python: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp` and `.venv/bin/python`. "
        "Ruff-clean (line length 120; `ruff check` and `ruff format` on every file you touch). Write NOTES.txt in the worktree root listing every interpretation you made. Leave changes uncommitted. "
        "You may update existing tests in your owned test files when the behaviour they pin changes on purpose; never weaken an unrelated assertion.\n\n"
        "BACKGROUND. The owner has decided that the story CLI (`.venv/bin/python -m storygame.story_cli`, commands in storygame/story_cmds/) is the only correct way to edit story source "
        "(data/stories/<story>/source/*.yaml). No check can see who typed an edit, so the rule is enforced on the result: source must be exactly what the CLI writes (its canonical format, "
        "storygame/story_cmds/cmd_fmt.py), and every place the factory still edits by hand is a missing CLI command to add.\n\n"
        + cpu_rules(CORES)
    )


def owned_check(owned):
    pattern = "|".join(p.replace(".", "\\.") for p in owned)
    return f"""changed=$(git status --porcelain --untracked-files=all | sed 's/^...//' | grep -vE '^(\\.venv|NOTES\\.txt)$' || true)
echo "changed files: $changed"
bad=$(printf '%s\\n' "$changed" | grep -vE '^({pattern})?$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership changed: $bad"; exit 1; }}
"""


# ---------------------------------------------------------------- T1 station 5 format

F_OWNED = [
    "factory/stations/free_gates.py",
    "tests/test_factory_stations.py",
    "storygame/story_cmds/cmd_fmt.py",
    "tests/story_source/test_cmd_fmt.py",
]
F_TESTS = "tests/test_factory_stations.py tests/story_source/test_cmd_fmt.py tests/test_entry_snapshots.py tests/test_factory_deliver.py"
F_SPEC = (
    common(F_OWNED)
    + "TODAY. factory/stations/free_gates.py (station 5, free_gates_handler) runs the free gates on a candidate repair tree, fail-fast: source_tree checks (when the payload has source_root), "
    "then an entry-snapshot step (regenerates entry snapshots with write_entry_snapshots only in a ticket tree, then check_entry_snapshots; read it), then gap rules, carry matrix, ruff and tests. "
    "It never formats the source, so an edit written outside the CLI fails about 10 format tests in CI.\n\n"
    "WHAT TO BUILD.\n"
    "1. In storygame/story_cmds/cmd_fmt.py add a public function `format_source_tree(root: Path, *, check: bool) -> tuple[list[str], list[str]]` returning (changed, refused): relative posix paths of "
    "files that are not canonical (rewritten when check is False) and of files whose reformatting would change a value (never written). It must apply exactly the rules run() applies today "
    "(dumps_document(load_document(path)), the _values_equal safety check, sorted rglob of *.yaml). Make run() use it for the whole-tree case, with output and exit codes unchanged. Add a test of "
    "format_source_tree in tests/story_source/test_cmd_fmt.py.\n"
    "2. In free_gates.py import it by name at module level (`from storygame.story_cmds.cmd_fmt import format_source_tree`) and call it through that module-level name (tests monkeypatch it). Add a "
    "format step that runs AFTER the source_tree checks and BEFORE the entry-snapshot step (the snapshot fingerprint covers the source bytes, so formatting must come first). Its source root is the "
    "resolved payload source_root when given, otherwise <story_root>/source when that directory exists; if neither, skip the step. Payload `story_format: false` skips it (same pattern as "
    "`carry_matrix` and `entry_snapshots`); default on.\n"
    "3. When the ticket has its own tree and the source root lies inside it, call format_source_tree(source_root, check=False): it rewrites non-canonical files. Otherwise call it with check=True and "
    'NEVER write: the station must not modify the main checkout. Fail with StationResult(False, "story_format", text) when refused is non-empty (text names each file and says reformatting would '
    "change a value), when check=True finds changed files (text names each file and says to run `story_cli fmt`), or when the function raises. Pass text through _tail.\n"
    '4. Keep the success result exactly StationResult(True, "free_gates", "all free gates passed"). Update the docstrings. Existing tests that do not test this step pass `"story_format": False` '
    "where needed so they neither write nor slow down. Add focused tests: (a) ticket tree holding a copy of the story package (at the same relative path as DEFAULT_ROOT) with one source file "
    "rewritten value-identically but non-canonically (for example scenes/1A.yaml rewritten with yaml.safe_dump(width=40); story.yaml is too simple, it dumps back identically): the station passes, the file is canonical afterwards, the snapshots are fresh "
    "(check_entry_snapshots empty) and the real DEFAULT_ROOT files are unchanged; (b) no ticket tree with the same copy as the handler's root: fails with check story_format naming the file, "
    "nothing written; (c) format_source_tree monkeypatched to report a refused file: fails naming it; (d) `story_format: false` skips the step. Stub gap-delta functions and pass `carry_matrix: False` "
    "as the existing tests do, so the new tests stay fast.\n\n"
    f"HOW TO TEST: `PYTEST_XDIST_AUTO_NUM_WORKERS={CORES} timeout 900 .venv/bin/python -m pytest -q -n {CORES} -p no:cacheprovider {F_TESTS}`. All must pass, within 600 seconds. "
    "The check also runs an independent probe of behaviours (a) to (d) and fails if anything under data/ changed."
)
F_PROBE = r"""
import shutil
import tempfile
from pathlib import Path

import yaml

import factory.stations.free_gates as fg
from factory.checks.gap_delta import DEFAULT_ROOT
from factory.line import Station
from storygame.runtime.entry_snapshots import check_entry_snapshots
from storygame.story_cmds.cmd_fmt import format_source_tree
from tests.test_factory_stations import NOW, make_ticket

here = Path.cwd().resolve()
rel = DEFAULT_ROOT.resolve().relative_to(here)
real = {p.relative_to(DEFAULT_ROOT).as_posix(): p.read_bytes() for p in DEFAULT_ROOT.rglob("*") if p.is_file()}
fg.snapshot = lambda root, anchors=None: {}
fg.load_baseline = lambda path: {}
fg.new_results = lambda baseline, current: {}
assert format_source_tree(DEFAULT_ROOT / "source", check=True) == ([], []), "committed story is not canonical"


def messy_copy(base):
    story = base / rel
    shutil.copytree(DEFAULT_ROOT, story)
    path = story / "source" / "scenes" / "1A.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    path.write_text(yaml.safe_dump(data, sort_keys=False, width=40, allow_unicode=True), encoding="utf-8")
    assert yaml.safe_load(path.read_text(encoding="utf-8")) == data
    changed, refused = format_source_tree(story / "source", check=True)
    assert changed == ["scenes/1A.yaml"] and refused == [], (changed, refused)
    return story


def tree_bytes(story):
    return {p.relative_to(story).as_posix(): p.read_bytes() for p in story.rglob("*") if p.is_file()}


tmp = Path(tempfile.mkdtemp(prefix="st_fmt_"))
payload = {"gap_baseline": "unused.json", "carry_matrix": False, "story_root": str(rel)}

tree = tmp / "tree"
story = messy_copy(tree)
fg.ticket_tree = lambda *args: tree
result = fg.free_gates_handler(here)(make_ticket(dict(payload), station=Station.FREE_GATES), NOW)
assert result.passed, f"(a) station failed in a ticket tree: {result.check}: {result.output[:600]}"
assert format_source_tree(story / "source", check=True) == ([], []), "(a) source not canonical after the station"
assert check_entry_snapshots(story) == [], "(a) snapshots stale after formatting: format must run before regeneration"
print("(a) ticket tree: formatted, snapshots fresh, passed")

base = tmp / "plain"
story_b = messy_copy(base)
before_b = tree_bytes(story_b)
fg.ticket_tree = lambda *args: None
result = fg.free_gates_handler(base)(make_ticket(dict(payload), station=Station.FREE_GATES), NOW)
assert not result.passed and result.check == "story_format" and "1A.yaml" in result.output, f"(b) {result}"
assert tree_bytes(story_b) == before_b, "(b) station wrote without a ticket tree"
print("(b) no tree: failed naming the file, wrote nothing")

real_fmt = fg.format_source_tree
fg.format_source_tree = lambda root, *, check: ([], ["scenes/9Z.yaml"])
fg.ticket_tree = lambda *args: tree
result = fg.free_gates_handler(here)(make_ticket(dict(payload), station=Station.FREE_GATES), NOW)
assert not result.passed and result.check == "story_format" and "scenes/9Z.yaml" in result.output, f"(c) {result}"
fg.format_source_tree = real_fmt
print("(c) refused file fails the station")

fg.ticket_tree = lambda *args: None
result = fg.free_gates_handler(base)(
    make_ticket(dict(payload, story_format=False, entry_snapshots=False), station=Station.FREE_GATES), NOW
)
assert result.passed, f"(d) story_format: false did not skip the step: {result}"
print("(d) skip flag honoured")

assert {p.relative_to(DEFAULT_ROOT).as_posix(): p.read_bytes() for p in DEFAULT_ROOT.rglob("*") if p.is_file()} == real, "real story changed"
shutil.rmtree(tmp)
print("station 5 format probe ok")
"""


def check_for(key, owned, out_name, tests, probe, budget):
    files = " ".join(p for p in owned if p.endswith(".py"))
    return (
        f"""set -eo pipefail
OUT="{WORK}/out/{out_name}"
mkdir -p "$OUT"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s {REPO}/.venv .venv
"""
        + owned_check(owned)
        + f"""[ -n "$changed" ] || {{ echo "nothing changed"; exit 1; }}
.venv/bin/python -m ruff check {files}
.venv/bin/python -m ruff format --check {files}
"""
        + sampler(key, CORES + 2)
        + f"""start=$(date +%s)
PYTEST_XDIST_AUTO_NUM_WORKERS={CORES} timeout 900 .venv/bin/python -m pytest -q -n {CORES} -p no:cacheprovider {tests}
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget {budget} s)"
[ "$took" -le {budget} ] || {{ echo "over the {budget} s budget"; exit 1; }}
.venv/bin/python - <<'PYPROBE'
{probe}
PYPROBE
"""
        + sampler_end(key, CORES + 2)
        + f"""git diff --quiet -- data || {{ echo "something under data/ changed"; git diff --stat -- data; exit 1; }}
git add -- {" ".join(owned)}
git diff --cached > "$OUT/{out_name}.patch"
git reset -q
[ -s "$OUT/{out_name}.patch" ] || {{ echo "empty patch"; exit 1; }}
[ -f NOTES.txt ] && cp NOTES.txt "$OUT/NOTES.txt" || true
wc -l "$OUT/{out_name}.patch"
"""
    )


# ---------------------------------------------------------------- T2 beat placement + hand-edit log

B_OWNED = [
    "storygame/story_cmds/cmd_new.py",
    "tests/story_source/test_cmd_new.py",
    "factory/stations/wiring.py",
    "tests/test_factory_wiring.py",
]
B_TESTS = "tests/story_source/test_cmd_new.py tests/test_factory_wiring.py tests/test_factory_claim_edit.py tests/story_source/test_cmd_fmt.py tests/test_factory_line.py"
B_SPEC = (
    common(B_OWNED)
    + "TODAY. The factory's wiring station (factory/stations/wiring.py) gives a Codex worker a brief (wiring_spec) to apply one approved story fix with the story CLI, then checks it (_check_extra, "
    "which also runs `story_cli fmt --check` and, for a new pacing beat, beat_position_error on the compiled package). For kind add_pacing_beat the CLI is not enough: `story_cli new beat <scene> <id> "
    "--say <text>` (storygame/story_cmds/cmd_new.py, _make_beat) always appends with at_turn 0, so the brief tells the worker to 'move only the beat record ... to the right position by hand'. Every "
    "brief also says 'If the CLI refuses, make the smallest hand edit necessary', and nothing records when that happens.\n\n"
    "WHAT TO BUILD.\n"
    "1. `story_cli new beat <scene> <id> --say <text> --at-turn N` (N a non-negative integer): the new record gets at_turn N and is inserted into the scene's beats list directly before the first "
    "existing beat whose at_turn is greater than N, or at the end when there is none. That must be the same rule beat_position_error applies to the compiled package.pacing.events of the scene: read "
    "storygame/story_source/c_scene.py (and whatever compiles a scene's pacing events) to confirm the beats list order is the compiled event order, and if other source lists also contribute events "
    "to a scene, place the beat so beat_position_error passes and explain in NOTES.txt. Without --at-turn the command behaves exactly as today. The written file must stay canonical (the command's "
    "existing write path) and pass its existing check/compile rollback. Add tests in tests/story_source/test_cmd_new.py: insertion in the middle, at the end, tie with an equal at_turn (goes after "
    "equals), and a test that for every scene of the committed story a beat added with --at-turn set to each distinct existing at_turn of that scene passes beat_position_error on the compiled copy.\n"
    "2. In wiring.py's add_pacing_beat brief, use `new beat ... --at-turn <at_turn>` and remove the hand-move instruction and its `set beat:<id>.at_turn` step (keep the other set steps). "
    "The brief must no longer tell the worker to move or reorder anything by hand.\n"
    "3. HAND-EDIT LOG. Every wiring brief must tell the worker: if a CLI command refuses and you make a hand edit, record it; write `hand_edits.json` in the same directory as plan.json (the brief "
    'already says where plan.json is) as a JSON list, [] when there were none, each entry {"file": <source-relative path>, "record": <address or id>, "refused_command": <the exact CLI command '
    'that refused>, "error": <its error text>}. _check_extra must fail when the file is missing, is not a list, or has an entry missing a key, and print the entries it found. After a passing run '
    "the handler must read the file and add a plain line to the passing StationResult output, `hand edits: N` followed by one line per entry (file, record, refused command), so the factory's ticket "
    "evidence shows which CLI commands are missing. Keep every other output line as it is. Add tests in tests/test_factory_wiring.py for the new brief text (no hand move, --at-turn present, "
    "hand_edits.json instructions in every plan kind), for _check_extra rejecting a missing or malformed log, and for the handler reporting N hand edits (use the module's existing test seams for "
    "the Ringer run; never run Ringer or a model).\n\n"
    f"HOW TO TEST: `PYTEST_XDIST_AUTO_NUM_WORKERS={CORES} timeout 900 .venv/bin/python -m pytest -q -n {CORES} -p no:cacheprovider {B_TESTS}`. All must pass, within 600 seconds. "
    "The check also runs the CLI on a copy of the real story and checks the brief and check text."
)
B_PROBE = r"""
import json
import os
import shutil
import tempfile
from pathlib import Path

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.stations import wiring
from storygame.story_cli import main
from storygame.story_package.loader import load_story_package
from storygame.story_source.yamlio import load_document

here = Path.cwd()
tmp = Path(tempfile.mkdtemp(prefix="st_beat_"))
story = tmp / "story"
shutil.copytree(DEFAULT_ROOT, story)
placed = 0
for scene_path in sorted((story / "source" / "scenes").glob("*.yaml")):
    if scene_path.name.endswith(".match.yaml"):
        continue
    scene = load_document(scene_path)
    turns = sorted({b["at_turn"] for b in scene.get("beats", []) if isinstance(b.get("at_turn"), int)})
    if len(turns) < 2:
        continue
    scene_id = scene_path.stem
    n = turns[len(turns) // 2]
    os.chdir(story / "source")
    try:
        code = main(["new", "beat", scene_id, f"probe_beat_{placed}", "--say", "A probe line.", "--at-turn", str(n)])
    finally:
        os.chdir(here)
    assert code == 0, f"new beat --at-turn failed in {scene_id}"
    beats = load_document(scene_path)["beats"]
    index = next(i for i, b in enumerate(beats) if b["id"] == f"probe_beat_{placed}")
    assert beats[index]["at_turn"] == n, f"{scene_id}: at_turn {beats[index]['at_turn']} != {n}"
    package = load_story_package(story)
    error = wiring.beat_position_error(package.pacing.events, f"probe_beat_{placed}", scene_id)
    assert error is None, f"{scene_id}: {error}"
    print(scene_id, "beat at turn", n, "placed at index", index, "of", len(beats))
    placed += 1
    if placed == 3:
        break
assert placed >= 1, "no scene with two distinct beat turns to probe"
os.chdir(story / "source")
try:
    assert main(["fmt", "--check"]) == 0, "source not canonical after new beat --at-turn"
finally:
    os.chdir(here)

plan = {"kind": "add_pacing_beat", "scene": "1A", "beat": {"id": "x", "at_turn": 3, "text": "t", "verbatim": False, "trailing": False, "when": {}, "sets": {}}}
brief = wiring.wiring_spec(plan, "data/stories/continuity-initiative")
assert "--at-turn" in brief, "add_pacing_beat brief does not use --at-turn"
assert "by hand" not in brief.lower().replace("hand edit", ""), "brief still asks for a move by hand"
for kind in ("add_pacing_beat", "edit_claim_evidence", "set_text"):
    text = wiring.wiring_spec(dict(plan, kind=kind), "data/stories/continuity-initiative")
    assert "hand_edits.json" in text, f"{kind} brief lacks hand_edits.json"
extra = wiring._check_extra(Path("/tmp/plan.json"), "data/stories/continuity-initiative", ["a"])
assert "hand_edits.json" in extra, "_check_extra does not check hand_edits.json"
shutil.rmtree(tmp)
print("beat placement probe ok")
"""


def task(key, spec, check, owned, verified):
    return {
        "key": key,
        "task_type": "code-feature",
        "engine": "codex",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "max_attempts": 2,
        "ownership": owned,
        "spec": spec,
        "check": check,
        "expect_files": [],
        "timeout_s": 3600,
        "check_timeout_s": 1200,
        "verified": verified,
    }


manifest = {
    "run_name": "story-tool-only-edits",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        task(
            "st-station5-format",
            F_SPEC,
            check_for("f", F_OWNED, "station5-format", F_TESTS, F_PROBE, 600),
            F_OWNED,
            "tests pass in budget; a probe shows station 5 formats in a ticket tree before regenerating snapshots, fails without writing outside one, fails on a refused file, and honours the skip flag",
        ),
        task(
            "st-beat-placement",
            B_SPEC,
            check_for("b", B_OWNED, "beat-placement", B_TESTS, B_PROBE, 600),
            B_OWNED,
            "tests pass in budget; new beat --at-turn on a copy of the real story passes beat_position_error and stays canonical; the briefs drop the hand move and require hand_edits.json, and the check enforces it",
        ),
    ],
}

out = Path(__file__).with_name("story-tool-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
