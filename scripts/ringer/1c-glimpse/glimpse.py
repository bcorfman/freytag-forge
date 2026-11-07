# ruff: noqa: E501
"""1C glimpse manifest: the optional Michelle glimpse in the processing line becomes an uncertain sighting with guards who stop Kristin from checking. Story text only (plot.md, one knowledge entry) plus tests. Zero narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/1c-glimpse"

OLD_PLOT = "If she looks for Michelle, she glimpses a woman who could be her. Her face slips from sight before Kristin can be certain. The transfer is still moving."
NEW_PLOT = "If she looks for Michelle, she spots someone in the line who looks like Michelle, but she can't be sure. The woman goes around the corner out of sight before Kristin can be certain, and guards standing over the prisoners block her from investigating further. The transfer is still moving."
OLD_STATEMENT = "Kristin sees living captives in the processing line. She glimpses a woman who could be Michelle before the woman's face slips from sight."
NEW_STATEMENT = (
    "Kristin sees living captives in the processing line. She spots someone who looks like Michelle but cannot be sure."
)
NEW_DELIVERY_LEAD = "Kristin watches the sedated captives in the processing line. They are alive. She spots someone in the line who looks like Michelle, but she can't be sure. The woman goes around the corner out of sight before Kristin can be certain, and guards standing over the prisoners block her from investigating further. The transfer is still moving."

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD wording this task deliberately changes; never weaken, skip or delete any other test."""

SPEC = (
    COMMON
    + f"""

ROLE: story-text editor and test writer. You may edit/create ONLY: data/stories/continuity-initiative/plot.md (one exact replacement below), data/stories/continuity-initiative/knowledge.yaml (the `statement` and `delivery_text` of the single entry `k_sl_1c_b_r2`, nothing else), tests/test_richer_1c.py (add tests only unless an existing assertion pins the old wording), and any other test under tests/ (NOT under tests/fixtures/) that a failing test shows pins the OLD wording of this glimpse. Do NOT edit the 1C.2 `**Details:**` line (the loader allows 3 to 7 items and the line already has 7) and add no new scene thing, guard entity or placement: the guards are simply part of the facility. Never touch tests/fixtures/continuity_initiative_pre_3c_adoption/ (a frozen historical copy), world.yaml, storylet-routes.yaml, storylets.md, handoffs.yaml or any other story file.

BACKGROUND: Scene 1C has an optional reveal `k_sl_1c_b_r2` (earned by watching the processing line for Michelle). Kristin looks down the observation shaft at the processing line and glimpses someone who might be Michelle. The glimpse must stay UNCERTAIN: it asserts the facts `captives_confirmed_alive` and `michelle_possible_sighting` only, and nothing may say it was Michelle (plot.md: "Michelle's identity remains uncertain"). The story change gives the sighting a reason Kristin cannot check it: the woman goes around a corner and guards standing over the prisoners block her. Kristin already wants to find Michelle, so she is cued to see her; the text says only that the woman LOOKS like Michelle and that Kristin cannot be sure.

THE CHANGE (wording supplied; do not invent replacements; each old string occurs exactly once):
1. plot.md, in Scene 1C.2, replace exactly
   "{OLD_PLOT}"
   with exactly
   "{NEW_PLOT}"
2. knowledge.yaml, entry `k_sl_1c_b_r2`: replace the `statement` value (currently "{OLD_STATEMENT}") with exactly
   "{NEW_STATEMENT}"
   Keep `voiceable: false` and every other field. Replace ONLY the opening of its `delivery_text` (the text before "Brandon says,") so that it begins exactly:
   "{NEW_DELIVERY_LEAD}"
   followed by the existing "Brandon says, ..." remainder, which must stay word for word. Keep the YAML folded style (`>-`) that entry uses.

TESTS (first):
a. `k_sl_1c_b_r2`'s statement equals the new statement and its delivery_text starts with the new lead and ends with the unchanged Brandon sentences (assert the Brandon remainder as the literal text it has at HEAD: "Brandon says, \\"Copy the prisoner numbers if you want stronger proof. Or ask me about the transfer route. I can help with the service entrance. That will cost us the chance to copy the full set of numbers. There is time for one choice before the transfer leaves.\\"" after whitespace normalisation).
b. Every other field of `k_sl_1c_b_r2` is unchanged and written as literals in the test (read them from the file BEFORE you edit): voiceable false, earn_when, action_evidence, requires, establishes (exactly captives_confirmed_alive and michelle_possible_sighting, both true; no new fact), audience, available_in_scenes, source, relevance. Every OTHER knowledge entry is unchanged (compare the loaded package's other entries with the same entries loaded from tests/fixtures/continuity_initiative_pre_3c_adoption/ is NOT valid because that copy is older; instead assert in the test that the knowledge.yaml entry ids and the entry count are unchanged, and rely on the check script for the byte-level comparison).
c. The glimpse stays uncertain: neither the statement nor the delivery_text contains "is Michelle", "was Michelle", "it was her", "found Michelle", "confirmed" or "recogni" (case-insensitive), and no knowledge entry or storylet route establishes a fact for a confirmed 1C sighting.
d. The plot.md 1C.2 paragraph contains the new plot sentence exactly, no longer contains "slips from sight" or "could be her" in that scene, and the 1C.2 Details line is byte-identical to HEAD's.
e. The real engine path still works: with the existing helpers used by tests/test_richer_1c.py / tests/test_1c_offers.py, the command that earns `k_sl_1c_b_r2` still earns it and still offers Brandon's two choices exactly as before (the existing tests for these must pass unchanged).
f. The word "guards" in 1C must not break entity handling: `corridor_guards` is a group declared in world.yaml with scoped aliases [guards, guard] and placed only in a later scene. Run the package audit (storygame.audit audit_package, as tests/test_package_audit.py does) and the leak-scan/unavailable-entity tests; if any of them fails because of the new word "guards", DO NOT rename, alias, redeclare or place anything to work around it: report the exact failure and the test names in the final message (the task is then reported as blocked and the orchestrator decides).
g. Prompt size does not grow: tests/test_audit_budget.py has a ratchet (`test_real_package_ratchet`, fixture tests/fixtures/deep_turn_budget.json) that pins each scene's narrator prompt size and fails if it grows; 1C is pinned at 4,961. The new statement is shorter than the old one on purpose (the vivid detail lives only in the delivery text). Using the helpers in tests/test_prompt_budget.py, measure the 1C narrator prompt (system + user) at a state where `k_sl_1c_b_r2` is earned, before and after your change (record the before number BEFORE editing), assert in a test that the after-prompt is NOT longer than before, and state both numbers in the final message. tests/test_audit_budget.py and its fixture must pass UNCHANGED: never edit tests/fixtures/deep_turn_budget.json.
Then run: tests/test_richer_1c.py tests/test_richer_1c_voice.py tests/test_1c_closeout.py tests/test_1c_offers.py tests/test_1c_reading_pointer.py tests/test_continuity_1c_incident.py tests/test_delivery_echo.py tests/test_voiceable_knowledge.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_prompt_budget.py tests/test_spine_expected_reveals.py tests/test_knowledge_leakage_matrix.py tests/test_scene_1c_grounding.py tests/test_audit_budget.py tests/test_prompt_presence.py tests/test_speaker_presence.py tests/test_discovery_continuity.py tests/test_audit_unbound_item.py tests/test_world_placements.py, plus every test file whose grep for `k_sl_1c_b_r2`, `slips from sight`, `could be Michelle` or `michelle_possible_sighting` matched (excluding tests/fixtures). Do NOT raise any prompt-size ceiling to make a test pass.

FINAL MESSAGE: the plot.md and knowledge.yaml diffs, every test changed or added (one line each), the before/after prompt sizes, and anything surprising (especially anything about the word "guards").
"""
)

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in tests/fixtures/*) echo "WHY: frozen fixture edited: $f"; exit 1;; $D/plot.md|$D/knowledge.yaml|tests/*) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
git add -A -- $D tests
$PY - <<'E' || exit 1
import subprocess, yaml
D = "data/stories/continuity-initiative"
def head(path): return subprocess.run(["git", "show", f"HEAD:{path}"], capture_output=True, text=True, check=True).stdout
# plot.md: exactly the two supplied replacements
old, new = head(f"{D}/plot.md"), open(f"{D}/plot.md").read()
expect = old.replace("OLD_PLOT_X", "NEW_PLOT_X")
assert old.count("OLD_PLOT_X") == 1, "HEAD plot.md does not contain the old sentence once"
assert new == expect, "plot.md differs from HEAD by more than the one supplied replacement"
# knowledge.yaml: only statement and delivery_text of k_sl_1c_b_r2
a, b = yaml.safe_load(head(f"{D}/knowledge.yaml")), yaml.safe_load(open(f"{D}/knowledge.yaml"))
assert a.keys() == b.keys(), "top-level keys changed"
ea = {e["id"]: e for e in a["knowledge"]}; eb = {e["id"]: e for e in b["knowledge"]}
assert list(ea) == list(eb), "entry ids or order changed"
for k in ea:
    if k != "k_sl_1c_b_r2": assert ea[k] == eb[k], f"entry {k} changed"
ta, tb = dict(ea["k_sl_1c_b_r2"]), dict(eb["k_sl_1c_b_r2"])
assert tb["statement"] == "NEW_STATEMENT_X", f"statement wrong: {tb['statement']!r}"
assert " ".join(tb["delivery_text"].split()).startswith("NEW_LEAD_X"), "delivery lead wrong"
tail = lambda t: " ".join(t["delivery_text"].split()).split("Brandon says,", 1)[1]
assert tail(ta) == tail(tb), "Brandon remainder of the delivery changed"
for f in ("statement", "delivery_text"): ta.pop(f); tb.pop(f)
assert ta == tb, "another field of k_sl_1c_b_r2 changed"
for f in ("package-level top keys",): pass
other = {k: v for k, v in a.items() if k != "knowledge"}; other_b = {k: v for k, v in b.items() if k != "knowledge"}
assert other == other_b, "non-knowledge keys changed"
print("story diff exact")
E
$PY -m pytest -q -p no:cacheprovider tests/test_richer_1c.py tests/test_richer_1c_voice.py tests/test_1c_closeout.py tests/test_1c_offers.py tests/test_1c_reading_pointer.py tests/test_continuity_1c_incident.py tests/test_delivery_echo.py tests/test_voiceable_knowledge.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_prompt_budget.py tests/test_spine_expected_reveals.py tests/test_knowledge_leakage_matrix.py tests/test_scene_1c_grounding.py tests/test_audit_budget.py tests/test_prompt_presence.py tests/test_speaker_presence.py tests/test_discovery_continuity.py tests/test_audit_unbound_item.py tests/test_world_placements.py > /tmp/t1cg.out 2>&1; rc=$?; tail -25 /tmp/t1cg.out; [ $rc -eq 0 ] || { echo "WHY: suites failed (if the failure is about the word guard, the task is blocked: report it)"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
mkdir -p OUTDIR && git diff --cached > OUTDIR/glimpse.patch && wc -l OUTDIR/glimpse.patch && git diff --cached --stat | tail -12
""".replace("OUTDIR", OUT)
CHECK = (
    CHECK.replace("OLD_PLOT_X", OLD_PLOT)
    .replace("NEW_PLOT_X", NEW_PLOT)
    .replace("NEW_STATEMENT_X", NEW_STATEMENT)
    .replace("NEW_LEAD_X", NEW_DELIVERY_LEAD)
)

manifest = {
    "run_name": "1c-glimpse",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "glimpse",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "data/stories/continuity-initiative/plot.md",
                "data/stories/continuity-initiative/knowledge.yaml",
                "tests/test_richer_1c.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests added first, story diff exact, suites and ruff pass, patch exported",
        }
    ],
}
Path(__file__).with_name("glimpse-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
