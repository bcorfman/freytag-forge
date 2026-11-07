# ruff: noqa: E501
"""A-r1 statement manifest: the 3A reunion statement drops its radios sentence (which repeats the scene frame and the A-r1 delivery). One knowledge line, two variations, in-memory prompt-diff tests. The frozen control is copied in by the check only. Zero narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-a1-statement"
OLD = "Kristin and Michelle have reunited. Michelle coordinates the prisoners through stolen radios and coded announcements."
NEW = "Kristin and Michelle have reunited."

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD statement this task deliberately changes; never weaken, skip or delete any other test."""

SPEC = (
    COMMON
    + f"""

ROLE: story-text editor, bench-variation author and test writer. You may edit/create ONLY: data/stories/continuity-initiative/knowledge.yaml (exactly one line), bench/variations/richer-3a-a1-control.json and bench/variations/richer-3a-a1-candidate.json (new), tests/test_richer_3a.py, tests/test_1c_closeout.py (only the pin of the old statement), tests/test_knowledge_projection.py (only pins of the old statement), and any other test under tests/ (NOT tests/fixtures/) that a failing test shows pins the OLD statement text of `k_sl_3a_a_r1`; update only that pin. Never touch world.yaml, plot.md, storylets or any other story file, and never create a bench/frozen/ directory (the control copy is made outside your worktree).

BACKGROUND: the 3A reunion entry `k_sl_3a_a_r1` has the statement "{OLD}". Replays showed that the narrator copies the second sentence (Michelle coordinating by radios and coded announcements) into its reply in 8 of 12 replays, even when no character may say it. That sentence repeats what the scene already says (the 3A entry text and scene frame mention scattered stolen radios and coded announcements, and the A-r1 delivery text says Michelle "turns back to her coded announcements"). The other entry `k_sl_3a_a_r2` shares the same facts and must stay exactly as it is.

THE CHANGE (wording supplied; do not invent replacements): in data/stories/continuity-initiative/knowledge.yaml, entry `k_sl_3a_a_r1`, replace the single line
  statement: '{OLD}'
with exactly
  statement: '{NEW}'
(same single-quote style, same indentation). Change NO other line of knowledge.yaml.
Variations: copy bench/variations/richer-3a-radio-candidate.json twice. `richer-3a-a1-control.json`: name `richer-3a-a1-control`, story_package `bench/frozen/continuity-pre-3a-a1`. `richer-3a-a1-candidate.json`: name `richer-3a-a1-candidate`, story_package `data/stories/continuity-initiative`. Everything else identical to richer-3a-radio-candidate.json. (The frozen directory does not exist in your worktree; do not create it and do not run anything that loads the control variation.)

TESTS (first; use the helpers in tests/test_richer_3a.py such as `_engine`, `_handoff`, `_authored_provider`; the prompt-building code in tests/test_knowledge_projection.py and tests/test_prompt_budget.py shows how to build a prompt):
1. `k_sl_3a_a_r1` has the new statement; every OTHER field of it is unchanged and written as literals read from the file BEFORE you edit (delivery_text, must_convey, requires, establishes, action_evidence, earn_when, audience, aliases, available_in_scenes, source, relevance, voiceable). `k_sl_3a_a_r2` is unchanged: its statement is exactly "Michelle has explained that freeing this block means little without exposing the other sites." and every other field is as before.
2. Prompt diff, built IN MEMORY, no frozen directory: at the reunion state reached through the real engine (the `Free the captives.` path, so the facts michelle_reached and uprising_prepared are true), build the narrator prompt from the live package, and again from the same package with the A-r1 statement replaced by the old string "{OLD}" (copy the loaded package and replace that one entry, for example with dataclasses.replace on the knowledge entry; do not edit files). The system prompts are byte identical, and the user prompts differ in EXACTLY four line pairs: the SCENE line and the three per-speaker 'may say this aloud' lines (Dr. Michelle McGehee, Brandon Corfman, Imprisoned senior official) for that statement, old text versus new text, in the same order and position; nothing else differs. State the whole expected diff as one exact assertion, and assert the live prompt is shorter by exactly 4 times (len(old statement) - len(new statement)) characters.
3. Before the reunion (3A entry state, no reunion facts): the two prompts are byte identical (the statement is not shown yet).
4. Both earned paths still work: the A-r1 command (`Free the captives.`) and the A-r2 command (the existing A-r2 command in the file, e.g. `Ask Michelle about other sites.`) earn exactly the deliveries and facts they earned before (the existing tests for these must still pass unchanged apart from the old-statement pin).
5. The narrator may still describe what the scene already says: with the engine and an authored/scripted provider, a narrator reply made of ONE plain narration segment that says "Michelle speaks into a stolen radio, passing coded announcements to the prisoners." (no grounding ids, no knowledge ids) is ACCEPTED (not rejected, not retried) both at the 3A opening state and at the reunion state. If either case is rejected because of the removed sentence or its words, DO NOT work around it: report the exact rejection reason and test names in the final message (the task is then blocked and the orchestrator decides).
Then run: tests/test_richer_3a.py tests/test_knowledge_projection.py tests/test_1c_closeout.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_budget.py tests/test_audit_unbound_item.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_world_model.py, plus every test file whose grep for the old statement text, `k_sl_3a_a_r1` or `stolen radios and coded` matched (excluding tests/fixtures). Do NOT raise any prompt-size ceiling or edit tests/fixtures/deep_turn_budget.json: a shorter prompt passes the ratchet unchanged.

FINAL MESSAGE: the one-line knowledge.yaml diff, every test changed or added (one line each), the measured prompt difference (characters removed, per occurrence and in total), and anything surprising (especially any rejection in test 5).
"""
)

CHECK = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
F=bench/frozen/continuity-pre-3a-a1
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in tests/fixtures/*|bench/frozen/*) echo "WHY: forbidden path: $f"; exit 1;; $D/knowledge.yaml|tests/*|bench/variations/richer-3a-a1-control.json|bench/variations/richer-3a-a1-candidate.json) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
git add -A -- $D tests bench/variations
test "$(git diff --cached --numstat -- $D | awk '{a+=$1; d+=$2} END {print a" "d}')" = "1 1" || { echo "WHY: story package must change exactly 1 added and 1 removed line"; git diff --cached --stat -- $D; exit 1; }
git diff --cached --numstat -- $D | awk '{print $3}' | grep -qx "$D/knowledge.yaml" || { echo "WHY: only knowledge.yaml may change under $D"; exit 1; }
$PY - <<'E' || exit 1
import subprocess, yaml
D = "data/stories/continuity-initiative"
head = subprocess.run(["git", "show", f"HEAD:{D}/knowledge.yaml"], capture_output=True, text=True, check=True).stdout
a, b = yaml.safe_load(head), yaml.safe_load(open(f"{D}/knowledge.yaml"))
ea = {e["id"]: e for e in a["knowledge"]}; eb = {e["id"]: e for e in b["knowledge"]}
assert list(ea) == list(eb), "entry ids or order changed"
for k in ea:
    if k != "k_sl_3a_a_r1": assert ea[k] == eb[k], f"entry {k} changed"
ta, tb = dict(ea["k_sl_3a_a_r1"]), dict(eb["k_sl_3a_a_r1"])
assert ta["statement"] == "OLD_X", f"HEAD statement unexpected: {ta['statement']!r}"
assert tb["statement"] == "NEW_X", f"statement wrong: {tb['statement']!r}"
ta.pop("statement"); tb.pop("statement"); assert ta == tb, "another field of k_sl_3a_a_r1 changed"
assert {k: v for k, v in a.items() if k != "knowledge"} == {k: v for k, v in b.items() if k != "knowledge"}, "non-knowledge keys changed"
print("story diff exact")
E
$PY - <<'E' || exit 1
import json
a=json.load(open('bench/variations/richer-3a-radio-candidate.json')); c=json.load(open('bench/variations/richer-3a-a1-control.json')); v=json.load(open('bench/variations/richer-3a-a1-candidate.json'))
for x,n,p in ((c,'richer-3a-a1-control','bench/frozen/continuity-pre-3a-a1'),(v,'richer-3a-a1-candidate','data/stories/continuity-initiative')):
    assert x['name']==n and x['story_package']==p, (n, x['name'], x['story_package'])
    y=dict(x); y['name']=a['name']; y['story_package']=a['story_package']
    assert y==a, f'{n} differs from richer-3a-radio-candidate beyond name/package'
print('variations ok')
E
# the frozen control is made outside the worktree; copy it in for the offline capture only, remove it before the patch export
[ -d /home/bcorfman/dev/freytag-forge/$F ] || { echo "WHY: frozen control missing in the main checkout"; exit 1; }
mkdir -p $F && cp /home/bcorfman/dev/freytag-forge/$F/* $F/
mkdir -p OUTDIR/cap
for arm in control candidate; do $PY -m bench.frozen_prompts capture bench/variations/richer-3a-a1-$arm.json 4 5 --out OUTDIR/cap/frozen-$arm.json > OUTDIR/cap/$arm.log 2>&1 || { echo "WHY: offline capture failed for $arm"; tail -20 OUTDIR/cap/$arm.log; rm -rf $F; exit 1; }; done
rm -rf $F
$PY - <<'E' || exit 1
import difflib, json
OLD = "OLD_X"; NEW = "NEW_X"
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
    assert len(changed)==4, f'c{n}: expected exactly 4 changed lines, got {len(changed)}: {changed}'
    assert sum(1 for x,y in changed if x==f'- {OLD}' and y==f'- {NEW}')==1, f'c{n}: SCENE line not changed exactly'
    for who in ('Dr. Michelle McGehee','Brandon Corfman','Imprisoned senior official'):
        assert (f'- {who} may say this aloud: {OLD}', f'- {who} may say this aloud: {NEW}') in changed, f'c{n}: speaker line for {who} not changed exactly'
    ta=len(wa['user'])+len(wa['system']); tb=len(wb['user'])+len(wb['system'])
    assert ta-tb==4*(len(OLD)-len(NEW)), f'c{n}: size change {ta-tb} is not 4x the statement difference'
    print(f'c{n}: payload diff ok; chars', ta, '->', tb)
E
$PY -m pytest -q -p no:cacheprovider tests/test_richer_3a.py tests/test_knowledge_projection.py tests/test_1c_closeout.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_audit_budget.py tests/test_audit_unbound_item.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_handoff_typed_tiebreak.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_world_model.py > /tmp/ta1.out 2>&1; rc=$?; tail -25 /tmp/ta1.out; [ $rc -eq 0 ] || { echo "WHY: suites failed (a rejection in the narrator-description test means the task is blocked: report it)"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
git status --porcelain | grep -q "bench/frozen" && { echo "WHY: frozen directory left in the worktree"; exit 1; }
mkdir -p OUTDIR && git diff --cached > OUTDIR/a1-statement.patch && wc -l OUTDIR/a1-statement.patch && git diff --cached --stat | tail -12
""".replace("OUTDIR", OUT)
CHECK = CHECK.replace("OLD_X", OLD).replace("NEW_X", NEW)

manifest = {
    "run_name": "3a-a1-statement",
    "workdir": OUT,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "a1-statement",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 900,
            "ownership": [
                "data/stories/continuity-initiative/knowledge.yaml",
                "bench/variations/richer-3a-a1-control.json",
                "bench/variations/richer-3a-a1-candidate.json",
                "tests/test_richer_3a.py",
                "tests/test_1c_closeout.py",
                "tests/test_knowledge_projection.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "tests added first, one-line change, exact prompt diff offline, suites and ruff pass, patch exported",
        }
    ],
}
Path(__file__).with_name("a1-statement-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
