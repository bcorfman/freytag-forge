"""Build the Ringer manifest that closes the producer/consumer audit gaps found in slice 4."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
DEPS = f"{REPO}/storygame/story_package/dependencies.py"
GAP = f"{REPO}/storygame/story_package/gap_rules.py"
GTEST = f"{REPO}/tests/test_gap_rules.py"
ITEST = f"{REPO}/tests/test_impact_report.py"
MODELS = f"{REPO}/storygame/story_package/models.py"
TTEST = f"{REPO}/tests/test_situation_trace.py"
GSCRIPT = f"{REPO}/scripts/gap_rules.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"
NAMES = "memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity|pursuit_1b"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {DEPS}, {GAP}, {GTEST} and {ITEST} (all exist; edit them). Touch nothing else (read {MODELS} but do not edit it).

PROBLEM. The new Layer 3 rules `no_producer` and `unread_effect` in {GAP} give about 10 and about 40 results on the real package (run `{ENV} && {PY} {REPO}/scripts/gap_rules.py <anchor>` for the anchors named in the existing real-package inventory test in {GTEST}). A previous worker classified them as missing audit kinds, not story gaps, and pinned them in an inventory test, which enshrines false positives. Fix the causes. Do not weaken the rules by raising thresholds or skipping facts by name.

CAUSE 1, rule logic (false-by-absence). A condition that requires a fact to be FALSE (FactPredicate.equals False, or the string/value forms the models use for false) is satisfied by absence: a fact that is not true at the start of the story is false until something sets it. In `no_producer`, a required value of false is producible when the fact is not true at the start; only when it is already true at the start (bootstrap state) does the false value need a producer that sets it false. Mirror how predicate_matches in {REPO}/storygame/runtime/validation.py treats an absent fact; follow that function, do not guess. An example from the real package: a pacing event whose `when` requires a fact to be false while a claim elsewhere sets it true must give NO no_producer result.

CAUSE 2, the consumer lookup in {DEPS} misses reading sites. Do a systematic audit, not a guess: walk every pydantic model reachable from StoryPackage in {MODELS} and list every field that can carry a fact id as a CONDITION or READ (fields typed FactPredicate, ActivationRule.all_facts_true and any_of, any field whose name contains 'trigger_fact', 'fact_id' used as a condition, 'when', 'requires', 'unlock_fact', completion or abort conditions of storylets or routes, canonical route event activation, ending and ending-variant `when`). Known missing: storylet completion/abort conditions, canonical route event activation conditions, StoryEnding and EndingVariant `when`. Add each missing site to `consumers()` with kind 'gate' (or 'wording' for variant selection of text) and a text in the same style as the existing ones. Do not change the text of existing consumers. Distinguish READS (conditions) from WRITES (effects, establishes, operations, costs): never count a write as a consumer.
Then add a COMPLETENESS TEST in {ITEST} that fails if a new reading site is added to the models and not handled: walk the model classes by introspection (pydantic model_fields and annotations) to find every condition-typed field, assert each is either in an explicit allowlist of (class, field) pairs consumed by `consumers()` or in an explicit allowlist of pairs that are deliberately not reads, with a comment-free reason string in the data. Also assert, for each fact id in the real package, that every occurrence of that fact in a condition-typed field found by the generic walk appears in consumers() for that fact (so the walk and the lookup agree on the real data).

AFTER THE FIX re-run both rules on EVERY pacing event, incident and transition anchor in the real package. Update the inventory test in {GTEST} to the new real results, whatever they are. Expect few or none. For every result that remains, classify it in your final message as a true story gap (give the story evidence, file and line, and why a reader would call it a gap) or a remaining audit hole (then fix the audit, do not pin it). Do not pin a result you believe is a false positive. If after real effort you cannot decide, pin it but name it in the final message as undecided.
Keep every existing test passing: {GTEST}, {ITEST}, {TTEST}. {GAP} and {DEPS} must contain no story names (no memory_card, kristin, patrol, laptop, k_sl_, t_1a, pursuit_1b, continuity), not even in comments. The measured case must still hold: removing every authored effect that sets kristin_marked_by_patrol still loads and still gives a no_producer result on the marked pursuit passage anchor `pursuit_1b`.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {GTEST} {ITEST} {TTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {DEPS} {GAP} {GTEST} {ITEST} && {PY} -m ruff check {DEPS} {GAP} {GTEST} {ITEST}`."""

CHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {DEPS} {GAP} {GTEST} {ITEST}
$PY -m ruff format --check {DEPS} {GAP} {GTEST} {ITEST}
if grep -n -i -E '{NAMES}' {DEPS} {GAP}; then echo 'STORY NAMES FOUND'; exit 1; fi
$PY -m pytest {GTEST} {ITEST} {TTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -12
$PY - <<'PY'
from pathlib import Path
from storygame.story_package.gap_rules import run_gap_rules
from storygame.story_package.loader import load_story_package
root = Path("{REPO}/data/stories/continuity-initiative")
package = load_story_package(root)
anchors = [e.id for e in package.pacing.events] + [i.id for i in package.incidents] + [t.id for t in package.pacing.transitions]
np_ = ue = 0
for a in anchors:
    for f in run_gap_rules(root, a, rules=["no_producer", "unread_effect"]):
        print(f.rule, a, f.subject)
        np_ += f.rule == "no_producer"
        ue += f.rule == "unread_effect"
print("REAL PACKAGE: no_producer", np_, "unread_effect", ue, "over", len(anchors), "anchors")
PY
$PY {GSCRIPT} pursuit_1b --rule no_producer | head -4
"""

manifest = {
    "run_name": "story-data-impact-report",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-impact-report",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "producer-consumer-audit-fix",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": [DEPS, GAP, GTEST, ITEST],
            "expect_files": [DEPS, GAP],
            "spec": SPEC,
            "check": CHECK,
            "verified": "false-by-absence conditions are not reported, every condition-reading site in the models is found by the consumer lookup (a completeness test enforces it), the measured case still reports, and the real-package results are re-listed",
        }
    ],
}
out = Path(__file__).with_name("slice4-audit-fix-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
