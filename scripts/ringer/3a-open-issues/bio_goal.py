# ruff: noqa: E501
"""Kristin bio manifest: the narrator bio drops its goal sentence (a goal changes by scene and each scene already carries its own `pressure` line). One story line plus its comment, two variations, offline prompt-diff checks across all nine scenes. The frozen control is copied in by the check only. Zero narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-bio-goal"
GOAL = " She wants to find her best friend, Michelle."
OLD_BIO = (
    "A 47-year-old former assessment lead for the U.S. Army with a background in Army intelligence, "
    "infrastructure, and operations who is practical, persistent, and reluctant to trust conspiracy theories." + GOAL
)
NEW_BIO = OLD_BIO[: -len(GOAL)]
OLD_COMMENT = "# This narrator-safe bio preserves her characterisation and immediate goal without previewing that role."
NEW_COMMENT = "# This narrator-safe bio preserves her characterisation without previewing that role. It names no goal: each scene's pressure line gives the current one."

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD bio text this task deliberately changes; never weaken, skip or delete any other test."""

SPEC = (
    COMMON
    + f"""

ROLE: story-text editor, bench-variation author and test writer. You may edit/create ONLY: data/stories/continuity-initiative/world.yaml (exactly two lines, below), bench/variations/richer-3a-bio-control.json and bench/variations/richer-3a-bio-candidate.json (new), tests/test_kristin_bio.py (new), and any other test under tests/ (NOT tests/fixtures/) that a failing test shows pins the OLD bio text of Kristin; update only that pin. Never touch knowledge.yaml, plot.md, storylets or any other story file, never touch tests/test_prompt_budget.py or tests/test_richer_1c.py, never edit tests/fixtures/*, and never create a bench/frozen/ directory (the control copy is made outside your worktree).

BACKGROUND: Kristin's `narrator_bio` (story-wide, shown in the CHARACTERS section of every scene where she appears) ends with a goal sentence: "{GOAL.strip()}". A goal is not who she is; it changes as the story goes on, and every scene already carries its own current goal in knowledge.yaml `scene_frames[].pressure` (the prompt shows it as "What presses on Kristin now: ..."). In scene 3A the bio says she wants to find Michelle while the SCENE and CONSTRAINTS sections say she and Michelle have reunited, and the narrator is contradicted by its own prompt. Michelle's own bio already says she is Kristin's closest friend, so the friendship stays.

THE CHANGE (wording supplied; do not invent replacements): in data/stories/continuity-initiative/world.yaml, npc `kristin`:
1. Replace the single line (keep indentation and the `narrator_bio:` key) so the value is exactly
  {NEW_BIO}
 (that is the old value without its last sentence "{GOAL.strip()}" and without the space before it; same plain style, no quotes added).
2. Replace the single comment line directly above it
  {OLD_COMMENT}
 with exactly
  {NEW_COMMENT}
Change NO other line of world.yaml. Do not change any other character's bio.
Variations: copy bench/variations/richer-3a-radio-candidate.json twice. `richer-3a-bio-control.json`: name `richer-3a-bio-control`, story_package `bench/frozen/continuity-pre-3a-bio`. `richer-3a-bio-candidate.json`: name `richer-3a-bio-candidate`, story_package `data/stories/continuity-initiative`. Everything else identical to richer-3a-radio-candidate.json. (The frozen directory does not exist in your worktree; do not create it and do not run anything that loads the control variation.)

TESTS (first; put them in the new file tests/test_kristin_bio.py; the prompt-building code in tests/test_knowledge_projection.py and tests/test_prompt_budget.py shows how to build a prompt for each scene):
1. Kristin's bio is exactly the new text; every other npc's `narrator_bio` equals the literal read from world.yaml BEFORE you edit it (copy the literals into the test); Kristin's bio contains no goal wording ("wants" does not appear).
2. For EVERY scene of the story (1A, 1B, 1C, 2A, 2B, 2C, 3A, 3B, 3C), build the first-turn narrator prompt from the live package the same way tests/test_prompt_budget.py builds its per-scene prompts, and again from the same package with Kristin's bio replaced by the OLD text "{OLD_BIO}" (copy the loaded package and replace that one character with dataclasses.replace or model_copy; do not edit files). For each scene the system prompts are byte identical and the user prompts differ in EXACTLY ONE line: the CHARACTERS line for Kristin (old line versus new line, same position), and the live user prompt is shorter by exactly len("{GOAL}") characters. State the whole expected diff as one exact assertion per scene.
3. Every scene's SCENE section still shows its own "What presses on Kristin now: ..." line, taken from knowledge.yaml `scene_frames` for that scene (compare to the file's literal pressure for each scene that has one).
Then run: tests/test_kristin_bio.py tests/test_richer_3a.py tests/test_knowledge_projection.py tests/test_1c_closeout.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_budget.py tests/test_audit_unbound_item.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_world_model.py tests/test_world_companions.py, plus every test file whose grep for the old bio text or `narrator_bio` matched (excluding tests/fixtures). Do NOT raise any prompt-size ceiling or edit tests/fixtures/deep_turn_budget.json: a shorter prompt passes the ratchet unchanged.

REPORT FILE (a throwaway, never committed): after the change, write `scene-characters.json` in the worktree root. It maps each of the nine scene ids to {{"characters": [the CHARACTERS lines of that scene's first-turn narrator prompt, one string each], "pressure": the "What presses on Kristin now" line (or null)}}. Produce it with a one-off python command, not a saved script. The orchestrator reads it to see which scenes still say Michelle is Kristin's closest friend.

FINAL MESSAGE: the two-line world.yaml diff, every test added or changed (one line each), the measured prompt difference per scene (characters removed), and anything surprising.
"""
)

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
F=bench/frozen/continuity-pre-3a-bio
CH=$(git status --porcelain | grep -v '^?? .venv' | grep -v '^?? scene-characters.json' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in tests/fixtures/*|bench/frozen/*|tests/test_prompt_budget.py|tests/test_richer_1c.py) echo "WHY: forbidden path: $f"; exit 1;; $D/world.yaml|tests/*|bench/variations/richer-3a-bio-control.json|bench/variations/richer-3a-bio-candidate.json) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
git add -A -- $D tests bench/variations
test "$(git diff --cached --numstat -- $D | awk '{a+=$1; d+=$2} END {print a" "d}')" = "2 2" || { echo "WHY: story package must change exactly 2 added and 2 removed lines"; git diff --cached --stat -- $D; exit 1; }
git diff --cached --numstat -- $D | awk '{print $3}' | grep -qx "$D/world.yaml" || { echo "WHY: only world.yaml may change under $D"; exit 1; }
$PY - <<'E' || exit 1
import subprocess, yaml
D = "data/stories/continuity-initiative"
head = subprocess.run(["git", "show", f"HEAD:{D}/world.yaml"], capture_output=True, text=True, check=True).stdout
a, b = yaml.safe_load(head), yaml.safe_load(open(f"{D}/world.yaml"))
na = {n["id"]: n for n in a["npcs"]}; nb = {n["id"]: n for n in b["npcs"]}
assert list(na) == list(nb), "npc ids or order changed"
for k in na:
    if k != "kristin": assert na[k] == nb[k], f"npc {k} changed"
ka, kb = dict(na["kristin"]), dict(nb["kristin"])
assert ka["narrator_bio"] == "OLD_BIO", f"HEAD bio unexpected: {ka['narrator_bio']!r}"
assert kb["narrator_bio"] == "NEW_BIO", f"bio wrong: {kb['narrator_bio']!r}"
ka.pop("narrator_bio"); kb.pop("narrator_bio"); assert ka == kb, "another field of kristin changed"
assert {k: v for k, v in a.items() if k != "npcs"} == {k: v for k, v in b.items() if k != "npcs"}, "non-npc keys changed"
text = open(f"{D}/world.yaml").read()
assert "NEW_COMMENT" in text, "comment line not exactly as supplied"
assert "OLD_COMMENT" not in text, "old comment line still present"
print("story diff exact")
E
$PY - <<'E' || exit 1
import json
a=json.load(open('bench/variations/richer-3a-radio-candidate.json')); c=json.load(open('bench/variations/richer-3a-bio-control.json')); v=json.load(open('bench/variations/richer-3a-bio-candidate.json'))
for x,n,p in ((c,'richer-3a-bio-control','bench/frozen/continuity-pre-3a-bio'),(v,'richer-3a-bio-candidate','data/stories/continuity-initiative')):
    assert x['name']==n and x['story_package']==p, (n, x['name'], x['story_package'])
    y=dict(x); y['name']=a['name']; y['story_package']=a['story_package']
    assert y==a, f'{n} differs from richer-3a-radio-candidate beyond name/package'
print('variations ok')
E
# the frozen control is made outside the worktree; copy it in for the offline capture only, remove it before the patch export
[ -d /home/bcorfman/dev/freytag-forge/$F ] || { echo "WHY: frozen control missing in the main checkout"; exit 1; }
mkdir -p $F && cp /home/bcorfman/dev/freytag-forge/$F/* $F/
mkdir -p OUTDIR/cap
for arm in control candidate; do $PY -m bench.frozen_prompts capture bench/variations/richer-3a-bio-$arm.json 4 5 --out OUTDIR/cap/frozen-$arm.json > OUTDIR/cap/$arm.log 2>&1 || { echo "WHY: offline capture failed for $arm"; tail -20 OUTDIR/cap/$arm.log; rm -rf $F; exit 1; }; done
rm -rf $F
$PY - <<'E' || exit 1
import json
OLD = "OLD_BIO"; NEW = "NEW_BIO"
OLD_LINE = "- Kristin Schweitzer is a" + OLD[1:]; NEW_LINE = "- Kristin Schweitzer is a" + NEW[1:]
c=json.load(open('OUTDIR/cap/frozen-control.json')); d=json.load(open('OUTDIR/cap/frozen-candidate.json'))
assert len(c['endpoints'])==len(d['endpoints'])==2
for a,b in zip(c['endpoints'],d['endpoints']):
    n=a['n']; assert n==b['n'] and a['command']==b['command']
    assert a['committed_after_prefix']==b['committed_after_prefix'], f'c{n}: committed facts differ'
    wa,wb=a['wire_payload'],b['wire_payload']
    assert wa['system']==wb['system'], f'c{n}: system prompt differs'
    assert wa['max_tokens']==wb['max_tokens'] and wa['response_format']==wb['response_format'], f'c{n}: request settings differ'
    la,lb=wa['user'].splitlines(), wb['user'].splitlines()
    assert len(la)==len(lb), f'c{n}: line count differs'
    changed=[(x,y) for x,y in zip(la,lb) if x!=y]
    assert changed==[(OLD_LINE,NEW_LINE)], f'c{n}: expected exactly the Kristin CHARACTERS line to change, got {changed}'
    ta=len(wa['user'])+len(wa['system']); tb=len(wb['user'])+len(wb['system'])
    assert ta-tb==len(OLD)-len(NEW), f'c{n}: size change {ta-tb} is not the removed sentence'
    print(f'c{n}: payload diff ok; chars', ta, '->', tb)
E
$PY -m pytest -q -p no:cacheprovider tests/test_kristin_bio.py tests/test_richer_3a.py tests/test_knowledge_projection.py tests/test_1c_closeout.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_budget.py tests/test_audit_unbound_item.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_world_model.py tests/test_world_companions.py > /tmp/tbio.out 2>&1; rc=$?; tail -25 /tmp/tbio.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
[ -f scene-characters.json ] || { echo "WHY: scene-characters.json report missing"; exit 1; }
$PY - <<'E' || exit 1
import json
r = json.load(open('scene-characters.json'))
assert sorted(r) == sorted(['1A','1B','1C','2A','2B','2C','3A','3B','3C']), f'scene ids wrong: {sorted(r)}'
for s, v in r.items():
    assert v['characters'], f'{s}: no character lines'
    k = [x for x in v['characters'] if x.startswith('Kristin Schweitzer')]
    assert len(k) == 1 and 'wants to find' not in k[0], f'{s}: Kristin line wrong: {k}'
print('scene report ok')
E
mkdir -p OUTDIR && mv scene-characters.json OUTDIR/scene-characters.json
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
git status --porcelain | grep -q "bench/frozen" && { echo "WHY: frozen directory left in the worktree"; exit 1; }
git diff --cached > OUTDIR/bio-goal.patch && wc -l OUTDIR/bio-goal.patch && git diff --cached --stat | tail -12
""".replace("OUTDIR", OUT)
CHECK = (
    CHECK.replace("OLD_BIO", OLD_BIO)
    .replace("NEW_BIO", NEW_BIO)
    .replace("OLD_COMMENT", OLD_COMMENT)
    .replace("NEW_COMMENT", NEW_COMMENT)
)

manifest = {
    "run_name": "3a-bio-goal",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "bio-goal",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "data/stories/continuity-initiative/world.yaml",
                "bench/variations/richer-3a-bio-control.json",
                "bench/variations/richer-3a-bio-candidate.json",
                "tests/test_kristin_bio.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests added first, two-line change, exact prompt diff offline for 3A and every scene, suites and ruff pass, patch exported",
        }
    ],
}
Path(__file__).with_name("bio-goal-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
