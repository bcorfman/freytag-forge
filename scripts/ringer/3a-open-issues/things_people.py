# ruff: noqa: E501
"""Build the manifest for the corrected 3A presence projection (plan step 1, free)."""

from __future__ import annotations

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/3a-things-people"
REPO = "/home/bcorfman/dev/freytag-forge"

SPEC = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD behaviour this task deliberately changes; never weaken, skip or delete any other test.

ROLE: engine editor and test writer. You may edit ONLY: packages/worldkeeper/src/worldkeeper/model.py, a NEW test file packages/worldkeeper/tests/test_people_alongside.py, storygame/runtime/item_facts.py, tests/test_referred_reach.py, and any other test under tests/ that a failing test shows pins the OLD narration THINGS block or the old named-person Place wording (update only that pin and report it). NEVER edit: tests/fixtures/place_feed/baseline_prompts.json, tests/test_prompt_budget.py, tests/test_richer_1c.py, tests/test_kristin_bio.py, tests/fixtures/continuity_initiative_pre_3c_adoption/, or anything under data/, bench/, scripts/ or other packages. Do not change the story package. If tests/test_place_scoped_feed.py (the 1B opening golden) or tests/test_prompt_budget.py fail because of the new line, DO NOT touch them: report the exact failing assertion, the old and new prompt lines and the measured sizes; the orchestrator reviews and updates them separately.

BACKGROUND. The narrator prompt has a THINGS section built by `ItemFactsProvider._things_block(narration=True)` in storygame/runtime/item_facts.py. It lists things, groups, the protagonist (with \"With Kristin: <companions>.\"), and any person or place the player's command names (`_referred_lines_for_command`, stored in `self._referred_lines` by `prepare_turn`). A person merely standing with the protagonist is NOT listed, so the narrator is never told where she is. Two earlier attempts exist (scripts/ringer/3a-open-issues/present-people.patch, read it for the shape) but DO NOT apply it wholesale: it (a) gave every present person the command-scoped state instruction `If it changes, give \"state\": ...`, (b) rendered the placement as `world.name(parent)`, losing authored placement text, (c) deduplicated by rendered-line prefix matching, and (d) walked the world tree inside storygame. The corrected design below fixes those four. Tests build the REAL narrator prompt: see tests/test_referred_reach.py `_real_prompt`-style helpers if present in the patch, tests/test_place_scoped_feed.py `_opening_prompt`/`_state_at`, tests/test_richer_3a.py. DO NOT subclass a provider to force characters into THINGS.

THE CHANGE.
1. World (packages/worldkeeper, world-only logic; storygame only adapts): add `World.people_alongside(entity_id)` returning, as a sorted tuple, the IDs of characters that satisfy all of: `is_a(id, \"character\")`, not the given entity, `is_visible`, `alongside(entity_id, id)` (same spot; do NOT use `together`, which accepts nested areas), not in `companions(entity_id)`, and whose parent is not a group (a group's own line speaks for its members). Hidden, missing and shut-away people are excluded (is_visible). Docstring one line. Tests in packages/worldkeeper/tests/test_people_alongside.py (own tiny worlds; follow the style of the other tests in that directory): same-spot visible person included; person in a nested sub-area of the protagonist's area excluded; person in a different area excluded; hidden, shut-away (closed container) and status-missing excluded; companion excluded; group member excluded while a person directly in the same area as the group is included; the entity itself excluded; split companion (companion fact present but in another area) is NOT in the result either way (companions are excluded by the companion fact; document with a test what happens and keep the behaviour: excluded only when the companion is also alongside, i.e. a companion who has walked off and is not alongside is simply not alongside, so it is not returned; a companion who IS alongside is excluded because the protagonist's line already names it. Make sure the world method and `_things_block` agree: the protagonist line lists companions that are alongside; every other alongside person gets a line).
2. item_facts: in the narration THINGS block only, after the protagonist's line and before the command-referred lines, add one line per person from `world.people_alongside(protagonist_id)` that is also an NPC of the package (`self.state.package.world.npcs`), in the order the world gives. The non-narration `_things_block()` (used by the item-fact prompts and the matcher) stays exactly as it is: no person lines, no change to name-matching scope, no change to any tracked fact. The `THINGS:` header must also appear when only such lines exist.
   a. One shared helper builds a person line for BOTH the automatic lines and the existing command-named lines (replace the inline code in `_referred_lines_for_command`): `- <label>.` plus ` Place: <where>.` plus state text. <label> comes from `_referred_entity_label`. <where>: if `world.place_text(entity_id)` is not None, use it verbatim (authored placement text, valid until the person or an ancestor moves); else if the parent is a character use `self._entity_label(world, parent_id)` (never expose a hidden real name); else `world.place_label(entity_id)` which gives the parent's name; an unplaced person (no parent) has no Place part, as today. This also changes the existing command-named person line when the person has authored placement text; a person without text renders exactly as today.
   b. State text: a person who is only present (not named by the command) gets the ORDINARY state description `State: <current>. It can be: <other>.` (the `narration=False` form of `_state_text`), so the narrator knows she is, say, conscious without being told how to report a change. A person the command names keeps the existing `narration=True` form with `If it changes, give \"state\": \"<other>\".`. The helper takes a flag for this.
   c. Deduplicate by ENTITY identity, not rendered text. A person is skipped from the automatic lines if: the command names them (record the entity ids that `_referred_lines_for_command` renders, e.g. `self._referred_person_ids`, reset in `prepare_turn` and wherever `_referred_lines` is reset), or the entity is the one a THINGS name resolves to (`world.resolve(name)` for each listed name), or the entity is the one an observation line resolves to (`world.resolve(thing.name)` for each observation `visible_things`). Do not match on line text prefixes.
   d. Group behaviour is unchanged: group members are never promoted to a solo line merely by being members. A person who is directly named by the command still gets their own line.
   e. No scene, story or character name may appear in the code. No new prompt text other than these lines. Do not change CHARACTERS, SCENE or CONSTRAINTS.

TESTS (write first; real prompt path; put the story-package ones in tests/test_referred_reach.py unless a nearby file has the right helpers; use a small synthetic package for the placement-text cases):
 1. 3A, command \"Enter the medical level.\": exactly one Michelle line of the form `- Michelle. Place: detention level.` directly after \"- Kristin. Place: detention level. With Kristin: Brandon.\"; Brandon has no line of his own; the senior official (member of the captives group) has none.
 2. 3A opening prompt (as in tests/test_place_scoped_feed.py `_opening_prompt`) lists Michelle in THINGS.
 3. \"Ask Michelle about the lemon cake.\" yields her line exactly once, and it uses the command-scoped state form if she has any state axis (use the synthetic package to prove both state forms: a present person with an axis shows `It can be:` and not `If it changes`; the same person named by the command shows `If it changes`).
 4. Authored placement text (synthetic package using the story-package placement-text syntax, as tests/test_world_placements.py does): the person's line shows the text verbatim, both as a present person and when the command names them; after the person (or an ancestor) is moved the text stops applying and the parent's name is used; an unnamed character (npc with unnamed_label, not yet named) shows its unnamed label; a person whose parent is a character shows that character's safe label, never a hidden real name.
 5. Dedup by identity: a person already listed through a THINGS name or an observation line is not listed twice even if the label text differs from the line prefix; a person the command names is listed once.
 6. A person in another area, a hidden person, and a nested-area person get no line. The non-narration `_things_block()` never contains person lines.
 7. Companion alongside is not given its own line; a companion who is not alongside is not listed as a companion on the protagonist's line (existing behaviour) and, if visible and alongside, is not duplicated.
 8. Recovery/opening/normal-turn assembly use the same contract: find where the opening prompt and the recovery prompt are assembled (grep for `_things_block(` and `narration=True` in storygame/runtime/) and test that each carries the person lines the same way; report anything that builds THINGS without going through this code.
Then run: packages/worldkeeper/tests (whole directory), tests/test_referred_reach.py tests/test_opening_things_fact.py tests/test_fixed_thing_marker.py tests/test_scene_1b_grounding.py tests/test_runtime_capture.py tests/test_bench_item_facts.py tests/test_place_scoped_feed.py tests/test_richer_3a.py tests/test_speaker_lines.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_world_companions.py tests/test_world_placements.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_1a_kitchen_start.py, plus every test file that `grep -l \"THINGS:\"` matches under tests/.

INVENTORY ARTIFACT (free, outside the repo): write a small script at {WORK}/inventory.py (NOT in the repo) that, for each of the nine scenes of data/stories/continuity-initiative (1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B, 3C), builds the real narration prompt offline at the scene's opening (use the same helpers as tests/test_place_scoped_feed.py; no model call, stub urlopen like the tests do) and prints the THINGS block and the person lines the new rule adds, comparing against the same script run on the pre-change code (use `git stash` is forbidden; instead call the provider with the new code and compute the 'old' view by taking lines not from the new person lines). Run it and write {WORK}/inventory.txt with one section per scene: the person lines added at the opening, and the same for the scene's first scripted command if you can reach it with the existing helpers (else say 'opening only'). Also record 'user prompt characters' before/after for each opening if you can compute the before from the same run.

FINAL MESSAGE: the diff summary of model.py and item_facts.py, every test added or changed (one line each, and say why for any pre-existing test you changed), the exact THINGS block at the 3A opening and at 3A c4, anything surprising (especially any prompt-assembly path that does not use this code), the 1B opening difference in words, and the nine-scene table.
"""

CHECK = f"""set -o pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
mkdir -p {WORK}/cap
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{{print $2}}' | sort)
[ -n "$CH" ] || {{ echo "WHY: nothing changed"; exit 1; }}
for f in $CH; do case "$f" in tests/fixtures/place_feed/baseline_prompts.json|tests/fixtures/continuity_initiative_pre_3c_adoption/*|tests/test_prompt_budget.py|tests/test_richer_1c.py|tests/test_kristin_bio.py) echo "WHY: forbidden path: $f"; exit 1;; packages/worldkeeper/src/worldkeeper/model.py|packages/worldkeeper/tests/*|storygame/runtime/item_facts.py|tests/*) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
echo "$CH" | grep -qx storygame/runtime/item_facts.py || {{ echo "WHY: item_facts.py not changed"; exit 1; }}
echo "$CH" | grep -qx packages/worldkeeper/src/worldkeeper/model.py || {{ echo "WHY: model.py not changed"; exit 1; }}
echo "$CH" | grep -qx packages/worldkeeper/tests/test_people_alongside.py || {{ echo "WHY: worldkeeper test missing"; exit 1; }}
git diff -- storygame/runtime/item_facts.py packages/worldkeeper/src/worldkeeper/model.py | grep '^+' | grep -qi 'michelle\\|kristin\\|brandon\\|detention' && {{ echo "WHY: story or character name in engine code"; exit 1; }}
test -s {WORK}/inventory.txt || {{ echo "WHY: inventory.txt missing"; exit 1; }}
for s in 1A 1B 1C 2A 2B 2C 3A 3B 3C; do grep -q "$s" {WORK}/inventory.txt || {{ echo "WHY: inventory lacks scene $s"; exit 1; }}; done
git add -A -- storygame tests packages
$PY -m pytest -q -p no:cacheprovider packages/worldkeeper/tests > {WORK}/wk.out 2>&1 || {{ tail -30 {WORK}/wk.out; echo "WHY: worldkeeper suite failed"; exit 1; }}
tail -3 {WORK}/wk.out
$PY -m pytest -q -p no:cacheprovider tests/test_referred_reach.py tests/test_opening_things_fact.py tests/test_fixed_thing_marker.py tests/test_scene_1b_grounding.py tests/test_runtime_capture.py tests/test_bench_item_facts.py tests/test_place_scoped_feed.py tests/test_richer_3a.py tests/test_speaker_lines.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_world_companions.py tests/test_world_placements.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_1a_kitchen_start.py -rf > {WORK}/suite.out 2>&1; rc=$?
tail -25 {WORK}/suite.out
if [ $rc -ne 0 ]; then
  BAD=$(grep '^FAILED' {WORK}/suite.out | grep -v 'tests/test_place_scoped_feed.py' || true)
  [ -z "$BAD" ] || {{ echo "$BAD"; echo "WHY: failures outside the reviewable 1B golden"; exit 1; }}
  echo "INFO: only tests/test_place_scoped_feed.py failures remain (reviewable 1B golden)"
fi
echo "INFO (not a gate): prompt budget suite"; $PY -m pytest -q -p no:cacheprovider tests/test_prompt_budget.py 2>&1 | tail -15
cp {REPO}/bench/variations/richer-3a-people-candidate.json {WORK}/cap/var-candidate.json
$PY -m bench.frozen_prompts capture {WORK}/cap/var-candidate.json 4 5 --out {WORK}/cap/frozen-candidate.json > {WORK}/cap/candidate.log 2>&1 || {{ echo "WHY: offline capture failed"; tail -20 {WORK}/cap/candidate.log; exit 1; }}
for n in 4 5; do cp {REPO}/bench/results/richer-3a-probe/bio/frozen-candidate-c$n.json {WORK}/cap/frozen-control-c$n.json; done
test "$(sha256sum {WORK}/cap/frozen-control-c4.json | cut -c1-12)" = c3f98a8f9601 || {{ echo "WHY: control c4 payload changed"; exit 1; }}
test "$(sha256sum {WORK}/cap/frozen-control-c5.json | cut -c1-12)" = 8e8555fa004d || {{ echo "WHY: control c5 payload changed"; exit 1; }}
$PY - <<'E' || exit 1
import difflib, json, re
W='{WORK}/cap'
d=json.load(open(W+'/frozen-candidate.json'))
assert [e['n'] for e in d['endpoints']]==[4,5]
for b in d['endpoints']:
    n=b['n']; a=json.load(open(f'{{W}}/frozen-control-c{{n}}.json'))['endpoints'][0]
    assert a['command']==b['command'], 'same command'
    assert a['committed_after_prefix']==b['committed_after_prefix'], f'c{{n}}: committed facts differ'
    wa,wb=a['wire_payload'],b['wire_payload']
    assert wa['system']==wb['system'], f'c{{n}}: system prompt differs'
    assert wa['max_tokens']==wb['max_tokens'] and wa['response_format']==wb['response_format'], f'c{{n}}: request settings differ'
    lines=list(difflib.ndiff(wa['user'].splitlines(), wb['user'].splitlines()))
    minus=[l[2:] for l in lines if l.startswith('- ')]; plus=[l[2:] for l in lines if l.startswith('+ ')]
    print(f'c{{n}} minus:', minus); print(f'c{{n}} plus:', plus)
    assert not minus, f'c{{n}}: lines removed: {{minus}}'
    if n==5:
        assert not plus, f'c5 already names Michelle, so the diff must be empty, got {{plus}}'; print('c5: payload identical to control'); continue
    assert len(plus)==1 and re.fullmatch(r'- [^.\\n]*Michelle[^\\n]*\\. Place: detention level\\.', plus[0]), f'c{{n}}: expected exactly one Michelle THINGS line without a state instruction, got {{plus}}'
    assert 'If it changes' not in plus[0]
    things=wb['user'].split('THINGS:')[1].split('CONSTRAINTS:')[0]
    tl=things.strip().splitlines()
    assert tl.index(plus[0])==[i for i,x in enumerate(tl) if x.startswith('- Kristin')][0]+1, f'c{{n}}: not directly after the protagonist line'
    print(f'c{{n}}: payload diff ok; chars', len(wa['user']), '->', len(wb['user']))
E
PYF=$(echo "$CH" | grep '\\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || {{ echo "WHY: ruff check failed"; exit 1; }}
  $PY -m ruff format --check $PYF || {{ echo "WHY: ruff format failed"; exit 1; }}
fi
git diff --cached > {WORK}/things-people.patch && wc -l {WORK}/things-people.patch && git diff --cached --stat | tail -12
"""

manifest = {
    "run_name": "3a-things-people",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "things-people",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3600,
            "check_timeout_s": 900,
            "ownership": [
                "packages/worldkeeper/src/worldkeeper/model.py",
                "packages/worldkeeper/tests/test_people_alongside.py",
                "storygame/runtime/item_facts.py",
                "tests/test_referred_reach.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests first; World.people_alongside; THINGS gains one Michelle line at c4/c5 with ordinary state wording; dedup by identity; placement text lifecycle; suites and ruff pass; patch exported",
        }
    ],
}

Path(__file__).with_name("things-people-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
