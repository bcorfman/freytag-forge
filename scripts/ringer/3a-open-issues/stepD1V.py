# ruff: noqa: E501
"""Step D1-V manifest (round 1): the two voiceable:false flags with a frozen D1 control, and an offline decode/validate replay of D1's saved c4 replies. Zero narrator neurons."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = "/home/bcorfman/dev/ringer-work/3a-open-issues-stepD1V"

COMMON = f"""Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch the main checkout, never run `uv`, never call a billed model, MCP indexing or the network, and never run `python -m bench run` or `python -m bench.frozen_prompts replay` or any script that calls a model. FIRST run: [ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv ; then run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider <tests>` (PYTHONPATH must include $PWD/packages/worldkeeper/src, otherwise worldkeeper imports from the MAIN checkout). Ruff: `.venv/bin/python -m ruff check <py files>` and `-m ruff format <py files>`. Leave changes uncommitted. Work TESTS FIRST: write the new tests, run them, see them fail for the right reason, then make the change. You may update an existing test only if it pins the OLD behaviour this task deliberately changes; never weaken, skip or delete any other test."""

SPEC_EDIT = (
    COMMON
    + """

ROLE: story-package editor, bench-variation author and test writer. You may edit/create ONLY: data/stories/continuity-initiative/knowledge.yaml (exactly two added lines), bench/frozen/continuity-pre-3a-d1v/ (new: a byte-identical copy of the nine package files in data/stories/continuity-initiative/ AS THEY ARE AT HEAD, made BEFORE you edit knowledge.yaml; copy exactly the same file set that bench/frozen/continuity-pre-3a-d1/ holds), bench/variations/richer-3a-d1-control.json and bench/variations/richer-3a-d1v.json (new), tests/test_richer_3a.py, tests/test_speaker_lines.py (you may only ADD tests to the latter), and any other test under tests/ that a failing test shows pins the observation status of k_sl_3a_a_r1 or k_sl_3a_a_r2 (update only that pin).

THE CHANGE (wording supplied; do not invent replacements): in data/stories/continuity-initiative/knowledge.yaml add exactly one line `  voiceable: false` (two-space indent, same style as the other voiceable lines in that file, e.g. the one under k_sl_1b_b_r0) inside each of the two entries `k_sl_3a_a_r1` and `k_sl_3a_a_r2`, directly under the `statement:` line. Change NO other field of any entry. The two statements stay the short D1 statements.
Variations: copy bench/variations/richer-3a-d1.json twice. `richer-3a-d1-control.json`: name `richer-3a-d1-control`, story_package `bench/frozen/continuity-pre-3a-d1v` (the frozen D1 state is the control). `richer-3a-d1v.json`: name `richer-3a-d1v`, story_package `data/stories/continuity-initiative`. Everything else (script of nine commands, thorough entry state, entry_facts, item_facts, judges off) is identical to richer-3a-d1.json.

TESTS (first):
- In tests/test_richer_3a.py: both entries have `voiceable` false; every other field of both entries (statement, delivery_text, must_convey, requires, establishes, action_evidence, earn_when, audience) equals the frozen D1 copy bench/frozen/continuity-pre-3a-d1v/knowledge.yaml (load both packages and compare the entries field by field; the only allowed difference is voiceable). The frozen copy equals HEAD's other eight files byte for byte.
- Projection: with michelle_reached and uprising_prepared true in 3A (use the helpers in the file, e.g. `_engine(true_facts=ARRIVED)`), the SCENE section of the projected narration prompt STILL contains both short statements (an observation is hidden from speakers, never from SCENE), while NO per-speaker "may say this aloud" line contains either statement; and the per-speaker lines for the OTHER 3A statements are unchanged: compare the set of per-speaker lines of the prompt built from the frozen D1 package against the new prompt: the difference is exactly the six lines (A-r1 and A-r2, for Michelle, Brandon and the senior official) at that state, nothing else, and the SCENE text and system prompt are byte identical. Look at tests/test_speaker_lines.py and tests/test_prompt_budget.py `_prompts` for how to build prompts for two packages.
- Both realizations: the A-r1 path (`Free the captives.`) and the A-r2 path (`Ask Michelle about other sites.`, or the existing command) still earn their reveals, deliveries and facts exactly as before (the existing tests for these must still pass unchanged).
- The new prompt is shorter than the frozen D1 prompt at that state by the length of those six lines.
- Add a short test to tests/test_speaker_lines.py that a `voiceable: false` statement still appears in SCENE and not in any speaker line (only if an equivalent test does not already exist; check first).
Then run: tests/test_richer_3a.py tests/test_knowledge_projection.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_frozen_prompts.py tests/test_bench.py, plus every test file whose grep for the two entry IDs matched. If a regenerated expectation file exists for the spine (scripts/generate_spine_expected_reveals.py), regenerate only if a test fails because of this change and report the diff.

FINAL MESSAGE: the two one-line diffs, every test changed or added, the frozen directory file list, and the per-speaker line difference you measured (character count).
"""
)

CHECK_EDIT = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
D=data/stories/continuity-initiative
F=bench/frozen/continuity-pre-3a-d1v
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in $D/knowledge.yaml|tests/*|$F/|$F/*|bench/variations/richer-3a-d1-control.json|bench/variations/richer-3a-d1v.json) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
git add -A -- $D bench tests
test "$(git diff --cached --numstat -- $D/knowledge.yaml | awk '{print $1+$2}')" = "2" || { echo "WHY: knowledge.yaml must change exactly two added lines"; git diff --cached -- $D/knowledge.yaml | head -40; exit 1; }
test "$(git diff --cached -U0 -- $D/knowledge.yaml | grep -c '^+  voiceable: false$')" = "2" || { echo "WHY: the two added lines must be '  voiceable: false'"; exit 1; }
for f in connections.yaml handoffs.yaml incidents.yaml pacing.yaml plot.md storylet-routes.yaml storylets.md world.yaml; do cmp $D/$f $F/$f || { echo "WHY: frozen copy of $f differs from HEAD"; exit 1; }; done
git show HEAD:$D/knowledge.yaml | cmp - $F/knowledge.yaml || { echo "WHY: frozen knowledge.yaml is not HEAD's"; exit 1; }
diff <(ls bench/frozen/continuity-pre-3a-d1) <(ls $F) || { echo "WHY: frozen file set differs from continuity-pre-3a-d1"; exit 1; }
$PY - <<'E' || exit 1
import json
a=json.load(open('bench/variations/richer-3a-d1.json')); c=json.load(open('bench/variations/richer-3a-d1-control.json')); v=json.load(open('bench/variations/richer-3a-d1v.json'))
for x,n,p in ((c,'richer-3a-d1-control','bench/frozen/continuity-pre-3a-d1v'),(v,'richer-3a-d1v','data/stories/continuity-initiative')):
    assert x['name']==n and x['story_package']==p, (n, x['name'], x['story_package'])
    y=dict(x); y['name']=a['name']; y['story_package']=a['story_package']
    assert y==a, f'{n} differs from richer-3a-d1 beyond name/package'
print('variations ok')
E
$PY -m pytest -q -p no:cacheprovider tests/test_richer_3a.py tests/test_knowledge_projection.py tests/test_speaker_lines.py tests/test_prompt_budget.py tests/test_prompt_presence.py tests/test_prompt_inert_lines.py tests/test_markdown_story_package.py tests/test_package_audit.py tests/test_scene_roleplay_contract.py tests/test_knowledge_leakage_matrix.py tests/test_speaker_presence.py tests/test_spine_expected_reveals.py tests/test_3ab_spine_prompts.py tests/test_3a_records_followup.py tests/test_late_scene_repro.py tests/test_discovery_continuity.py tests/test_frozen_prompts.py tests/test_bench.py > /tmp/td1v.out 2>&1; rc=$?; tail -25 /tmp/td1v.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
PYF=$(echo "$CH" | grep '\.py$' || true)
if [ -n "$PYF" ]; then
  $PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
  $PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
fi
mkdir -p OUTDIR && git diff --cached > OUTDIR/D1V-edit.patch && wc -l OUTDIR/D1V-edit.patch && git diff --cached --stat | tail -12
""".replace("OUTDIR", OUT)

SPEC_DECODE = (
    COMMON
    + """

ROLE: bench engineer. You may edit/create ONLY: bench/frozen_decode.py (new) and tests/test_frozen_decode.py (new). Do not edit any other file.

PURPOSE: an earlier billed replay (bench/results/richer-3a-probe/d1/d1-rows.json and control-rows.json, lists of {n, sample, command, narration, error, raw}) found that three D1 replies at endpoint n=4 (samples 4, 5, 6, one-based) did not parse as strict JSON (two repeat `item_facts` keys in a 4,225-character degenerate run, one is truncated at 859 characters), and that some parseable replies put a person in their own custody. Nobody has checked what the REAL engine does with such raw replies. Build an offline tool that feeds saved replies through the real decoding and validation code, with NO model call, and reports what survives.

BUILD bench/frozen_decode.py (importable, plus `python -m bench.frozen_decode ROWS.json --frozen FROZEN.json --out REPORT.json`):
1. Find the REAL decoder: read storygame/runtime/capture.py (ItemFactsProvider and the code that turns the model's raw `narration` string into segments and item_facts; there is a decoder that 'keeps finished segments') and storygame/runtime/validation.py (proposal validation, `selected_knowledge_ids`). Call those functions; do not reimplement or loosen them. Find, by reading code, how a recorded model reply string becomes (segments, selected_knowledge_ids, item_facts / proposed fact changes) and how the engine validates or rejects a proposal and applies fact changes. If the production path cannot be called without a network, call its pure decode and validate functions directly or with `_send_http` patched to return the saved raw body; never touch the network.
2. For each row of ROWS.json (skip rows with an error; note them), produce a record: n, sample, strict_json_parse (bool, via json.loads of the narration string), decoder_result (segments count and kinds, whether the decoder recovered from a partial or invalid reply, any exception type and message), validation_result (accepted, rejected with the engine's reason, or recovered), the proposed item_fact changes after decoding (item id -> place/holder/condition), and `self_custody` (bool: some item/person is proposed to be held by itself; look at how item_facts express holders). If FROZEN.json is given, build the validation context from the saved committed facts for that endpoint (`committed_after_prefix` in frozen-d1.json) when the validator needs it; if an engine state is required, rebuild it the way bench/frozen_prompts.py does for the same endpoint and say so in the report.
3. Report summary counts and a plain-language `limits` string saying exactly what was and was not exercised (for example: decode only, no committed-state apply).

TESTS (first, offline, fast, no network, no .env): (a) a well-formed reply decodes with strict_json_parse true and the expected segments; (b) a reply truncated in the middle of item_facts is processed without raising, and the report states whether segments survived; (c) a reply with repeated item_facts keys; (d) a reply with a self-custody proposal is flagged and the report states what the validator did with it (assert whatever the real code actually does, after reading it; do not assume); (e) a row with an error is skipped and noted; (f) the CLI writes REPORT.json. Build inputs for (a)-(d) from small synthetic strings AND, if present, the real rows of d1-rows.json samples 4-6 at n=4 (skip that test if the file is missing).
Run: tests/test_frozen_decode.py tests/test_frozen_prompts.py tests/test_bench.py.
Then RUN the CLI on the real files and write the reports (the check requires them): `python -m bench.frozen_decode bench/results/richer-3a-probe/d1/d1-rows.json --frozen bench/results/richer-3a-probe/d1/frozen-d1.json --out OUTDIR/decode-d1.json` and the same for control-rows.json with frozen-control.json -> OUTDIR/decode-control.json.

FINAL MESSAGE: what the real decoder and validator do with D1 c4 samples 4, 5 and 6 (accepted, recovered or rejected; which facts, if any, would be committed), how many of the 24 c4 rows in each arm put a person in their own custody and what the validator does with that, and the limits.
""".replace("OUTDIR", OUT)
)

CHECK_DECODE = r"""set -o pipefail
[ -e .venv ] || ln -s /home/bcorfman/dev/freytag-forge/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
PY=.venv/bin/python
CH=$(git status --porcelain | grep -v '^?? .venv' | awk '{print $2}' | sort)
[ -n "$CH" ] || { echo "WHY: nothing changed"; exit 1; }
for f in $CH; do case "$f" in bench/frozen_decode.py|tests/test_frozen_decode.py) ;; *) echo "WHY: edited file outside ownership: $f"; exit 1;; esac; done
grep -n "urlopen(\|requests\.\|httpx\.\|openai" bench/frozen_decode.py | grep -v "^[0-9]*:\s*#" && { echo "WHY: module must not touch the network"; exit 1; }
$PY -m pytest -q -p no:cacheprovider tests/test_frozen_decode.py tests/test_frozen_prompts.py tests/test_bench.py > /tmp/td1vd.out 2>&1; rc=$?; tail -25 /tmp/td1vd.out; [ $rc -eq 0 ] || { echo "WHY: suites failed"; exit 1; }
test -s OUTDIR/decode-d1.json && test -s OUTDIR/decode-control.json || { echo "WHY: decode reports missing; run the CLI on the real files"; exit 1; }
$PY - <<'E' || exit 1
import json
for name in ('decode-d1','decode-control'):
    r=json.load(open(f'OUTDIR/{name}.json'))
    recs=r['records'] if isinstance(r,dict) and 'records' in r else r
    n4=[x for x in recs if x.get('n')==4]
    assert len(n4)==12, (name, 'expected 12 records at n=4', len(n4))
    assert all('strict_json_parse' in x and 'self_custody' in x for x in n4), 'record fields missing'
    if name=='decode-d1':
        bad={x['sample'] for x in n4 if not x['strict_json_parse']}
        assert bad=={4,5,6}, f'strict-parse failures should be samples 4,5,6, got {bad}'
    assert isinstance(r,dict) and r.get('limits'), 'report needs a limits string'
print('reports ok')
E
PYF=$(echo "$CH" | grep '\.py$')
$PY -m ruff check $PYF || { echo "WHY: ruff check failed"; exit 1; }
$PY -m ruff format --check $PYF || { echo "WHY: ruff format failed"; exit 1; }
git add -A && git diff --cached > OUTDIR/D1V-decode.patch && wc -l OUTDIR/D1V-decode.patch && git diff --cached --stat | tail -6
""".replace("OUTDIR", OUT)


def task(key, spec, check, ownership, effort):
    return {
        "key": key,
        "task_type": "code-fix",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", f"model_reasoning_effort={effort}"],
        "max_attempts": 2,
        "timeout_s": 3000,
        "check_timeout_s": 900,
        "ownership": ownership,
        "spec": spec,
        "check": check,
        "expect_files": [],
        "verified": "tests added first, change in place, suites and ruff pass, patch exported",
    }


manifest = {
    "run_name": "3a-open-issues-stepD1V",
    "workdir": OUT,
    "max_parallel": 2,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        task(
            "d1v-flags",
            SPEC_EDIT,
            CHECK_EDIT,
            [
                "data/stories/continuity-initiative/knowledge.yaml",
                "bench/frozen/continuity-pre-3a-d1v/",
                "bench/variations/richer-3a-d1-control.json",
                "bench/variations/richer-3a-d1v.json",
                "tests/test_richer_3a.py",
                "tests/test_speaker_lines.py",
            ],
            "medium",
        ),
        task(
            "d1v-decode",
            SPEC_DECODE,
            CHECK_DECODE,
            ["bench/frozen_decode.py", "tests/test_frozen_decode.py"],
            "high",
        ),
    ],
}
Path(__file__).with_name("stepD1V-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("wrote")
