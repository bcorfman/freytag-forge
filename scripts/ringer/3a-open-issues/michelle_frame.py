# ruff: noqa: E501
"""Michelle frame manifest (O2): the 3A frame sentence "Michelle is beside the captives." leaves the always-on SCENE frame and
becomes an opening-only sentence in the 3A entry_text, so the opening still names Michelle and later turns stop re-staging
her. No world effect and no placement text (people only reach THINGS when the command names them). Zero narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-michelle-frame"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD behaviour this task deliberately changes; never weaken, skip or delete any other test."""

SPEC = (
    COMMON
    + """

ROLE: story-package editor and test writer. You may edit ONLY: data/stories/continuity-initiative/knowledge.yaml (exactly one line), data/stories/continuity-initiative/plot.md (exactly one line), tests/test_richer_3a.py (add tests; update the pin named below), and any other test under tests/ (including a JSON fixture under tests/fixtures/ that a failing test names, but NEVER tests/fixtures/continuity_initiative_pre_3c_adoption/, tests/test_prompt_budget.py, tests/test_richer_1c.py, or tests/test_kristin_bio.py) that a failing test shows pins the OLD 3A frame sentence or the OLD 3A entry text; update only that pin and report it. Do not touch world.yaml, handoffs.yaml, the opening cue, any delivery, statement, fact, prerequisite or speaker line, anything under storygame/ or packages/, and do not add a new test file.

BACKGROUND (so you understand the change; do not act on it beyond the spec). In scene 3A the narrator's SCENE section always shows the scene frame `situation` (knowledge.yaml `scene_frames`, scene_id 3A). It ends with the sentence "Michelle is beside the captives.". That sentence is the ONLY line of the 3A opening prompt that says Michelle is there (people appear in THINGS only when the player's command refers to them, so a placement `text` cannot carry it; do not try that). The sentence stays in SCENE for every later turn, where the narrator reads it as the scene's opening picture and re-stages it ("sees Michelle standing beside the captives"). The scene's `entry_text` (plot.md, scene 3A front matter) is shown to the narrator only at the opening (check this in the prompts: it is in the opening SCENE and NOT in the SCENE of a later turn) and is also the first paragraph the player reads. This task MOVES the information to the opening only: the sentence leaves the frame, and a short sentence naming Michelle is added at the end of the entry text. No world effect, no companion change, no change to any reunion statement (both reunion statements and all six per-speaker lines must be exactly as today).

THE STORY CHANGES (wording supplied; do not invent replacements):
1. knowledge.yaml, the 3A `scene_frames` entry: replace its `situation` value `"The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels. Michelle is beside the captives."` by the same string without the final sentence: `"The detention sector: rows of holding blocks, scattered stolen radios, and captives who are alert rather than passive. Security is tightening around the lower levels."` (one line changed; `pressure` untouched).
2. plot.md, scene 3A front matter, the `entry_text:` line: insert the sentence ` Michelle was among them.` (a leading space, no other change) immediately after `before rescue arrived.` and before the two escaped newlines `\n\n` that end the string, so it ends `... someone inside had been organizing this long before rescue arrived. Michelle was among them.\n\n"`. The `entry_variants` text and the prose line "Michelle is beside the captives." in Scene 3A.1 stay unchanged. Nothing else in plot.md changes.

TESTS (write first; look at tests/test_richer_3a.py helpers `_engine`, `_handoff`, `_authored_provider`, `_turn_text`, and tests/test_prompt_budget.py `_prompts` / tests/test_speaker_lines.py for building the real narrator prompt exactly as it ships: DO NOT subclass a provider to force characters into THINGS, use the shipped prompt path, and note that Michelle does not appear in THINGS). The control package for comparisons is the package at HEAD: build it in a temporary directory with `git show HEAD:<path>` for the nine files of data/stories/continuity-initiative/ (see bench/frozen/continuity-pre-3a-radio for the file list).
1. The 3A frame `situation` no longer mentions Michelle and ends with "Security is tightening around the lower levels."; update the existing pin in tests/test_richer_3a.py (it asserts the old ending) to the new ending, nothing else there.
2. The 3A entry text equals the old entry text plus ` Michelle was among them.` before its final blank line; the entry variants are unchanged.
3. Opening prompt (as the scene is entered; see `python -m bench prompt --help`, it contacts no model, or the test helpers): relative to the control the ONLY differences are the SCENE frame line (sentence gone) and the entry text line (sentence added); the system prompt is byte identical. In the opening SCENE the words "Michelle was among them." are present once and "Michelle is beside the captives." is absent.
4. A later turn BEFORE the reunion (command `Look at the captives.`) and the turn after the A-r1 path (`Free the captives.`) AND after the A-r2 path (the existing A-r2 command in the file, e.g. `Ask Michelle about other sites.`), each reached through the real engine: relative to the control the ONLY difference is the SCENE frame line (sentence gone); "Michelle was among them." does NOT appear anywhere in the prompt; both reunion statements are still in SCENE after the reunion; the six 'may say this aloud' lines for them are unchanged.
5. The existing deliveries, facts and reveals tests pass UNCHANGED.
Then run: tests/test_richer_3a.py tests/test_world_model.py tests/test_world_companions.py tests/test_world_placements.py tests/test_knowledge_projection.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_unbound_item.py tests/test_audit_budget.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_1a_kitchen_start.py, plus every test file whose grep for `Michelle is beside` or `rescue arrived` matched. Do NOT raise any prompt-size ceiling or deep-turn budget fixture to make a test pass: if a ceiling fixture or budget test fails, report it in the final message (with the measured numbers) instead.

FINAL MESSAGE: the two story diffs, every test changed or added (one line each), anything surprising (for example any test that failed first and why), and the measured prompt difference (characters) at the 3A opening, at the pre-reunion state and at the reunion state.
"""
)

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in tests/fixtures/continuity_initiative_pre_3c_adoption/*|tests/test_prompt_budget.py|tests/test_richer_1c.py|tests/test_kristin_bio.py) echo "WHY: forbidden path: $f"; exit 1;; $D/knowledge.yaml|$D/plot.md|tests/*) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
git add -A -- $D tests
for f in knowledge.yaml plot.md; do test "$(git diff --cached --numstat -- $D/$f | awk '{print $1" "$2}')" = "1 1" || { echo "WHY: $f must change exactly one line"; git diff --cached -- $D/$f | head -30; exit 1; }; done
git diff --cached --numstat -- $D | awk '{print $3}' | sort | tr '\n' ' ' | grep -qx "$D/knowledge.yaml $D/plot.md " || { echo "WHY: only knowledge.yaml and plot.md may change under $D"; exit 1; }
git diff --cached -U0 -- $D/knowledge.yaml | grep -E '^[-+]' | grep -vE '^(---|\+\+\+) ' > /tmp/mf-k.txt
$PY - <<'E' || exit 1
l=open('/tmp/mf-k.txt').read().splitlines()
assert len(l)==2 and l[0].startswith('-') and l[1].startswith('+'), l
o,n=l[0][1:],l[1][1:]
assert o.endswith(' Michelle is beside the captives."'), 'old line not the 3A situation: '+o
assert n==o.replace(' Michelle is beside the captives."','"'), 'knowledge.yaml change is not exactly the removal of the last sentence: '+n
print('knowledge.yaml diff exact')
E
git diff --cached -U0 -- $D/plot.md | grep -E '^[-+]' | grep -vE '^(---|\+\+\+) ' > /tmp/mf-p.txt
$PY - <<'E' || exit 1
l=open('/tmp/mf-p.txt').read().splitlines()
assert len(l)==2 and l[0].startswith('-') and l[1].startswith('+'), l
o,n=l[0][1:],l[1][1:]
assert o.startswith('entry_text: "A partly unsecured detention sector'), 'old line is not the 3A entry_text: '+o[:80]
end='rescue arrived.\\n\\n"'
assert o.endswith(end), 'old entry_text ending unexpected'
assert n==o[:-len(end)]+'rescue arrived. Michelle was among them.\\n\\n"', 'plot.md change is not exactly the supplied sentence: '+n[-120:]
print('plot.md diff exact')
E
mkdir -p OUTDIR/ctl OUTDIR/cap
for f in connections.yaml handoffs.yaml incidents.yaml knowledge.yaml pacing.yaml plot.md storylet-routes.yaml storylets.md world.yaml; do git show HEAD:$D/$f > OUTDIR/ctl/$f; done
$PY - <<'E' || exit 1
import json
a=json.load(open('bench/variations/richer-3a-radio-candidate.json'))
for n,p in (('control','OUTDIR/ctl'),('candidate','data/stories/continuity-initiative')):
    x=dict(a); x['name']='richer-3a-frame-'+n; x['story_package']=p
    json.dump(x, open(f'OUTDIR/cap/var-{n}.json','w'), indent=2)
E
for arm in control candidate; do $PY -m bench.frozen_prompts capture OUTDIR/cap/var-$arm.json 1 4 --out OUTDIR/cap/frozen-$arm.json > OUTDIR/cap/$arm.log 2>&1 || { echo "WHY: offline capture failed for $arm"; tail -20 OUTDIR/cap/$arm.log; exit 1; }; done
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
    print(f'c{n} minus:', minus); print(f'c{n} plus:', plus)
    frame_old=[m for m in minus if 'Michelle is beside the captives.' in m]
    assert len(frame_old)==1 and frame_old[0].endswith('lower levels. Michelle is beside the captives.'), f'c{n}: old frame line not removed exactly once: {minus}'
    assert plus==[frame_old[0].replace(' Michelle is beside the captives.','')] and len(minus)==1, f'c{n}: expected only the frame line to change: minus={minus} plus={plus}'
    assert 'Michelle was among them.' not in wb['user'], f'c{n}: opening-only sentence leaked into a later turn'
    assert wb['user'].count('may say this aloud:')==wa['user'].count('may say this aloud:'), f'c{n}: speaker lines changed'
    if n==4:
        for st in ('Kristin and Michelle have reunited.','Michelle has explained that freeing this block means little'):
            assert st in wb['user'].split('SCENE:')[1].split('THINGS:')[0], 'c4: reunion statement left SCENE'
    print(f'c{n}: payload diff ok; chars', len(wa['user'])+len(wa['system']), '->', len(wb['user'])+len(wb['system']))
E
for arm in control candidate; do if [ $arm = control ]; then PK="--package OUTDIR/ctl"; else PK=""; fi; $PY -m bench prompt --scene 3A $PK > OUTDIR/cap/open-$arm.json 2> OUTDIR/cap/open-$arm.log || { echo "WHY: bench prompt failed for $arm"; tail -10 OUTDIR/cap/open-$arm.log; exit 1; }; done
$PY - <<'E' || exit 1
import difflib, json
c=json.load(open('OUTDIR/cap/open-control.json')); d=json.load(open('OUTDIR/cap/open-candidate.json'))
assert c['system']==d['system'], 'opening: system prompt differs'
lines=list(difflib.ndiff(c['user'].splitlines(), d['user'].splitlines()))
minus=[l[2:] for l in lines if l.startswith('- ')]; plus=[l[2:] for l in lines if l.startswith('+ ')]
print('opening minus:', minus); print('opening plus:', plus)
assert len(minus)==2 and len(plus)==2, 'opening: expected exactly the frame line and the entry text line to change'
assert any('Michelle is beside the captives.' in m for m in minus), 'opening: old frame line not changed'
assert d['user'].count('Michelle was among them.')==1, 'opening: sentence not present exactly once'
assert 'Michelle is beside the captives.' not in d['user'], 'opening: old sentence still present'
print('opening prompt diff ok; chars', len(c['user']), '->', len(d['user']))
E
$PY -m pytest -q -p no:cacheprovider tests/test_richer_3a.py tests/test_world_model.py tests/test_world_companions.py tests/test_world_placements.py tests/test_knowledge_projection.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_unbound_item.py tests/test_audit_budget.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_1a_kitchen_start.py > /tmp/tmf.out 2>&1; rc=$?; tail -25 /tmp/tmf.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
mkdir -p OUTDIR && git diff --cached > OUTDIR/michelle-frame.patch && wc -l OUTDIR/michelle-frame.patch && git diff --cached --stat | tail -12
""".replace("OUTDIR", OUT)

manifest = {
    "run_name": "3a-michelle-frame",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "michelle-frame",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "data/stories/continuity-initiative/knowledge.yaml",
                "data/stories/continuity-initiative/plot.md",
                "tests/test_richer_3a.py",
                "tests/test_world_placements.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests added first, two exact story diffs, payload diff exact at c1 and c4, suites and ruff pass, patch exported",
        }
    ],
}
Path(__file__).with_name("michelle-frame-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
