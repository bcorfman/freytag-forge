"""Build the Ringer manifest for slice 2, task 2: the gap rules (layer 3)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
MOD = f"{REPO}/storygame/story_package/gap_rules.py"
SCRIPT = f"{REPO}/scripts/gap_rules.py"
TEST = f"{REPO}/tests/test_gap_rules.py"
ROOT = f"{REPO}/data/stories/continuity-initiative"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"

SPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python. You own ONLY these three NEW files: {MOD}, {SCRIPT}, {TEST}. Edit nothing else: no story data, no engine, no other test, no doc. Another worker already added World.holds(holder_id, entity_id) to packages/worldkeeper/src/worldkeeper/model.py; use it for custody.

BACKGROUND. docs/story-gap-guide.md defines three checks every situation must run: (1) custody: an action that uses an item requires the actor to hold it; (2) co-location: it also requires the actor to be where any device the prose names for it is; (3) no strand: with 1 and 2 applied as a hypothetical, every response to a pressure still leaves an authored path to the exit. A working but Reyes-specific, hardcoded prototype is .plans/story-data-phase0/render_trace.py (read its simulate(), after_departure() and Gap 1/2/3 sections). Slice 1 is {REPO}/storygame/story_package/situation_trace.py (read it: it has _producers, _consumers and anchor handling you may mirror but must not edit). YOUR JOB: port the three checks into a story-agnostic registry. These are Layer 3 'story rules': deterministic, they may run the real engine, they REPORT FLAGS and never block anything and never raise on a flag. Layer 4 judgment (is a response plausible, what repair) is NOT your job: no responses table, no proposals.

HARD RULE: {MOD} and {SCRIPT} must contain NO story names. No fact id, entity id, claim id, scene id or word from the continuity-initiative story (not memory_card, kristin, patrol, laptop, k_sl_, t_1a, etc.) anywhere, even in comments. Everything comes from the loaded StoryPackage. The tests may name story ids.

MODULE API in {MOD}:
  @dataclass(frozen=True) class Flag: rule: str; anchor: str; subject: str (the claim id); summary: str (one plain sentence); evidence: tuple[str, ...] (plain lines; each line that quotes or names a story record ends with its source location 'file.yaml:LINE' found by scanning the package root's *.yaml and *.md files for the first line containing 'id: <record id>' or the record id; if not found omit the location and NEVER invent one).
  RULES: dict[str, Callable] registry with exactly three entries named 'custody', 'co_location', 'no_strand'. Each rule takes (package, root, anchor, exits) and returns a list of Flag.
  exit_transitions(package, anchor) -> list[Transition]: pacing event anchor -> transitions whose source_scene_id == event.scene_id sorted by (priority, id); incident anchor -> its successor_transition_id transition (or none); transition anchor -> itself. Unknown anchor -> ValueError("unknown anchor '<a>'"); an anchor matching more than one kind -> ValueError("ambiguous anchor ..."), same wording as situation_trace.
  run_gap_rules(root: Path, anchor: str, rules: Iterable[str] | None = None) -> list[Flag]: loads load_story_package(root); unknown rule name -> ValueError. Flags sorted by (rule, subject, summary). Deterministic.
  render_flags(flags, anchor) -> str: markdown. Title '# Gap flags: <anchor>', then one sentence 'Layer 3 story rules. Flags are reported, never block a build, and are not judgments; read the evidence.', then per flag '### <rule>: <subject>', the summary, and the evidence as bullets. With none: 'No flags.' Read-only.

EXIT CLAIMS. For the anchor's exit transitions, the exit claims are the knowledge claims (package.knowledge.knowledge) whose `establishes` effects set a fact (fact_id equals value) that one of the transition's triggers requires (see _append_claim_checks in situation_trace.py for the matching).

BASELINE STATE for one exit claim (helper, shared by the rules): state = RuntimeState.bootstrap(package) (it starts in the first scene; seeds the world, applies placements and world effects). If the transition's source_scene_id differs from state.current_scene_id, also call apply_scene_placements(package, state.facts, source_scene_id) and set state.current_scene_id to it. Assert true (Fact(predicate=fact_id, subject='story', value='true')) every fact in claim.requires, every `when` fact of the anchor event (event anchors only), and every trigger fact of the exit transition that this claim does NOT establish (they have already happened by the time the player can use the claim). Then apply_world_effects(package, state.facts). Add the claim's source storylet id to state.active_event_ids (when the source has one). If explain_reveal(state, 'player', claim).reason (storygame/runtime/reveal_eligibility.py) is not 'eligible' at baseline the claim cannot be assessed: produce NO flag for it. world = world_for(package, state.facts) (storygame/runtime/world_model.py); protagonist = package.world.protagonist_id.

Candidate items for a claim: entity ids in claim.entity_ids plus claim.relevance.entity_ids that exist in the world, world.is_item(id) is true, and the schema does not mark them fixed (WorldSchema.is_fixed, reached through world.schema or the equivalent attribute of World; look at how the model exposes it).

RULE custody: for each candidate item with world.holds(protagonist, item) true at baseline: choose a different character: the sorted-first character in the world that is not the protagonist and is world.together(protagonist, character) at baseline; if none, no flag for this item. Move the item to that character (world.move(item, character), a hypothetical on this scratch state only), recompute explain_reveal; if still 'eligible' emit a Flag: summary like 'Claim <id> names <item> but the engine lets the protagonist use it while <character> holds it.' Evidence: the claim record location; the transition trigger it supports; the line 'holder at baseline: <protagonist>; after the hypothetical move: <character>; engine verdict: eligible'; and the claim's delivery text first sentence with the claim location. If the verdict changes, no flag.

RULE co_location: for each candidate item NOT listed in claim.reach_entity_ids, with world.area(item) not None and world.area(protagonist) not None and not world.together(protagonist, item) at baseline, and the claim eligible at baseline: Flag 'Claim <id> names <item> but is usable while the protagonist is away from it.' Evidence: claim location; 'protagonist in <area>; <item> in <area>'; the claim's reach_entity_ids (or 'none').

RULE no_strand: apply the custody hypothetical. For each (claim, item) the custody rule would flag: for each fact the claim establishes that the exit transition triggers on and that is NOT already true at baseline: list its other producers using the same producer discovery as situation_trace._producers (pacing events, other claims, deliveries/fallback handoffs). Flag when every producer is a claim that names that same item (so all become unusable if someone else holds the item) AND no pacing-event producer and no delivery producer exists AND no authored world effect (package.world.fact_effects, effects with move == item) moves the item to the protagonist. Summary: 'If <character> holds <item>, nothing else can set <fact>, so the exit <transition> can never open.' Evidence: each producer (with location), the fact the exit needs, the list of authored effects that move the item (or 'none'), and the caveat line 'Not stranded if <fact> is already true before the item is lost.'

SCRIPT {SCRIPT}: argparse: anchor, --root (default {ROOT}), --rule (repeatable). Prints render_flags output. Always exit 0 when it ran, even with flags (flags never block); exit 2 with the message on stderr for ValueError. Mirror {REPO}/scripts/situation_trace.py.

TESTS {TEST} (pytest, compact, helpers shared; copy the story to tmp_path with shutil.copytree and edit YAML with yaml.safe_load/safe_dump as {REPO}/tests/test_situation_trace.py does). Each rule gets one seeded-defect test that trips it and one clean-story test that does not. Real data first: run the script on anchor officer_presses_1a and read the output; the author's known case is that the claim k_sl_1a_b_r1 lets Kristin read the memory card while the officer holds it (custody), names kristin_laptop without a reach requirement while the laptop is in her truck (co_location, if the data shows it), and that surrender leaves no other producer of michelle_lead_actionable (no_strand). Assert the flags the real data gives for those (rule + claim id + item id), not exact wording. If a rule gives NO flag on the real data, do not fake it: report in your final message exactly which rule and why (print the baseline eligibility and holder), keep that rule's seeded-defect test using an edited copy where it does trip, and finish. Clean-story variants: custody clean = remove the item from the claim's entity_ids and relevance.entity_ids in the copy; co_location clean = add the item to reach_entity_ids; no_strand clean = give the needed fact a second producer that is not item-gated (the smallest valid edit that still loads, such as an extra effect on an existing pacing event, or a delivery cost) and assert the flag disappears. Also test: unknown anchor and unknown rule raise ValueError; output is deterministic across two calls; the package files are byte-identical before and after; the module source contains none of the story words listed in HARD RULE (read the file and assert); `python scripts/gap_rules.py` is exercised through its main(argv) and returns 0 with flags and 2 for an unknown anchor. The control anchor i_2a_real_leak must simply run without error (do not assert its flags).

HOW TO RUN (from {REPO}): `{ENV} && {PY} -m pytest {TEST} {REPO}/tests/test_situation_trace.py -q --no-cov -p no:cacheprovider 2>&1 | tail -30`; never --cov. Format and lint: `{PY} -m ruff format {MOD} {SCRIPT} {TEST} && {PY} -m ruff check {MOD} {SCRIPT} {TEST}`. Script run: `{ENV} && {PY} {SCRIPT} officer_presses_1a`."""

CHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {MOD} {SCRIPT} {TEST}
$PY -m ruff format --check {MOD} {SCRIPT} {TEST}
if grep -n -i -E 'memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity' {MOD} {SCRIPT}; then echo 'STORY NAMES FOUND in module or script'; exit 1; fi
$PY -m pytest {TEST} {REPO}/tests/test_situation_trace.py -q --no-cov -p no:cacheprovider 2>&1 | tail -25
$PY {SCRIPT} officer_presses_1a > /tmp/gap-rules-reyes.md
cat /tmp/gap-rules-reyes.md | head -60
grep -q '^### custody' /tmp/gap-rules-reyes.md || (echo 'no custody flag on the Reyes anchor'; exit 1)
$PY {SCRIPT} i_2a_real_leak > /dev/null
test "$($PY {SCRIPT} nope 2>/dev/null; echo $?)" = 2
# the three files only
git status --porcelain -- storygame scripts tests packages | grep -v -E 'gap_rules|test_gap_rules' | grep -v -E '^( M|\\?\\?) (tests/|scripts/ringer/)' || true
"""

VERIFIED = (
    "three gap rules (custody, co_location, no_strand) run through a registry with seeded-defect and clean-story "
    "tests, the Reyes anchor flags custody, the module carries no story names, and slice 1 tests still pass"
)

manifest = {
    "run_name": "story-data-gap-rules",
    "workdir": "/home/bcorfman/dev/ringer-work/story-data-gap-rules",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "gap-rules",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": [MOD, SCRIPT, TEST],
            "expect_files": [MOD, SCRIPT, TEST],
            "spec": SPEC,
            "check": CHECK,
            "verified": VERIFIED,
        }
    ],
}

out = Path(__file__).with_name("slice2-gap-rules-manifest.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
