"""Build the Ringer manifest that fixes the two slice 1 thin spots in the situation trace."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
TRACE = f"{REPO}/storygame/story_package/situation_trace.py"
GAP = f"{REPO}/storygame/story_package/gap_rules.py"
TTEST = f"{REPO}/tests/test_situation_trace.py"
GTEST = f"{REPO}/tests/test_gap_rules.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python, never --cov. You own ONLY {TRACE}, {GAP}, {TTEST} and {GTEST} (all exist). Touch nothing else.

BACKGROUND. {TRACE} renders a read-only 'situation trace' for an anchor (pacing event, incident or transition). Its output is used as a BLIND packet for reviewers, so it must stay data only: it must NEVER contain flags, gaps, responses, judgments, a '## 4.' or '## 5.' section, a '| Response |' table, or the words 'flag' or 'gap' as findings. Two thin spots were found; fix both.

THIN SPOT 1. For a transition anchor, section '## 1. The situation' shows only 'Transition X goes from scene A to scene B at priority N.' and no prose about the situation. Add the source scene's authored situation: package.knowledge.scene_frames has a SceneFrame per scene (scene_id, situation, pressure). For a transition anchor, add under the existing bullet: '- Situation in scene <source>: <situation>' (omit the line when the frame's situation is empty) and '- Pressure in scene <source>: <pressure>'. Use the frame of transition.source_scene_id. Do the same for pacing-event anchors (event.scene_id) and incident anchors (incident.scene_id) so the three anchor kinds behave alike. Quote the text exactly as authored; do not paraphrase.

THIN SPOT 2. The '### What the engine checks to deliver these' table ends with the fixed sentence 'It does not check who holds anything.' That is a claim about the engine that nothing computes. Replace it with a computed result. In {GAP} add a public function `custody_checks(package, anchor) -> list[CustodyCheck]` (a frozen dataclass: claim_id, item_id, character_id, holder_checked: bool). It reuses the existing baseline and hypothetical-move machinery of the custody rule (read _custody_findings and its helpers) but returns a row for EVERY claim/item pair the custody rule evaluates (same candidates, same baseline requirements), not only those that would be flagged: holder_checked is True when moving the item to another character makes the claim ineligible, False when the claim stays eligible. {GAP} must keep containing no story names (no memory_card, kristin, patrol, laptop, k_sl_, t_1a, continuity, not even in comments). Do not change what the three existing rules flag. In {TRACE}, under the table, print one line per CustodyCheck: 'Claim `<claim>`: the engine <does|does not> check whether `<character>` holds `<item>` (tested by moving it).' When there are no checks, print 'No held item is named by these claims.' Import from the gap_rules module; no circular import.

TESTS. Extend {TTEST}: (a) the transition anchor 't_1b_1c' and the pacing anchor 'officer_presses_1a' show a 'Situation in scene' or 'Pressure in scene' line whose text equals the SceneFrame text from the loaded package (resolve it from the package, do not hardcode prose); (b) for 'officer_presses_1a' the output has a 'does not check whether' line naming the memory card's holder test, resolved from the custody_checks() result rather than a literal string where possible; (c) a seeded-clean case: in a tmp_path copy, so the engine does check (find the smallest valid edit that makes the claim ineligible when another character holds the item; if the engine has no such mechanism, say so in your final message and test the 'does check' branch by calling the renderer with a patched custody_checks result via monkeypatch); (d) keep the existing blind-packet tests passing, they forbid the '## 4.' and '## 5.' sections and '| Response |'. Extend {GTEST} with a test that custody_checks returns a row for every pair the custody rule flags, with holder_checked False for each flagged pair.

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {TTEST} {GTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {TRACE} {GAP} {TTEST} {GTEST} && {PY} -m ruff check {TRACE} {GAP} {TTEST} {GTEST}`. Print a trace with `{ENV} && {PY} {REPO}/scripts/situation_trace.py t_1a_1b`."""

CHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {TRACE} {GAP} {TTEST} {GTEST}
$PY -m ruff format --check {TRACE} {GAP} {TTEST} {GTEST}
if grep -n -i -E 'memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity' {GAP}; then echo 'STORY NAMES FOUND in gap_rules'; exit 1; fi
$PY -m pytest {TTEST} {GTEST} -q --no-cov -p no:cacheprovider 2>&1 | tail -12
$PY {REPO}/scripts/situation_trace.py t_1a_1b > /tmp/trace-t1a1b.md
cat /tmp/trace-t1a1b.md | head -40
grep -q 'Situation in scene\\|Pressure in scene' /tmp/trace-t1a1b.md
if grep -q 'It does not check who holds anything' /tmp/trace-t1a1b.md; then echo 'old fixed sentence still present'; exit 1; fi
if grep -n -i -E '## 4\\.|## 5\\.|\\| Response \\||flag' /tmp/trace-t1a1b.md; then echo 'trace is no longer blind-safe'; exit 1; fi
$PY {REPO}/scripts/gap_rules.py officer_presses_1a | grep -c '^### '
"""

manifest = {
    "run_name": "story-data-gap-rules",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-gap-rules",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "trace-thin-spots",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 900,
            "ownership": [TRACE, GAP, TTEST, GTEST],
            "expect_files": [TRACE, TTEST],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the trace shows the authored scene situation for every anchor kind, the engine-checks table reports a computed custody result instead of a fixed sentence, and the trace stays free of flags and findings",
        }
    ],
}
out = Path(__file__).with_name("slice2-trace-spots-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
