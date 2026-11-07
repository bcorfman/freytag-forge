# ruff: noqa: E501
"""Reunion world-effect manifest (O2): michelle_reached gets an `accompany` world effect, with a frozen control package and two variations. Zero narrator neurons (the check's capture uses the canned reply)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-reunion-effect"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD behaviour this task deliberately changes; never weaken, skip or delete any other test."""

SPEC = (
    COMMON
    + """

ROLE: story-package editor, bench-variation author and test writer. You may edit/create ONLY: data/stories/continuity-initiative/world.yaml (exactly the change below), bench/frozen/continuity-pre-3a-reunion/ (new), bench/variations/richer-3a-reunion-control.json and bench/variations/richer-3a-reunion-candidate.json (new), tests/test_richer_3a.py, tests/test_world_model.py, tests/test_world_companions.py (add tests only), and any other test under tests/ that a failing test shows pins the OLD behaviour (the set of facts that carry world effects, or Michelle not being Kristin's companion after the reunion); update only that pin.

BACKGROUND (so you understand the change; do not act on it beyond the spec): when a knowledge entry establishes a fact that has a world effect (`on_assert` in world.yaml), the engine leaves that entry out of the SCENE section of the narrator prompt, because the world state now records it (storygame/runtime/knowledge.py `_effect_item_ids`; precedent: facts `relay_open`, `memory_card_recovered`, and, from commit 38d5ae8c, `detention_uprising_started`). The two 3A reunion entries `k_sl_3a_a_r1` and `k_sl_3a_a_r2` (knowledge.yaml) both establish `michelle_reached` and `uprising_prepared`. No other entry establishes `michelle_reached`. The effect below is true to the plot: after the reunion Michelle goes with Kristin through the block (plot.md Scene 3A: she leads Kristin through the medical level, then Kristin, Michelle and Brandon fight upward; scene 3B declares companions [brandon, michelle]). Do NOT add a fake effect, do not edit knowledge.yaml, plot.md or any other story file.

THE CHANGE (wording supplied; do not invent replacements): in data/stories/continuity-initiative/world.yaml, in the `facts:` list, replace the single line `- michelle_reached` by exactly these three lines (same style as `detention_uprising_started` and `facts: brandon_identified`):
- id: michelle_reached
  on_assert:
  - {accompany: michelle, with: kristin}
Change nothing else in world.yaml.

FROZEN CONTROL: BEFORE you edit world.yaml, copy byte for byte the nine package files of data/stories/continuity-initiative/ AS THEY ARE AT HEAD into bench/frozen/continuity-pre-3a-reunion/ (exactly the same file set that bench/frozen/continuity-pre-3a-radio/ holds). This frozen copy is the control arm.
VARIATIONS: copy bench/variations/richer-3a-radio-candidate.json twice. `richer-3a-reunion-control.json`: name `richer-3a-reunion-control`, story_package `bench/frozen/continuity-pre-3a-reunion`. `richer-3a-reunion-candidate.json`: name `richer-3a-reunion-candidate`, story_package `data/stories/continuity-initiative`. Everything else (nine commands, thorough entry state, entry_facts, item_facts, judges off) identical to richer-3a-radio-candidate.json.

TESTS (first; look at tests/test_richer_3a.py helpers `_engine`, `_handoff`, `_authored_provider`, `_turn_text`, and tests/test_prompt_budget.py `_prompts` / tests/test_speaker_lines.py for building prompts for two packages; tests/test_world_companions.py for companion assertions):
1. world.fact_effects['michelle_reached'] is exactly one effect, accompany michelle with kristin; and tests/test_world_model.py's pin of the set of facts that carry world effects gains `michelle_reached` (that is the only change to that test).
2. Behaviour in the real engine: before the reunion (no facts) Michelle is not Kristin's companion; after the A-r1 path (`Free the captives.`) AND after the A-r2 path (the existing A-r2 command in the file, e.g. `Ask Michelle about other sites.`) `world.companions('kristin')` contains both brandon and michelle, and the facts michelle_reached and uprising_prepared are true; deliveries, facts and reveals are exactly as before (the existing tests for these must still pass UNCHANGED).
3. Prompt diff against the frozen control, at the state with michelle_reached and uprising_prepared true in 3A reached through the real engine (not by asserting facts directly, since direct assertion does not run the effect): the SCENE section of the projected narration prompt no longer contains either short statement (`Kristin and Michelle have reunited.` / `Michelle has explained that freeing this block means little without exposing the other sites.`); every per-speaker 'may say this aloud' line is UNCHANGED (still six lines for those two statements: Michelle, Brandon, the senior official); the system prompt is byte identical; the only other change is the line for Kristin, which gains Michelle: `With Kristin: Brandon, Michelle.` instead of `With Kristin: Brandon.`. State the whole expected diff as one exact assertion (the removed lines and the changed line), so any other change fails.
4. Before the reunion (state with no 3A facts, and at the 3A entry): the prompt built from the live package is BYTE IDENTICAL to the one from the frozen control (the effect cannot leak early).
5. The effect does not survive the scene change wrongly: after the 3A to 3B transition the companions are exactly what 3B declares (brandon, michelle) with no duplication, and a revisit does not accumulate stale companions (look at storygame/runtime/world_model.py around the scene-entry companion reset).
6. The frozen control equals HEAD's package files byte for byte (compare with `git show HEAD:<path>` is not possible inside a test; instead assert the frozen world.yaml equals the live world.yaml with the three new lines replaced by `- michelle_reached`, and the other eight files are byte equal to the live ones).
Then run: tests/test_richer_3a.py tests/test_world_model.py tests/test_world_companions.py tests/test_world_placements.py tests/test_knowledge_projection.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_unbound_item.py tests/test_audit_budget.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py, plus every test file whose grep for `michelle_reached` or `fact_effects` matched. If a regenerated expectation file exists (scripts/generate_spine_expected_reveals.py), regenerate only if a test fails because of this change and report the diff. Do NOT raise any prompt-size ceiling to make a test pass: if a ceiling fixture or budget test fails, report it in the final message instead.

FINAL MESSAGE: the world.yaml diff, every test changed or added (with one line each), the frozen directory file list, anything surprising (for example any test that failed first and why), and the measured prompt difference at the reunion state (characters removed from SCENE, characters added to the Kristin line).
"""
)

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
F=bench/frozen/continuity-pre-3a-reunion
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in $D/world.yaml|tests/*|$F/|$F/*|bench/variations/richer-3a-reunion-control.json|bench/variations/richer-3a-reunion-candidate.json) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
git add -A -- $D bench tests
test "$(git diff --cached --numstat -- $D | awk '{a+=$1; d+=$2} END {print a" "d}')" = "3 1" || { echo "WHY: story package must change exactly 3 added and 1 removed lines (world.yaml only)"; git diff --cached --stat -- $D; git diff --cached -- $D | head -40; exit 1; }
git diff --cached --numstat -- $D | awk '{print $3}' | grep -qx "$D/world.yaml" || { echo "WHY: only world.yaml may change under $D"; exit 1; }
git diff --cached -U0 -- $D/world.yaml | grep -E '^[-+]' | grep -vE '^(---|\+\+\+) ' > /tmp/rue-diff.txt
printf -- '-- michelle_reached\n+- id: michelle_reached\n+  on_assert:\n+  - {accompany: michelle, with: kristin}\n' | diff - /tmp/rue-diff.txt || { echo "WHY: world.yaml diff is not the supplied three lines replacing '- michelle_reached'"; exit 1; }
for f in connections.yaml handoffs.yaml incidents.yaml knowledge.yaml pacing.yaml plot.md storylet-routes.yaml storylets.md; do cmp $D/$f $F/$f || { echo "WHY: frozen copy of $f differs from HEAD"; exit 1; }; done
git show HEAD:$D/world.yaml | cmp - $F/world.yaml || { echo "WHY: frozen world.yaml is not HEAD's"; exit 1; }
[ "$(ls bench/frozen/continuity-pre-3a-radio)" = "$(ls $F)" ] || { echo "WHY: frozen file set differs from continuity-pre-3a-radio"; exit 1; }
$PY - <<'E' || exit 1
import json
a=json.load(open('bench/variations/richer-3a-radio-candidate.json')); c=json.load(open('bench/variations/richer-3a-reunion-control.json')); v=json.load(open('bench/variations/richer-3a-reunion-candidate.json'))
for x,n,p in ((c,'richer-3a-reunion-control','bench/frozen/continuity-pre-3a-reunion'),(v,'richer-3a-reunion-candidate','data/stories/continuity-initiative')):
    assert x['name']==n and x['story_package']==p, (n, x['name'], x['story_package'])
    y=dict(x); y['name']=a['name']; y['story_package']=a['story_package']
    assert y==a, f'{n} differs from richer-3a-radio-candidate beyond name/package'
print('variations ok')
E
mkdir -p OUTDIR/cap
for arm in control candidate; do $PY -m bench.frozen_prompts capture bench/variations/richer-3a-reunion-$arm.json 4 5 --out OUTDIR/cap/frozen-$arm.json > OUTDIR/cap/$arm.log 2>&1 || { echo "WHY: offline capture failed for $arm"; tail -20 OUTDIR/cap/$arm.log; exit 1; }; done
$PY - <<'E' || exit 1
import difflib, json
c=json.load(open('OUTDIR/cap/frozen-control.json')); d=json.load(open('OUTDIR/cap/frozen-candidate.json'))
assert len(c['endpoints'])==len(d['endpoints'])==2
for a,b in zip(c['endpoints'],d['endpoints']):
    n=a['n']; assert n==b['n']
    assert a['command']==b['command'], 'same command'
    assert a['committed_after_prefix']==b['committed_after_prefix'], f'c{n}: committed facts differ'
    wa,wb=a['wire_payload'],b['wire_payload']
    assert wa['system']==wb['system'], f'c{n}: system prompt differs'
    assert wa['max_tokens']==wb['max_tokens'] and wa['response_format']==wb['response_format'], f'c{n}: request settings differ'
    lines=list(difflib.ndiff(wa['user'].splitlines(), wb['user'].splitlines()))
    minus=[l[2:] for l in lines if l.startswith('- ')]; plus=[l[2:] for l in lines if l.startswith('+ ')]
    assert len(minus)==3 and len(plus)==1, f'c{n}: expected 3 removed and 1 added line, got {len(minus)} and {len(plus)}: {minus} {plus}'
    assert any(m.startswith('- Kristin and Michelle have reunited.') for m in minus), f'c{n}: reunion line not removed from SCENE'
    assert any(m.startswith('- Michelle has explained that freeing this block') for m in minus), f'c{n}: other-sites line not removed from SCENE'
    kr=[m for m in minus if m.startswith('- Kristin. Place:')]
    assert kr and kr[0].endswith('With Kristin: Brandon.'), f'c{n}: control Kristin line unexpected: {minus}'
    assert plus[0]==kr[0][:-len('Brandon.')]+'Brandon, Michelle.', f'c{n}: candidate Kristin line unexpected: {plus}'
    print(f'c{n}: payload diff ok; chars', len(wa['user'])+len(wa['system']), '->', len(wb['user'])+len(wb['system']))
E
$PY -m pytest -q -p no:cacheprovider tests/test_richer_3a.py tests/test_world_model.py tests/test_world_companions.py tests/test_world_placements.py tests/test_knowledge_projection.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_unbound_item.py tests/test_audit_budget.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py > /tmp/treu.out 2>&1; rc=$?; tail -25 /tmp/treu.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
mkdir -p OUTDIR && git diff --cached > OUTDIR/reunion-effect.patch && wc -l OUTDIR/reunion-effect.patch && git diff --cached --stat | tail -12
""".replace("OUTDIR", OUT)

manifest = {
    "run_name": "3a-reunion-effect",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "reunion-effect",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "data/stories/continuity-initiative/world.yaml",
                "bench/frozen/continuity-pre-3a-reunion/",
                "bench/variations/richer-3a-reunion-control.json",
                "bench/variations/richer-3a-reunion-candidate.json",
                "tests/test_richer_3a.py",
                "tests/test_world_model.py",
                "tests/test_world_companions.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests added first, effect in place, prompt diff exact, suites and ruff pass, patch exported",
        }
    ],
}
Path(__file__).with_name("reunion-effect-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
