# ruff: noqa: E501
"""Round 33b: Step 6 nine-scene coverage ledger generator, and R1b-2 deterministic term-leak adjudication. Free, no model."""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/factory-33b"
REPO = "/home/bcorfman/dev/freytag-forge"
PY = f"{REPO}/.venv/bin/python"
R1B = "/home/bcorfman/dev/ringer-work/qual-20261122/gates/r1b"

COMMON = (
    "You are an engineer on freytag-forge. Your current working directory IS a git worktree of the repo (detached at HEAD). "
    "Edit files here directly. NEVER git commit, NEVER call a model (not `claude`, not `codex`), NEVER use the network, never run `uv`. "
    f"Use the interpreter {PY} only (if `.venv` is missing in the worktree, run `ln -s {REPO}/.venv .venv` first). Never pass --cov to pytest. "
    "Python 3.12, ruff line length from pyproject. Write NOTES.txt (worktree root, never committed) listing each ambiguity and your choice. "
    "Read AGENTS.md first, then docs/world-model-grounding.md only if you touch story data (you must not). Do not edit story source, runtime code or any existing test."
)

SPEC_LEDGER = (
    COMMON
    + "\n\nYou may edit ONLY: scripts/qualification/coverage_ledger.py (new), tests/test_coverage_ledger.py (new), "
    ".plans/qualification/coverage-ledger.md (new, generated), tests/shard_durations.json (add exactly one entry for the new test file with value 3.0, keeping the file's key order and format).\n\n"
    "TASK: write the Step 6 nine-scene coverage ledger generator. Read first: .plans/qualification/step-6-structural-check.md (the goal text), .plans/game-path-completion-matrix-gen.py and .plans/game-path-completion-matrix.md "
    "(an older ledger of timing and storylets; reuse its way of reading the package, do not edit it), tests/test_game_path_journeys.py (KNOWN_UNREACHABLE, PLAYER_REALIZATIONS, CHAINS, play()), tests/journey_prefix.py (run()), tests/fixtures/known_unreachable_approved.json.\n\n"
    "`scripts/qualification/coverage_ledger.py` exposes: `static_ledger(package, known_unreachable, approved_ids) -> dict` (no journeys; pure; fast) and `journey_evidence(preferred_runs) -> dict` plus `main(argv)` with flags `--journeys` (actually play the journeys: for every player-visible storylet realization play it once with the same `CHAINS` preference logic the journey test uses, using `multiprocessing` with at most 4 workers, importing the helpers from tests.test_game_path_journeys / tests.journey_prefix rather than copying them) and `--write PATH`. "
    "The ledger covers all nine scenes (1A to 3C) and for each scene lists: \n"
    "(1) STORYLETS: every storylet realization id with status `reachable` (a journey picked it; with --journeys record the journey id and turn), `observer_only` (audience not player-visible public, cannot be journeyed), or `retired_or_unreachable` (in KNOWN_UNREACHABLE; also shown with the approved-list decision text). Without --journeys the status for a player-visible realization is `reachable_by_nightly_journey` (the nightly parametrized test asserts it) and the output says so in its header. Any player-visible realization neither journeyed nor in KNOWN_UNREACHABLE is `UNACCOUNTED` and the generator exits non-zero.\n"
    "(2) EARNED EXITS: the scene's outgoing transition ids and, with --journeys, whether some journey left the scene by an earned transition (versus a forced exit); the terminal ending (3C) reached by the default journey.\n"
    "(3) PRESSURE RESPONSES: each pressure event id of the scene (from the package pacing data; the older ledger lists them in its section A) and, with --journeys, whether any journey recorded it as a fired deadline event (state.turn_records[*].deadline_event_ids) or not; `not exercised` is a plain finding, not an error.\n"
    "(4) ENTRY-STATE CLASSES: with --journeys, the distinct sets of scene-entry facts (the facts true when the scene is entered, restricted to the facts the scene's storylets and transitions read) observed across the journeys, with the count of journeys per class; without it, the list of facts the scene reads.\n"
    "(5) ACTION CLASSES: the action kinds the journeys used in the scene (take the kinds from whatever the journey harness records, e.g. selected candidate kinds or the ACTION_COMMANDS entries); if the harness records none, say `not recorded` rather than inventing.\n"
    "(6) UNEXAMINED: a closing section that states plainly what this ledger does NOT cover: pairwise deviations, custody/location changes, free-text discovery by a blind player, and state merging; one sentence each.\n"
    "Output is deterministic Markdown (sorted, no timestamps). Write the real result with `--journeys --write .plans/qualification/coverage-ledger.md` and include the run time in seconds on the last line of your NOTES.txt (not in the ledger).\n\n"
    "TESTS (tests/test_coverage_ledger.py, fast, NO journeys played, total under 5 seconds): static_ledger on the real package: all nine scenes appear; the four N-3 ids are `retired_or_unreachable`; every other player-visible realization is `reachable_by_nightly_journey` and none is `UNACCOUNTED`; observer-only realizations are listed as such; a synthetic KNOWN_UNREACHABLE that omits one N-3 id makes that id `UNACCOUNTED` and `main` exit non-zero (call main with an injected mapping or monkeypatch); the output is byte-identical across two calls; the committed `.plans/qualification/coverage-ledger.md` header lists the same realization counts as static_ledger (one parametrized assertion, not many tests). Add one-line tests only where behaviour is distinct; keep the file under 80 lines."
)

SPEC_R1B2 = (
    COMMON
    + "\n\nYou may create ONLY the directory tools_gates_r1b2/ in the worktree (untracked) containing: adjudicate.py, tests/test_adjudicate.py, and the outputs labels.json and report.md. Touch nothing else.\n\n"
    f"TASK R1b-2: label each recorded narration term-leak rejection deterministically, with no model and no human. Read first: {R1B}/measure.py, {R1B}/NOTES.txt, {R1B}/sources.json, {R1B}/sample.json, {R1B}/report.md "
    "(an earlier worker measured the rejections; bench reports keep `guard_rejections[]` on each turn of `runs[].turns` and the separate `rejected_turns`; entries have `code`, a message, sometimes the `term`, and `rejected_narration`; the accepted narration of the turn is in `narration`/`text`), and storygame/runtime/narration_safety.py lines 150 to 275 (the guard: it rejects narration that names a known term the player has not earned).\n"
    "Method (implement exactly): for every rejection entry whose code is `narration_known_term_leak` or whose message fallback says `unavailable knowledge` or `unavailable entity`, take the leaked term from the entry's `term` field, else from the single-quoted text in its message (if the message is truncated or no term can be recovered, label `undecidable`). Casefold and normalise whitespace. Then label, first match wins:\n"
    "  `player_echo`: the term occurs (word-boundary match, or plural/possessive of it) in the player's own command for that turn. The player introduced it; narration repeating it reveals nothing new, so the rejection is a CANDIDATE FALSE rejection.\n"
    "  `previously_visible`: the term occurs in any EARLIER player-visible text of the same run (entry text if recorded, accepted narration of earlier turns, earlier player commands). CANDIDATE FALSE rejection (the player already saw it).\n"
    "  `unearned_new`: neither. A probable TRUE leak.\n"
    "  `undecidable`: no term, or the run lacks the earlier turns needed.\n"
    "Process the 68 term-leak rejections found by the earlier measurement over the canonical sources in sources.json (skip files marked skipped_reason; apply the same SHA-256 and run de-duplication the earlier worker used: read measure.py and reuse its loading helpers by importing it with importlib from its absolute path, do not copy them). Write labels.json (one record per rejection: source file, run index, turn, term, label, player_input, recovered bool, 160-character excerpts of rejected and accepted narration) and report.md: counts and shares per label, recovered share per label, ten sample rows per label (all of them if fewer), a plain statement of what the labels do and do not prove (player_echo is a policy judgment about what the guard is for, not a proof; a candidate false rejection still needs the guard owner's decision), and the effect on the earlier numbers: if all candidate false rejections were accepted, how the visible-rejection rate (19 of 428 bench turns, 1 of 162 hosted) would change, stating how many of the 19 visible rejections are candidate false.\n"
    "TESTS (tests/test_adjudicate.py, pytest from inside tools_gates_r1b2 with `PYTHONPATH=$PWD`, fixtures in tmp_path, no repo imports other than measure.py via importlib): a term in the player command is player_echo; plural and possessive count; a term in an earlier accepted narration is previously_visible; a term only in LATER turns is not; a term nowhere is unearned_new; a missing term is undecidable; a message with a quoted term is parsed; first-match order (term in both command and earlier text is player_echo); the totals add up. At least 8 tests, under 5 seconds."
)

FILES_B = r"scripts/qualification/coverage_ledger\.py|tests/test_coverage_ledger\.py|\.plans/qualification/coverage-ledger\.md|tests/shard_durations\.json"

CHECK_LEDGER = f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK/out"
[ -e .venv ] || ln -s {REPO}/.venv .venv
git reset -q
git add -A -- . ':(exclude)NOTES.txt' ':(exclude)tools_gates_r1b2'
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^({FILES_B})$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
start=$(date +%s)
{PY} -m pytest -q -p no:cacheprovider tests/test_coverage_ledger.py tests/test_regen_shard_durations.py tests/test_shard_balance.py
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 120 s)"
[ "$took" -le 120 ] || {{ echo "over the 120 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
echo "ruff files: $PYFILES"
{PY} -m ruff check $PYFILES
{PY} -m ruff format --check $PYFILES
test -s .plans/qualification/coverage-ledger.md || {{ echo "ledger not written"; exit 1; }}
for s in 1A 1B 1C 2A 2B 2C 3A 3B 3C; do grep -q "$s" .plans/qualification/coverage-ledger.md || {{ echo "scene $s missing from ledger"; exit 1; }}; done
grep -qi 'unexamined' .plans/qualification/coverage-ledger.md || {{ echo "unexamined section missing"; exit 1; }}
! grep -q 'UNACCOUNTED' .plans/qualification/coverage-ledger.md || {{ echo "ledger has UNACCOUNTED realizations"; exit 1; }}
start=$(date +%s)
{PY} scripts/qualification/coverage_ledger.py --journeys --write "$WORK/out/ledger-recheck.md"
took=$(( $(date +%s) - start ))
echo "journey run took $took s (budget 300 s)"
[ "$took" -le 300 ] || {{ echo "journey run over the 300 s budget"; exit 1; }}
cmp "$WORK/out/ledger-recheck.md" .plans/qualification/coverage-ledger.md || {{ echo "ledger not deterministic"; exit 1; }}
git diff --cached > "$WORK/out/step6-ledger.patch"
test -s "$WORK/out/step6-ledger.patch"
"""

CHECK_R1B2 = f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK/out"
[ -e .venv ] || ln -s {REPO}/.venv .venv
git reset -q
tracked=$(git status --porcelain --untracked-files=no | grep -v '\\.venv' || true)
[ -z "$tracked" ] || {{ echo "tracked files changed: $tracked"; exit 1; }}
extra=$(git status --porcelain --untracked-files=all | grep '^??' | awk '{{print $2}}' | grep -vE '^(tools_gates_r1b2/|NOTES\\.txt$|\\.venv$|\\.serena)' || true)
[ -z "$extra" ] || {{ echo "files outside ownership: $extra"; exit 1; }}
cd tools_gates_r1b2
start=$(date +%s)
PYTHONPATH=$PWD {PY} -m pytest -q -p no:cacheprovider tests/test_adjudicate.py
took=$(( $(date +%s) - start ))
echo "tests took $took s (budget 30 s)"
[ "$took" -le 30 ] || {{ echo "over budget"; exit 1; }}
n=$(grep -c '^def test_' tests/test_adjudicate.py)
[ "$n" -ge 8 ] || {{ echo "expected at least 8 tests, found $n"; exit 1; }}
{PY} -m ruff check adjudicate.py tests/test_adjudicate.py
{PY} - <<'E'
import json
rows = json.load(open("labels.json"))
rows = rows if isinstance(rows, list) else rows["records"]
labels = {{r["label"] for r in rows}}
assert labels <= {{"player_echo", "previously_visible", "unearned_new", "undecidable"}}, labels
print("records", len(rows), "labels", sorted(labels))
assert len(rows) >= 40, "expected on the order of 68 rejections, got %d" % len(rows)
text = open("report.md").read().lower()
for need in ("player_echo", "previously_visible", "unearned_new", "undecidable", "does not prove", "19"):
    assert need in text, "report.md lacks " + need
E
mkdir -p "$WORK/out/r1b2"
cp labels.json report.md adjudicate.py "$WORK/out/r1b2/"
test -s "$WORK/out/r1b2/labels.json"
"""

common = {
    "task_type": "code-feature",
    "engine": "codex",
    "engine_args": ["-c", "model_reasoning_effort=medium"],
    "max_attempts": 2,
    "check_timeout_s": 600,
}
manifest = {
    "run_name": "qual-step6-ledger-r1b2",
    "workdir": WORK,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            **common,
            "key": "coverage-ledger",
            "timeout_s": 2400,
            "ownership": [
                "scripts/qualification/coverage_ledger.py",
                "tests/test_coverage_ledger.py",
                ".plans/qualification/coverage-ledger.md",
                "tests/shard_durations.json",
            ],
            "spec": SPEC_LEDGER,
            "check": CHECK_LEDGER,
            "expect_files": [],
            "verified": "Every storylet of the nine scenes is accounted reachable, observer-only or retired, deterministically.",
        },
        {
            **common,
            "key": "r1b2-term-leak-adjudication",
            "timeout_s": 1800,
            "ownership": [
                "tools_gates_r1b2/adjudicate.py",
                "tools_gates_r1b2/tests/test_adjudicate.py",
                "tools_gates_r1b2/labels.json",
                "tools_gates_r1b2/report.md",
            ],
            "spec": SPEC_R1B2,
            "check": CHECK_R1B2,
            "expect_files": [],
            "verified": "Recorded term-leak rejections are labelled player_echo, previously_visible, unearned_new or undecidable by a deterministic rule.",
        },
    ],
}
Path(__file__).with_name("round33b-ledger-r1b2-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
