# ruff: noqa: E501
"""Plan experiment S (free part): the speaker-line template stops inviting literal utterance. Engine-only, one line."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/3a-speech-template"
CTL = f"{REPO}/bench/results/richer-3a-probe/bio"

SPEC = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, never run `python -m bench run` or `python -m bench.frozen_prompts replay`. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>`. Ruff: `.venv/bin/python -m ruff check <files>` and `-m ruff format <files>`. Leave changes uncommitted. TESTS FIRST.

ROLE: engine editor and test writer. Edit ONLY storygame/runtime/cloudflare.py and tests under tests/ (update a test only if it pins the OLD wording below; never weaken or delete others). Do not touch data/, bench/, scripts/, packages/, or any other source file.

THE CHANGE (exactly one template, nothing else). In `CloudflareTurnProvider._speaker_constraint_lines` (storygame/runtime/cloudflare.py) the line is built as `f"{{self._display_name(speaker_id)}} may say this aloud: {{item['statement']}}"`. Change ONLY the words so the line reads `<Name> may talk about this fact: <statement>` (f"{{name}} may talk about this fact: {{item['statement']}}"). Keep: one line per eligible speaker per fact, their order, the present-or-named filter, the exact fact text. Do not add any new rule, header or sentence anywhere; do not touch the system prompt, SCENE, or any other section. Grep storygame/ and tests/ for the old phrase `may say this aloud` and for anything else that depends on it (prompt-presence, speaker-lines, leakage and budget tests, bench helpers under tests/); update only pins of that phrase. The new phrase is 3 characters shorter per line? compute and report the exact character difference per line (do not raise any size ceiling).

TESTS: write first a test (tests/test_speaker_lines.py, existing file) that the speaker lines for a present speaker use `may talk about this fact:` and never `may say this aloud`, with the statement text unchanged, filtering unchanged (an absent unnamed speaker gets no line), one line per statement per speaker. Then run: tests/test_speaker_lines.py tests/test_speaker_presence.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_knowledge_leakage_matrix.py tests/test_scene_roleplay_contract.py tests/test_prompt_budget.py tests/test_richer_3a.py tests/test_frozen_prompts.py tests/test_bench.py tests/test_place_scoped_feed.py plus every test file that `grep -l "may say this aloud"` matches. tests/test_place_scoped_feed.py may fail on the 1B opening golden for a reason unrelated to this task (a separate pending change in the main checkout); report it, do not touch it.

FINAL MESSAGE: the diff, every test changed or added, the per-line character difference, anything else that mentions the old phrase.
"""

CHECK = f"""set -o pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
mkdir -p {WORK}/cap
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{{print $2}}' | sort)
[ -n "$CH" ] || {{ echo "WHY: nothing changed"; exit 1; }}
for f in $CH; do case "$f" in storygame/runtime/cloudflare.py|tests/*) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
echo "$CH" | grep -qx storygame/runtime/cloudflare.py || {{ echo "WHY: cloudflare.py not changed"; exit 1; }}
test "$(git diff -- storygame/runtime/cloudflare.py | grep -c '^[+-][^+-]')" = 2 || {{ echo "WHY: cloudflare.py must change exactly one line"; git diff -- storygame/runtime/cloudflare.py; exit 1; }}
git diff -- storygame/runtime/cloudflare.py | grep -q "may talk about this fact:" || {{ echo "WHY: new phrase missing"; exit 1; }}
grep -rn "may say this aloud" storygame && {{ echo "WHY: old phrase still in storygame/"; exit 1; }}
git add -A -- storygame tests
cp {REPO}/bench/variations/richer-3a-people-candidate.json {WORK}/cap/var.json
$PY -m bench.frozen_prompts capture {WORK}/cap/var.json 4 5 --out {WORK}/cap/frozen-S.json > {WORK}/cap/capture.log 2>&1 || {{ echo "WHY: offline capture failed"; tail -20 {WORK}/cap/capture.log; exit 1; }}
$PY - <<'E2'
import difflib, json
W='{WORK}/cap'
d=json.load(open(W+'/frozen-S.json'))
for b in d['endpoints']:
    n=b['n']; a=json.load(open(f'{CTL}/frozen-candidate-c{{n}}.json'))['endpoints'][0]
    wa,wb=a['wire_payload'],b['wire_payload']
    assert wa['system']==wb['system'], f'c{{n}}: system differs'
    ua=wa['user']; ub=wb['user']
    ua2=ua.replace(' may say this aloud: ',' may talk about this fact: ')
    n_lines=ua.count(' may say this aloud: ')
    assert n_lines>=1, f'c{{n}}: control has no speaker lines'
    # the worktree is at HEAD: presence line and placement text are absent here, so everything else must match exactly
    assert ua2==ub, 'c%d: payloads differ beyond the template:\\n'%n+'\\n'.join(l for l in difflib.unified_diff(ua2.splitlines(),ub.splitlines(),lineterm='') )
    print(f'c{{n}}: only the template changed on {{n_lines}} speaker lines; chars', len(ua),'->',len(ub))
E2
$PY -m pytest -q -p no:cacheprovider tests/test_speaker_lines.py tests/test_speaker_presence.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_knowledge_leakage_matrix.py tests/test_scene_roleplay_contract.py tests/test_prompt_budget.py tests/test_richer_3a.py tests/test_frozen_prompts.py tests/test_bench.py -rf > {WORK}/suite.out 2>&1; rc=$?; tail -15 {WORK}/suite.out; [ $rc -eq 0 ] || {{ echo "WHY: suites failed"; exit 1; }}
PYF=$(echo "$CH" | grep '\\.py$' || true)
if [ -n "$PYF" ]; then $PY -m ruff check $PYF && $PY -m ruff format --check $PYF || {{ echo "WHY: ruff"; exit 1; }}; fi
git diff --cached > {WORK}/speech-template.patch && wc -l {WORK}/speech-template.patch && git diff --cached --stat | tail -6
"""

manifest = {
    "run_name": "3a-speech-template",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "speech-template",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=low"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": ["storygame/runtime/cloudflare.py", "tests/test_speaker_lines.py"],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "one template line changed, payload differs from the saved control only by that template, suites and ruff pass, patch exported",
        }
    ],
}
Path(__file__).with_name("speech-template-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
