"""Build the Ringer manifests for slice 4: shared dependency lookup + impact report, then the two producer/consumer rules."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
DEPS = f"{REPO}/storygame/story_package/dependencies.py"
IMPACT = f"{REPO}/storygame/story_package/impact_report.py"
ISCRIPT = f"{REPO}/scripts/impact_report.py"
ITEST = f"{REPO}/tests/test_impact_report.py"
TRACE = f"{REPO}/storygame/story_package/situation_trace.py"
TTEST = f"{REPO}/tests/test_situation_trace.py"
GAP = f"{REPO}/storygame/story_package/gap_rules.py"
GTEST = f"{REPO}/tests/test_gap_rules.py"
GSCRIPT = f"{REPO}/scripts/gap_rules.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"
NAMES = "memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity|pursuit_1b"
HARD = (
    "HARD RULE: the new modules and scripts contain NO story names (no memory_card, kristin, patrol, laptop, k_sl_, "
    "t_1a, pursuit_1b, continuity), not even in comments or docstrings. Everything comes from the loaded StoryPackage. "
    "Tests may name story ids."
)

SPEC1 = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY these files: {DEPS} (create), {IMPACT} (create), {ISCRIPT} (create), {ITEST} (create), {TRACE} (edit) and {TTEST} (edit). Touch nothing else.

BACKGROUND. {TRACE} has private helpers `_producers(package, fact_id, value)`, `_consumers(package, fact_id, exclude_transition_id=None)` and `_operation_value` that answer 'what can set this fact' and 'what reads this fact'. A new impact report needs the same answers, so they must live in one shared module, not be copied.

STEP 1, shared lookup in {DEPS}: move those helpers there as PUBLIC functions with typed results: `producers(package, fact_id, value=True) -> list[Producer]` and `consumers(package, fact_id, exclude_transition_id=None) -> list[Consumer]`, where Producer and Consumer are frozen dataclasses (Producer: kind, record_id, scene_id (str | None), text; Consumer: kind in {{'gate','wording','world'}}, record_id, text). `text` must equal the strings the trace prints today so the trace output stays byte-identical. Keep the discovery behaviour exactly as it is now EXCEPT: audit every way a fact can become true at runtime and add the missing producer kinds so none is silently absent. Audit by reading {REPO}/storygame/runtime/engine.py, state.py, validation.py and the story_package models: canonical bridge events and storylet-route realization operations (package.storylet_routes), incident outcome advantages/costs if they assert facts, scene entry facts, FactDelivery costs, ending markers if they assert, and world effects that assert. Add each kind that really asserts the fact with a Producer of its own kind name. Do not add a kind you cannot show asserts a fact. Report in your final message which kinds you added, and which you checked and rejected, each with the code location. Update {TRACE} to import from {DEPS} and delete its private copies. The existing {TTEST} must pass UNCHANGED for the existing assertions, and the rendered output for officer_presses_1a, i_2a_real_leak and t_1b_1c must be byte-identical to before except where an added producer kind appears (capture them before editing, in the scratchpad, and compare after; report any difference).

STEP 2, the impact report in {IMPACT}: `render_impact_report(root: Path, subject: str) -> str`. The subject resolves, in order, among: a fact id (package.knowledge.facts), a claim id (package.knowledge.knowledge), a pacing event id, a transition id, a storylet id. Zero matches -> ValueError("unknown subject '<s>'"); more than one kind -> ValueError("ambiguous subject '<s>': <kinds>"). Output is markdown, read-only, data only (no judgments, no 'flag', no 'gap', no proposals), title '# Impact report: <subject>', and one sentence 'Generated from the current story files. Read-only; edit the sources, not this page.' Sections for a FACT: '## Set by' (every producer with its kind, record id, scene), '## Read by' (every consumer with kind and record id), '## Claims' (claims that establish it and claims that require it, with ids), '## Tests that name it' (below). For a CLAIM: what it requires (each required fact with its producers), what it establishes (each fact with its consumers), its source storylet or realization, and the tests that name it. For a PACING EVENT, TRANSITION or STORYLET: the facts it reads (when, triggers, activation conditions, realization when) each with its producers, the facts it sets each with its consumers, then the tests that name it. When a list is empty print '- none'. 'Tests that name it': scan {REPO}/tests/*.py (top level only; skip tests/fixtures and anything under bench/frozen) for lines containing the id as a whole token; print up to 5 'tests/file.py:LINE' per file, files sorted, at most 20 lines total, then '(N more)' if truncated; label the section so it is clear these are textual matches of the id, not proof the test covers it. Deterministic output. Cite a story source location 'file.yaml:LINE' for a record only on a line that defines it (a line `- id: X`, `{{id: X, ...}}` or a bare `X:` key); omit otherwise. Never invent one.

STEP 3: {ISCRIPT}: argparse subject, --root (default {REPO}/data/stories/continuity-initiative); prints the report; exit 0; exit 2 with the ValueError text on stderr. Mirror {REPO}/scripts/situation_trace.py.

STEP 4, tests in {ITEST} (compact, shared helpers): one subject of each kind renders every section; the Set by list for a fact equals what dependencies.producers returns; an empty producer list prints '- none'; unknown and ambiguous subjects raise ValueError (build the ambiguous one in a tmp_path copy as {REPO}/tests/test_situation_trace.py does); output is deterministic; the story files are byte-identical before and after; the test-name scan finds this test file's own id token in a synthetic tmp_path layout (make the tests directory scanned a parameter `tests_dir` with the repo default so tests can pass a tmp dir); {DEPS}, {IMPACT} and {ISCRIPT} contain none of the story words (read the files and assert). Add to {TTEST} one test that the trace imports the shared lookup (the trace module has no `_producers` or `_consumers` left).
{HARD}

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {ITEST} {TTEST} {REPO}/tests/test_gap_rules.py -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {DEPS} {IMPACT} {ISCRIPT} {ITEST} {TRACE} {TTEST} && {PY} -m ruff check {DEPS} {IMPACT} {ISCRIPT} {ITEST} {TRACE} {TTEST}`. Try it: `{ENV} && {PY} {ISCRIPT} kristin_marked_by_patrol`."""

CHECK1 = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {DEPS} {IMPACT} {ISCRIPT} {ITEST} {TRACE} {TTEST}
$PY -m ruff format --check {DEPS} {IMPACT} {ISCRIPT} {ITEST} {TRACE} {TTEST}
if grep -n -i -E '{NAMES}' {DEPS} {IMPACT} {ISCRIPT}; then echo 'STORY NAMES FOUND'; exit 1; fi
if grep -n 'def _producers\\|def _consumers' {TRACE}; then echo 'private copies still in the trace'; exit 1; fi
$PY -m pytest {ITEST} {TTEST} {REPO}/tests/test_gap_rules.py -q --no-cov -p no:cacheprovider 2>&1 | tail -12
$PY {ISCRIPT} kristin_marked_by_patrol > /tmp/impact-fact.md
head -40 /tmp/impact-fact.md
grep -q 'Set by' /tmp/impact-fact.md && grep -q 'Read by' /tmp/impact-fact.md && grep -q 'Tests that name it' /tmp/impact-fact.md
test "$($PY {ISCRIPT} nope_not_a_subject 2>/dev/null; echo $?)" = 2
"""

SPEC2 = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {GAP} and {GTEST} (both exist; edit them). Do not touch {GSCRIPT} (it takes --rule names from the registry), the dependencies module, or any other file.

BACKGROUND. {GAP} is a registry `RULES` of Layer 3 'story rules': deterministic, they REPORT results and never block or raise on a result. {DEPS} (created by the previous task) provides public `producers()` and `consumers()`. Read {GAP}, {DEPS}, {REPO}/docs/story-gap-guide.md and {REPO}/.plans/story-data-redesign-plan.md section 6 (Slice 4) first.

ADD two rules to RULES, same signature (package, root, anchor, exits) -> list[Flag]; reuse the existing Flag dataclass, citation helper and citation rules (a location only for a line that defines the named record; otherwise none). Both use {DEPS}; do not copy producer or consumer discovery.

RULE 'no_producer' (a condition with no producer). Scope = the conditions the anchor itself and its exits read: for a pacing-event anchor, the event's `when` facts and every realization's `when` facts; for every anchor, each exit transition's triggers and the `requires` of the exit claims (as the other rules compute them); for an incident anchor, the successor transition's triggers. For each (fact_id, required value) in scope: if `producers(package, fact_id, value)` is empty AND the fact is not true at the start of the story (bootstrap a RuntimeState and check) AND no other mechanism makes it true (the producer audit in {DEPS} decides that; do not special-case), emit a Flag: rule 'no_producer', subject = the fact id, summary '<record kind> <record id> reads <fact> but nothing can set it.', evidence: the record that reads it (with its defining location), 'Set by: nothing found', and the consumers list for that fact.

RULE 'unread_effect' (an effect read by nothing). Scope = the facts the anchor sets: a pacing event anchor's `effects`, the `establishes` of the exit claims, an incident anchor's outcome advantages and costs. For each fact with NO consumer at all (a wording-only consumer counts as read; no consumer of any kind does not): emit a Flag: rule 'unread_effect', subject = fact id, summary '<record kind> <record id> sets <fact> but nothing reads it.', evidence: the setting record with location where it defines one, 'Read by: nothing'. A fact that a transition trigger, a pacing condition, a claim requirement, a storylet activation, a world effect or guard reads is read.

HARD RULE: {GAP} contains no story names (no memory_card, kristin, patrol, laptop, k_sl_, t_1a, pursuit_1b, continuity), not even in comments.

TESTS in {GTEST}. Each rule gets a seeded-defect test and a clean-story test, built in tmp_path copies of data/stories/continuity-initiative (shutil.copytree; edit YAML with yaml.safe_load and yaml.safe_dump like the existing tests). THE MEASURED CASE for no_producer: the fact kristin_marked_by_patrol is set by authored effects (see where it is asserted: grep the yaml files) and read by the marked passage of the pacing event `pursuit_1b` (a realization `when`). Remove every authored effect that asserts kristin_marked_by_patrol in a tmp_path copy (find them: pacing events, claims' establishes, route operations, deliveries); the copy must still LOAD (assert load_story_package succeeds on it, to show the loader misses the defect), and run_gap_rules(root, 'pursuit_1b', rules=['no_producer']) must flag kristin_marked_by_patrol. The unedited package gives no no_producer result for that anchor. For unread_effect make the smallest valid edit that leaves a set fact with no reader (for example give an existing pacing event an extra effect on a fact that is declared in the three fact lists but read by nothing; find how the existing tests add a synthetic fact, such as the _add_world_fact helpers in {REPO}/tests/test_exit_backstop_invariant.py) and assert the flag; the clean variant removes the extra effect. Also: run BOTH rules on the real package for EVERY pacing event, incident and transition anchor and collect all results; in your final message list every real result and classify each as a true story gap or a missing producer/consumer kind in the audit; if any are missing kinds, say which and stop without weakening the rules. Add a test that asserts the real-package results for the anchors equal the set you found and explained (keep it small, and name the anchors). Keep every existing test passing.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {GTEST} {REPO}/tests/test_situation_trace.py -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {GAP} {GTEST} && {PY} -m ruff check {GAP} {GTEST}`. Run: `{ENV} && {PY} {GSCRIPT} pursuit_1b`."""

CHECK2 = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {GAP} {GTEST}
$PY -m ruff format --check {GAP} {GTEST}
if grep -n -i -E '{NAMES}' {GAP}; then echo 'STORY NAMES FOUND in gap_rules'; exit 1; fi
grep -q "no_producer" {GAP} && grep -q "unread_effect" {GAP}
$PY -m pytest {GTEST} {REPO}/tests/test_situation_trace.py {REPO}/tests/test_impact_report.py -q --no-cov -p no:cacheprovider 2>&1 | tail -12
$PY {GSCRIPT} pursuit_1b --rule no_producer | head -10
test "$($PY {GSCRIPT} officer_presses_1a | grep -c '^### ')" -ge 5
"""


def task(key, spec, check, own, expect, verified, effort="high"):
    return {
        "key": key,
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", f"model_reasoning_effort={effort}"],
        "max_attempts": 2,
        "timeout_s": 2400,
        "check_timeout_s": 900,
        "ownership": own,
        "expect_files": expect,
        "spec": spec,
        "check": check,
        "verified": verified,
    }


def write(name, t):
    out = Path(__file__).with_name(name)
    out.write_text(
        json.dumps(
            {
                "run_name": "story-data-impact-report",
                "workdir": "/home/bcorfman/dev/ringer-work/story-data-impact-report",
                "max_parallel": 1,
                "worktrees": False,
                "repo": REPO,
                "tasks": [t],
            },
            indent=2,
        )
        + "\n"
    )
    print(out)


write(
    "slice4-impact-report-manifest.json",
    task(
        "impact-report",
        SPEC1,
        CHECK1,
        [DEPS, IMPACT, ISCRIPT, ITEST, TRACE, TTEST],
        [DEPS, IMPACT, ISCRIPT, ITEST],
        "producer and consumer lookup lives in one shared module used by the trace and the new impact report, the report prints set-by, read-by, claims and textual test matches for a fact, claim, event, transition or storylet, and the trace output is unchanged",
    ),
)
write(
    "slice4-producer-rules-manifest.json",
    task(
        "producer-consumer-rules",
        SPEC2,
        CHECK2,
        [GAP, GTEST],
        [GAP, GTEST],
        "a condition with no producer and an effect read by nothing are reported as rule results, the measured case (removing the effects that set the mark) still loads but is reported on the marked pursuit passage, and the real package results are listed and explained",
    ),
)
