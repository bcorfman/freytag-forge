# ruff: noqa: E501
"""Write embrace-manifest.json: one Ringer task (tests first) giving the 3A reunion its emotional embrace in the authored delivery text
(knowledge.yaml a_r1 and a_r2 delivery_text, handoffs.yaml michelle_reached fallback_text). Wording reviewed with Brandon 2026-11-07; no 'Shelly'.
The check uses no bashisms (Ringer runs checks under /bin/sh)."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/shared-narrator-embrace"
HERE = Path(__file__).parent

A_R1 = (
    "Kristin joins Michelle beside the captives. They are awake: the dose they were given is for the trip, and it wears off in the detention block. "
    'Michelle looks up, goes completely still, and then pulls Kristin into a tight embrace. "You\'re here," she says, her voice breaking. "You\'re really here." '
    "Kristin holds on just as hard, and for one unhurried moment nobody asks anything of either of them. "
    "Then Michelle wipes her eyes, turns back to her coded announcements, and points toward the medical level, where the experiment records wait."
)
A_R2 = (
    'Michelle looks up, goes completely still, and pulls Kristin into a tight embrace. "You\'re really here," she says, her voice breaking. '
    "For one unhurried moment nobody asks anything of either of them. "
    "Then she wipes her eyes and explains that freeing this block means little without exposing the other sites. "
    "Michelle points toward the medical level, where the experiment records wait."
)
FALLBACK = (
    "Kristin reaches Michelle among the holding blocks in the detention sector. They embrace and share one unhurried moment before "
    "Michelle turns back to the radio and the rescue."
)

TESTS = (
    "tests/test_richer_3a.py tests/test_1c_closeout.py tests/test_speaker_text.py tests/test_speaker_lines.py tests/test_cloudflare_transport.py "
    "tests/test_knowledge_projection.py tests/test_knowledge_narrated_gate.py tests/test_knowledge_leakage_matrix.py tests/test_package_audit.py "
    "tests/test_markdown_story_package.py tests/test_story_package_cache.py tests/test_world_second_package.py tests/test_act2_knowledge_sources.py "
    "tests/test_voiceable_knowledge.py tests/test_incidental_package.py tests/test_3c_adopted_package.py"
)

SPEC = f"""You work in the MAIN checkout of the game repo: {REPO} (not a worktree; it holds many uncommitted changes that belong to other work and MUST stay untouched). FIRST run `cd {REPO}`. NEVER git commit, git stash, git checkout/restore/reset, never `uv`, never call a billed model or the network, never run `python -m bench run`, `python -m bench.frozen_prompts replay` or any script that calls a model. Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>`. Ruff: `.venv/bin/python -m ruff check <files>` and `-m ruff format <files>`. Do not edit any file except those listed under OWNERSHIP.

BACKGROUND. In scene 3A the player reaches Michelle, her closest friend, in the detention block. The game appends authored text once when that reunion is earned (a knowledge entry's `delivery_text`, or the handoff `fallback_text` when the engine forces the handoff). Today that text only says the two share "one unhurried moment". Brandon wants it to be an emotional reunion with an embrace. The opening cue (`cue_text`) must stay unchanged: the opening shows Michelle at work and no greeting. This task changes authored story TEXT only: no code, no schema, no `speaker_text`.

TASK. Make exactly these three text replacements and nothing else. Choose any valid YAML quoting so that the loaded strings equal EXACTLY the following (do not edit, re-punctuate or reflow the words):
1. data/stories/continuity-initiative/knowledge.yaml, entry `k_sl_3a_a_r1`, field `delivery_text`:
{A_R1!r}
2. data/stories/continuity-initiative/knowledge.yaml, entry `k_sl_3a_a_r2`, field `delivery_text`:
{A_R2!r}
3. data/stories/continuity-initiative/handoffs.yaml, fact `michelle_reached`, field `fallback_text` (it is a folded scalar over two lines; keep a folded scalar and keep the lines at or under 120 characters):
{FALLBACK!r}
Do not touch `cue_text`, `must_convey`, any `statement`, any `speaker_text`, plot.md, storylets.md or storylet-routes.yaml (their wording "one unhurried moment" stays; it is still true).

TESTS FIRST. Find the tests that pin the old texts (grep tests/ for "joins Michelle beside the captives", "shares one unhurried moment", "share one unhurried moment before Michelle"; known: tests/test_richer_3a.py and tests/test_1c_closeout.py). Update those pins to the new exact strings FIRST, run them and see them fail for the right reason (record the failing summary in your final notes), then edit the YAML. Also add one meaningful test to tests/test_richer_3a.py: the new `a_r1` and `a_r2` delivery texts each contain an embrace and none of the words "Shelly" or "Shelly,", the opening `cue_text` of `michelle_reached` is unchanged, and the canonical `statement` of both entries is unchanged. Never delete or weaken a test; never loosen a rule.

EXISTING TESTS. Run the related suites in the check. If one fails only because it pins the old text, update just that expectation and keep its intent; list every existing test file you changed and why. If anything else fails (for example a narration-safety or leak scan on the new quoted dialogue), stop and report it rather than working around it.

OWNERSHIP. You may edit only: data/stories/continuity-initiative/knowledge.yaml, data/stories/continuity-initiative/handoffs.yaml, and files under tests/ whose pinned expectations change as described. Leave all changes uncommitted in place."""

CHECK = f"""cd {REPO} || exit 1
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
$PY scripts/ringer/shared-narrator/snapshot_tree.py {WORK}/after.json >/dev/null
$PY - <<'PY2' || exit 1
import json, re, sys
before = json.load(open('{WORK}/baseline.json')); after = json.load(open('{WORK}/after.json'))
changed = sorted(p for p in set(before) | set(after) if before.get(p) != after.get(p))
allowed = {{'data/stories/continuity-initiative/knowledge.yaml', 'data/stories/continuity-initiative/handoffs.yaml'}}
bad = [p for p in changed if p not in allowed and not re.fullmatch(r'tests/[A-Za-z0-9_]+\\.py', p)]
print('changed:', changed)
if bad:
    print('WHY: edited files outside ownership:', bad); sys.exit(1)
for need in sorted(allowed) + ['tests/test_richer_3a.py']:
    if need not in changed:
        print('WHY: expected change missing:', need); sys.exit(1)
PY2
for f in knowledge handoffs; do
  diff {WORK}/pre/$f.yaml data/stories/continuity-initiative/$f.yaml > {WORK}/$f.diff
  echo "$f changed lines: $(grep -c '^>' {WORK}/$f.diff) added, $(grep -c '^<' {WORK}/$f.diff) removed"
done
[ "$(grep -c '^<' {WORK}/knowledge.diff)" = 2 ] && [ "$(grep -c '^>' {WORK}/knowledge.diff)" = 2 ] || {{ echo "WHY: knowledge.yaml must change exactly two lines (the two delivery_text lines)"; cat {WORK}/knowledge.diff | cut -c1-160; exit 1; }}
[ "$(grep -c '^<' {WORK}/handoffs.diff)" -le 3 ] || {{ echo "WHY: handoffs.yaml changed more than the fallback_text"; cat {WORK}/handoffs.diff | cut -c1-160; exit 1; }}
grep -q 'embrace' data/stories/continuity-initiative/handoffs.yaml || {{ echo "WHY: handoffs fallback has no embrace"; exit 1; }}
[ "$(grep -c 'speaker_text:' data/stories/continuity-initiative/knowledge.yaml)" = 9 ] || {{ echo "WHY: speaker_text entries changed"; exit 1; }}
$PY -m pytest -q -p no:cacheprovider {TESTS} > /tmp/embrace-pytest.txt 2>&1
rc=$?
tail -25 /tmp/embrace-pytest.txt
[ "$rc" = 0 ] || {{ echo "WHY: tests failed"; exit 1; }}
$PY -m ruff check storygame tests || exit 1
$PY -m ruff format --check storygame tests || exit 1
echo "embrace check ok"
"""

manifest = {
    "run_name": "shared-narrator-embrace",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "embrace",
            "task_type": "code-feature",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 2400,
            "ownership": [
                f"{REPO}/data/stories/continuity-initiative/knowledge.yaml",
                f"{REPO}/data/stories/continuity-initiative/handoffs.yaml",
                f"{REPO}/tests/test_richer_3a.py",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [f"{REPO}/tests/test_richer_3a.py"],
            "verified": "pins updated first and failing, texts exact, only two knowledge lines and the fallback changed, related suites pass, ruff clean",
        }
    ],
}
(HERE / "embrace-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("written", len(SPEC), "chars of spec")
