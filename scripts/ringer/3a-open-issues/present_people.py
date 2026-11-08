# ruff: noqa: E501
"""Present-people manifest (Amendment 18, O1/O2): the narration THINGS block lists every person who is with the player
(visible, same spot, not a companion, not a group member, not already listed), so Michelle gets a placement line in
every 3A turn and the frame sentence "Michelle is beside the captives." can go. Engine change only; the story edit is
made by hand after the patch is applied. Zero narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-present-people"
CTL = f"{REPO}/bench/results/richer-3a-probe/bio"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD behaviour this task deliberately changes; never weaken, skip or delete any other test."""

SPEC = (
    COMMON
    + """

ROLE: engine editor and test writer. You may edit ONLY: storygame/runtime/item_facts.py, tests/test_referred_reach.py (add tests there; no new test file), and any other test under tests/ (including a JSON fixture under tests/fixtures/ that a failing test names, but NEVER tests/fixtures/continuity_initiative_pre_3c_adoption/, tests/test_prompt_budget.py, tests/test_richer_1c.py or tests/test_kristin_bio.py) that a failing test shows pins the OLD narration THINGS block; update only that pin and report it. Do not touch anything under data/, packages/, bench/ or scripts/, and do not change the story package.

BACKGROUND. The narrator prompt has a THINGS section built by `ItemFactsProvider._things_block(narration=True)` in storygame/runtime/item_facts.py. It lists things, groups and places that matter, the protagonist (with "With Kristin: <companions>."), and any person or place the player's command names (`_referred_lines_for_command`, stored in `self._referred_lines` by `prepare_turn`). A person who is merely standing with the protagonist is NOT listed, so the narrator is never told where she is (the world model knows: michelle's parent is the detention level, the same spot as Kristin). Example today at 3A, command "Enter the medical level.": THINGS holds only "- Kristin. Place: detention level. With Kristin: Brandon." and "- medical level. This is a place.". People reach the narrator only through CHARACTERS (bios) and SCENE. Tests such as tests/test_referred_reach.py and tests/test_place_scoped_feed.py build the REAL narrator prompt: use that shipped path and DO NOT subclass a provider to force characters into THINGS (an earlier attempt passed its tests only that way).

THE CHANGE. In the narration THINGS block (narration=True only; the non-narration block used by the item-fact prompts and every tracked fact stay exactly as they are), after the protagonist's line and before the command-referred lines, add one line for each character that satisfies ALL of: it is an NPC of the package (iterate `self.state.package.world.npcs` as `_referred_lines_for_command` does), it is not the protagonist, it is visible (`world.is_visible`), it is with the protagonist (`world.alongside(protagonist_id, entity_id)`: same spot), it is not one of the protagonist's companions (`world.companions(protagonist_id)`; they are already on the protagonist's line), it is not a member of a group (its parent is not a group: the group's own line speaks for its members), and its label is not already listed (neither a THINGS name nor already in the command-referred lines: a person the command names keeps exactly the line it has today, once). The line has exactly the form the command-named person line already has: `- <label>. Place: <parent name>.` followed by the person's state text, built with the same helpers (`_referred_entity_label`, `_state_text(world, entity_id, narration=True)`); put the shared code in one small helper used by both so the two forms cannot drift. The "THINGS:" header must also appear when only such lines exist. Order the new lines by entity order as the world gives it (deterministic). No scene, story or character name may appear in the code. Do not add any new text to the prompt other than these lines, and do not change CHARACTERS, SCENE or CONSTRAINTS.

TESTS (write first, in tests/test_referred_reach.py unless a nearby file already has the right helpers; real prompt path):
1. 3A, command "Enter the medical level." (reach it through the real engine, e.g. the helpers in tests/test_richer_3a.py or tests/test_prompt_budget.py `_prompts`): the narration THINGS block contains exactly one Michelle line of the form `- <her label>. Place: detention level.`, directly after the line "- Kristin. Place: detention level. With Kristin: Brandon." (companion Brandon is NOT given a line of his own), and the senior official (member of the captives group) has no line of his own.
2. The 3A opening prompt as the scene is entered (the real opening path, see `_opening_prompt` in tests/test_place_scoped_feed.py) lists Michelle in THINGS.
3. A command that names her ("Ask Michelle about the lemon cake.") yields her line exactly once.
4. A story state where an NPC stands in a different area from the protagonist gets no line (use any package scene where that holds, e.g. Michelle in an earlier scene or a built state), and the non-narration `_things_block()` never contains person lines.
5. A one-line test that the shared helper produces the same text for a command-named person and a present person.
Then run: tests/test_referred_reach.py tests/test_opening_things_fact.py tests/test_fixed_thing_marker.py tests/test_scene_1b_grounding.py tests/test_runtime_capture.py tests/test_bench_item_facts.py tests/test_place_scoped_feed.py tests/test_richer_3a.py tests/test_speaker_lines.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_world_companions.py tests/test_world_placements.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_1a_kitchen_start.py plus every test file that `grep -l "THINGS:"` matches under tests/. A test that fails because it pins the old THINGS block of a scene where a person now appears is the one kind you may update (change only that pin, and report it); anything else that fails is a finding to report, not to fix by editing the test. Do NOT raise any prompt-size ceiling or deep-turn budget fixture: tests/test_prompt_budget.py may now fail; report the measured numbers instead of touching it.

FINAL MESSAGE: the diff of storygame/runtime/item_facts.py, every test changed or added (one line each), anything surprising, the exact THINGS block at 3A c4 and at the 3A opening, and for EACH of the nine scenes of data/stories/continuity-initiative (1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B, 3C) the person lines the new rule adds at the scene's opening and at its first scripted command (or say none).
"""
)

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in tests/fixtures/continuity_initiative_pre_3c_adoption/*|tests/test_prompt_budget.py|tests/test_richer_1c.py|tests/test_kristin_bio.py) echo "WHY: forbidden path: $f"; exit 1;; storygame/runtime/item_facts.py|tests/*) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
echo "$CH" | grep -qx storygame/runtime/item_facts.py || { echo "WHY: item_facts.py not changed"; exit 1; }
git add -A -- storygame tests
mkdir -p OUTDIR/cap
$PY - <<'E' || exit 1
import json
a=json.load(open('bench/variations/richer-3a-bio-candidate.json'))
a['name']='richer-3a-people-candidate'; a['story_package']='data/stories/continuity-initiative'
json.dump(a, open('OUTDIR/cap/var-candidate.json','w'), indent=2)
E
$PY -m bench.frozen_prompts capture OUTDIR/cap/var-candidate.json 4 5 --out OUTDIR/cap/frozen-candidate.json > OUTDIR/cap/candidate.log 2>&1 || { echo "WHY: offline capture failed"; tail -20 OUTDIR/cap/candidate.log; exit 1; }
for n in 4 5; do cp CTL/frozen-candidate-c$n.json OUTDIR/cap/frozen-control-c$n.json; done
test "$(sha256sum OUTDIR/cap/frozen-control-c4.json | cut -c1-12)" = c3f98a8f9601 || { echo "WHY: control c4 payload changed"; exit 1; }
test "$(sha256sum OUTDIR/cap/frozen-control-c5.json | cut -c1-12)" = 8e8555fa004d || { echo "WHY: control c5 payload changed"; exit 1; }
$PY - <<'E' || exit 1
import difflib, json, re
d=json.load(open('OUTDIR/cap/frozen-candidate.json'))
assert [e['n'] for e in d['endpoints']]==[4,5]
for b in d['endpoints']:
    n=b['n']; a=json.load(open(f'OUTDIR/cap/frozen-control-c{n}.json'))['endpoints'][0]
    assert a['command']==b['command'], 'same command'
    assert a['committed_after_prefix']==b['committed_after_prefix'], f'c{n}: committed facts differ'
    wa,wb=a['wire_payload'],b['wire_payload']
    assert wa['system']==wb['system'], f'c{n}: system prompt differs'
    assert wa['max_tokens']==wb['max_tokens'] and wa['response_format']==wb['response_format'], f'c{n}: request settings differ'
    lines=list(difflib.ndiff(wa['user'].splitlines(), wb['user'].splitlines()))
    minus=[l[2:] for l in lines if l.startswith('- ')]; plus=[l[2:] for l in lines if l.startswith('+ ')]
    print(f'c{n} minus:', minus); print(f'c{n} plus:', plus)
    assert not minus, f'c{n}: lines removed from the prompt: {minus}'
    assert len(plus)==1 and re.fullmatch(r'- [^.\n]*Michelle[^\n]*\. Place: detention level\.', plus[0]), f'c{n}: expected exactly one Michelle THINGS line, got {plus}'
    things=wb['user'].split('THINGS:')[1].split('CONSTRAINTS:')[0]
    assert plus[0] in things, f'c{n}: the new line is not inside THINGS'
    tl=things.strip().splitlines()
    assert tl.index(plus[0])==[i for i,x in enumerate(tl) if x.startswith('- Kristin')][0]+1, f'c{n}: Michelle line is not directly after the protagonist line'
    assert 'Brandon.' in [x for x in tl if x.startswith('- Kristin')][0], f'c{n}: companion text lost'
    print(f'c{n}: payload diff ok; chars', len(wa['user']), '->', len(wb['user']))
E
$PY -m pytest -q -p no:cacheprovider tests/test_referred_reach.py tests/test_opening_things_fact.py tests/test_fixed_thing_marker.py tests/test_scene_1b_grounding.py tests/test_runtime_capture.py tests/test_bench_item_facts.py tests/test_place_scoped_feed.py tests/test_richer_3a.py tests/test_speaker_lines.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_world_companions.py tests/test_world_placements.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_1a_kitchen_start.py > /tmp/tpp.out 2>&1; rc=$?; tail -25 /tmp/tpp.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
echo "INFO (not a gate): prompt budget suite"; $PY -m pytest -q -p no:cacheprovider tests/test_prompt_budget.py 2>&1 | tail -15
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
git diff --cached > OUTDIR/present-people.patch && wc -l OUTDIR/present-people.patch && git diff --cached --stat | tail -12
""".replace("OUTDIR", OUT).replace("CTL", CTL)

manifest = {
    "run_name": "3a-present-people",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "present-people",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": ["storygame/runtime/item_facts.py", "tests/test_referred_reach.py"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests first, THINGS gains exactly one Michelle line at c4 and c5 and nothing else, suites and ruff pass, patch exported",
        }
    ],
}
Path(__file__).with_name("present-people-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
