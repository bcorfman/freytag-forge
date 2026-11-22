# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 19k: fix two diagnosis weak spots (station 11) and add a claim-wording-miss cause. FREE to build.

One Codex task. Usage: build_round19k_diagnosis_weak_spots_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-diagnosis-weak-spots"
OWNED = [
    "factory/stations/diagnose.py",
    "factory/stations/planner.py",
    "tests/test_factory_diagnose.py",
    "tests/test_factory_planner.py",
]
ALLOW_RE = "^(factory/stations/(diagnose|planner)\\.py|tests/test_factory_(diagnose|planner)\\.py)$"

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model (not `claude`, not `codex`), NEVER use the network, NEVER run `python -m bench run`. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>`.

BACKGROUND. `factory/stations/diagnose.py` (station 11) gives every failing playtest turn one cause by deterministic rules read against the compiled story package (`diagnose_turn`, first match wins: match_miss_on_offered_candidate, claim_not_offered, lead_outside_scene, unknown_object, no_authored_outcome, unclear). The fixture `tests/fixtures/factory/stuck_packets_1a.json` holds 21 real turns; `tests/test_factory_diagnose.py` pins their current causes. Two weak spots are known. Fix them, story-agnostically (no story names, places or characters in code or in tests' expectations of the rules; tests may use the real fixture and the real package like the existing tests do).

WEAK SPOT 1: an unknown modifier hides a known entity. "Question the approaching officer about Michelle." is labelled `unknown_object` only because the modifier "approaching" is not in the story vocabulary, though the command names a scene entity (the officer) and an acting verb. Fix, two parts, both in the unknown-word step: (a) a word also counts as known when a simple stem of it is in the vocabulary (strip one common suffix: `ing`, `ed`, `es`, `s`; also try `ing` -> restore a final `e`; keep it small, pure and tested); (b) an unknown word that sits immediately before a word of a named in-scene entity's surface form in the player's command (a modifier of a known thing) is ignored. After the change, a command whose only unknown words are such stems or modifiers falls through to the later rules. Genuinely unknown things stay `unknown_object` (a warehouse, a hidden compartment, a note).

WEAK SPOT 2: a verb the claim does not list. "Question Walt Pruitt about Michelle." is `no_authored_outcome`, though an authored claim for that person exists and misses only because "question" is not among its matcher verbs. Add a NEW cause `claim_wording_miss` (rule-decided, placed right AFTER `claim_not_offered` and BEFORE `lead_outside_scene` in `diagnose_turn`): a claim of the scene (`_claims_with_evidence`) whose `action_evidence` has at least 2 groups where the command satisfies every group but exactly one. Signals: `claim_ids` (sorted, all such claims), `missing` (a list of {claim_id, group} with the 0-based group index that did not match) and `decided_by` "rule". `why` is one plain sentence naming the claims. Do not offer claims that are the same claim already reported by `claim_not_offered` (that rule runs first and wins). Keep `CAUSES` a tuple in a stable order but put the new cause after `claim_not_offered`; REMOVE the position-based uses (`CAUSES[0]` ... `CAUSES[4]`, `CAUSES[:5]`) in the module and use named constants or names instead, so the order of CAUSES can never change a rule; the classifier fallback may choose any cause except `unclear`. Update `DIAGNOSE_BRIEF` with one line for the new cause (the brief says "first five causes": make it say every cause except unclear, in plain words). Bump `DIAGNOSE_VERSION` to `diagnose-v2` so saved diagnoses are recomputed. The summary function and counts must work with the new cause unchanged (they iterate CAUSES).

PLANNER. In `factory/stations/planner.py` find where `PLANNER_BRIEF` explains the diagnosis causes (the sentence that tells the planner to target the most common cause a proven technique can fix). Add exactly ONE short plain sentence: a `claim_wording_miss` turn names a claim that misses only one wording; the `edit_claim_evidence` kind fits it when the failing turn's own words supply the phrase. Change no other sentence. Existing planner tests that pin the brief should only change as that one sentence requires.

TESTS. Update `tests/test_factory_diagnose.py` (keep it under 15 seconds, hermetic, no model call): (1) the real-fixture test of causes keeps passing for every turn EXCEPT the ones named here; update only those pinned values: `smoke18c-1A-r2-t9` becomes `no_authored_outcome`; `smoke18c-1A-r2-t12` becomes `claim_wording_miss`; turns `smoke18c-1A-r1-t4`, `smoke18c-1A-r2-t6`, `smoke18c-1A-r3-t5`, `smoke18c-1A-r3-t6` and `smoke18c-1A-r3-t9` may become `claim_wording_miss` if and only if the rule genuinely finds a claim missing one group (print what the rule found in NOTES_19K.txt and keep them as pinned truth either way); every other turn keeps its current cause; (2) unit tests of the stem rule and the modifier rule with small synthetic packages or the real package, including a negative test that "Go to the old warehouse." stays `unknown_object` and that `Take the note from the hidden compartment.` stays `unknown_object`; (3) tests of the new rule: a passing case, a case where the command satisfies all groups (not this rule), a case where two groups miss (not this rule), a single-group claim (not this rule), and that `claim_not_offered` still wins when the claim is both unoffered and fully matched; (4) CAUSES contains the new cause, `unclear` is still last, and a classifier reply naming `claim_wording_miss` is accepted while `unclear` from the classifier is not. Update `tests/test_factory_planner.py` only if a pinned brief test needs the one new sentence.

HARD LIMITS. Edit only the owned files: @OWNED@. NEVER edit `factory/line.py`, `fix_plan.py`, `wiring.py`, `probe.py`, `tickets.py`, `factory/config/*`, story data under `data/`, `bench/`, `storygame/` or the fixture file. Write NOTES_19K.txt (worktree root, never committed) listing every ambiguity and your choice, plus the final cause for each of the 21 fixture turns."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- factory tests
bad=$(git diff --cached --name-only | grep -vE '@ALLOW_RE@' || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
git status --porcelain -- data tests/fixtures | grep . && { echo "story data or fixture changed"; exit 1; } || true
grep -q "claim_wording_miss" factory/stations/diagnose.py || { echo "new cause missing in diagnose.py"; exit 1; }
grep -q "claim_wording_miss" factory/stations/planner.py || { echo "planner sentence missing"; exit 1; }
grep -q "diagnose-v2" factory/stations/diagnose.py || { echo "version not bumped"; exit 1; }
if grep -n "CAUSES\\[" factory/stations/diagnose.py; then echo "position-based CAUSES use remains"; exit 1; fi
if grep -n -i -E "michelle|kristin|walt|reyes|officer|warehouse|compartment" factory/stations/diagnose.py; then echo "story-specific word in diagnose.py"; exit 1; fi
cat > "$WORK/out/verify_fixture.py" <<'PYV'
import json
from pathlib import Path
from factory.stations.diagnose import diagnose_turns
from factory.stations.wiring import _story_root
from storygame.story_package.loader import load_story_package

package = load_story_package(_story_root(Path(".")))
packets = json.load(open("tests/fixtures/factory/stuck_packets_1a.json"))
got = {p["key"]: r["cause"] for p, r in zip(packets, diagnose_turns(packets, package))}
base = {
    "smoke18c-1A-r1-t6": "lead_outside_scene", "smoke18c-1A-r1-t8": "lead_outside_scene",
    "smoke18c-1A-r1-t9": "lead_outside_scene", "smoke18c-1A-r1-t10": "unknown_object",
    "smoke18c-1A-r1-t11": "unknown_object", "smoke18c-1A-r1-t12": "unknown_object",
    "smoke18c-1A-r1-t13": "unknown_object", "smoke18c-1A-r2-t4": "claim_not_offered",
    "smoke18c-1A-r2-t11": "match_miss_on_offered_candidate", "smoke18c-1A-r2-t13": "claim_not_offered",
    "smoke18c-1A-r3-t3": "claim_not_offered", "smoke18c-1A-r3-t11": "lead_outside_scene",
    "smoke18c-1A-r3-t12": "lead_outside_scene", "smoke18c-1A-r3-t13": "lead_outside_scene",
}
bad = {k: (v, got.get(k)) for k, v in base.items() if got.get(k) != v}
assert not bad, f"turns that must not change did change: {bad}"
assert got["smoke18c-1A-r2-t9"] == "no_authored_outcome", got["smoke18c-1A-r2-t9"]
assert got["smoke18c-1A-r2-t12"] == "claim_wording_miss", got["smoke18c-1A-r2-t12"]
flex = ["smoke18c-1A-r1-t4", "smoke18c-1A-r2-t6", "smoke18c-1A-r3-t5", "smoke18c-1A-r3-t6", "smoke18c-1A-r3-t9"]
for k in flex:
    assert got[k] in {"no_authored_outcome", "claim_wording_miss"}, (k, got[k])
assert "unclear" not in got.values(), got
print("fixture causes ok:", json.dumps(got, indent=0))
PYV
.venv/bin/python "$WORK/out/verify_fixture.py"
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 tests/test_factory_diagnose.py
took=$(( $(date +%s) - start ))
echo "diagnose tests took $took s (budget 15 s)"
[ "$took" -le 15 ] || { echo "over the 15 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_factory_planner.py tests/test_factory_fix_plan.py tests/test_factory_wiring.py tests/test_factory_line.py tests/test_factory_stations.py tests/test_factory_probe_routing.py tests/test_factory_followups.py tests/test_factory_frozen.py
took=$(( $(date +%s) - start ))
echo "factory tests took $took s (budget 150 s)"
[ "$took" -le 150 ] || { echo "over the 150 s budget"; exit 1; }
.venv/bin/python -m ruff check factory tests/test_factory_diagnose.py tests/test_factory_planner.py
.venv/bin/python -m ruff format --check factory tests/test_factory_diagnose.py tests/test_factory_planner.py
[ ! -e factory/state/ledger.jsonl ] || { echo "a test wrote factory/state/ledger.jsonl"; exit 1; }
git diff --cached > "$WORK/out/diagnosis-weak-spots.patch"
test -s "$WORK/out/diagnosis-weak-spots.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return (
            text.replace("@REPO@", REPO)
            .replace("@WORK@", WORK)
            .replace("@OWNED@", ", ".join(OWNED))
            .replace("@ALLOW_RE@", ALLOW_RE)
        )

    return {
        "run_name": "factory-diagnosis-weak-spots",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "diagnosis-weak-spots",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 3000,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "Station 11 no longer blames an unknown modifier or a word's inflection for a command that names a scene entity, and a new rule-decided cause names claims that miss exactly one matcher group; the 21 real turns keep every other cause.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round19k-diagnosis-weak-spots-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
