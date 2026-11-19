# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 9b: decouple tests from copied authored prose (one task per test file).

Usage: build_round9b_manifest.py <name> <test_a.py> [<test_b.py> ...]
The per-file hit list comes from round9b-copied.json (made by the orchestrator's read-only audit on 2026-11-19).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
AUDIT = f"{REPO}/scripts/audit_copied_prose.py"
HITS = json.loads(Path(__file__).with_name("round9b-copied.json").read_text(encoding="utf-8"))


def spec(name: str, key: str) -> str:
    test = f"tests/{name}"
    table = "\n".join(f"  {i + 1}. {addr}  ::  {sentence}" for i, (addr, sentence) in enumerate(HITS[name]))
    return f"""You are a Python test engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 {test}` (never pass --cov); ruff as `.venv/bin/python -m ruff check {test}` and `.venv/bin/python -m ruff format {test}` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. {test} copies authored story sentences from the default story (data/stories/continuity-initiative) into its own source. When a writer edits the story, the test then fails on wording rather than on behaviour. The fix is to look the text up by record address instead of copying it. Addresses are the form kind:id.field, for example claim:k_sl_1a_b_r1.text (a claim's delivery text), claim:ID.says (its statement) and beat:ID.say[0] (a pacing beat's first realization). `from storygame.story_source.lookup import story_text` gives `story_text("claim:k_sl_1a_b_r1.text")` -> the passage as a string; pass `package=<StoryPackage>` when the test works on a modified copy of the story, so the lookup reads that copy. `story_text(address)` returns the WHOLE passage, which can have several sentences; the table below lists only the sentences of it that the test copies.

THE COPIES IN {test} (address :: sentence). Find each one (they may sit in a string literal, an f-string, a list, a dict, a comment or a docstring; straight and curly quotes count as the same):
{table}

YOUR JOB: edit ONLY {test} so that none of those sentences appears in it, keeping what each test PROVES unchanged. Pick the case that fits each copy:
- The test checks that the engine's output, a prompt, a record or a state contains or equals the authored text. Replace the literal with a lookup: the whole passage when the literal was the whole passage, or one sentence of the passage when it was one sentence (take it from `re.split(r"(?<=[.!?])\\s+", story_text(address))` by position; if the quotes in the literal differed from the passage, keep the assertion strict on the passage's own characters and say so in your notes).
- NO TAUTOLOGIES. An assertion must never compare a value to the lookup of the same record it was read from (for example `entry.delivery_text == story_text("claim:X.text")` when `entry` is claim X of the same package): that is always true and proves nothing. When the copied text was the EXPECTED value for a record the test also loads, the old test pinned the wording. Then replace the pin with the structural fact the test's name or comments claim (an id, a count, a condition, which fact it sets, a phrase that must appear that you take from a DIFFERENT record such as `must_convey`, or an ordering) as long as that is something the old assertion also proved; if the only thing the old assertion proved was the exact wording, do not fake it with a lookup. Keep the copy in place and put a line starting `RETIRE-CANDIDATE <copy number>:` and one sentence why in NOTES_{key}.txt. Use this sparingly; a lookup is right whenever the other side of the comparison is NOT the same record (engine output, a prompt, a state, a modified copy).
- The test is about a modified story copy (it patches a fact, claim or text). Look the text up in that copy with `package=`, or patch the copy using the text you looked up.
- The sentence is only a fixture payload: an arbitrary string handed to code whose behaviour does not depend on the story (a transport, a formatter, a judge input). Replace it with a short neutral invented sentence that is not story prose and does not name a story character, place or object, and use the same invented string everywhere the old one was used. Choose this only when you can show the test would behave identically for any string.
- A comment or docstring that quotes the sentence: reword it to describe the sentence, with no quotation.
- If a lookup would make a test pass for the wrong reason (for example the assertion becomes true for any text), do not use it; write why in NOTES_{key}.txt (worktree root, never committed) and leave that copy in place.
List every replacement in NOTES_{key}.txt as: copy number, case used, one line why.

RULES. Never split, wrap, join or rebuild a copied sentence from fragments of itself: the audit joins neighbouring string constants, so that does not remove a copy and it is not what is asked. Never mark a test skip or xfail, never delete or rename a test, never loosen or remove an assertion, never add a test, never change what an assertion's expected value means. Do not import anything outside the standard library, pytest, storygame and the helpers the file already uses. Never edit story data under data/. The audit that must end clean is `PYTHONPATH=$PWD .venv/bin/python {AUDIT} --repo $PWD --test {test}`; run it before you finish: it exits 0 with no pair listed when you are done, and exits 1 and lists the sentences still copied otherwise (only copies marked RETIRE-CANDIDATE may remain).

HARD LIMITS. Edit only {test}. Never edit other tests, tests/shard_durations.json, tests/conftest.py, docs/, data/, scripts/ or storygame/. Other tests are being migrated in parallel by other workers.
"""


def check(name: str, key: str, work: str) -> str:
    test = f"tests/{name}"
    stem = Path(name).stem
    head = f"tests/test__head_{stem}.py"
    return f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
hout=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {test} > "$out" 2>&1 || rc=$?
tail -15 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
# baseline: the same file at HEAD, run beside it (a copy named so pytest collects it)
git show HEAD:{test} > {head}
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs {head} > "$hout" 2>&1 || true
rm -f {head}
summ() {{ grep -E "[0-9]+ passed" "$1" | tail -1 | grep -oE "[0-9]+ (passed|skipped|xfailed)" | tr '\\n' ' '; }}
a=$(summ "$out"); b=$(summ "$hout")
echo "after: $a| head: $b"
[ "$a" = "$b" ] || {{ echo "pass/skip counts differ from HEAD"; exit 1; }}
# guard against deleted assertions
cnt() {{ grep -cE "assert |raises\\(" "$1" || true; }}
git show HEAD:{test} > "$hout.py"
[ "$(cnt {test})" -ge "$(cnt "$hout.py")" ] || {{ echo "assertions removed: $(cnt "$hout.py") -> $(cnt {test})"; exit 1; }}
# the audit must be clean for this file, except copies the worker marked RETIRE-CANDIDATE in its notes
left=$(.venv/bin/python {AUDIT} --repo $PWD --test {test} --json | .venv/bin/python -c "import json,sys; print(sum(len(v) for v in json.load(sys.stdin).values()))")
cand=$(grep -c '^RETIRE-CANDIDATE' NOTES_{key}.txt 2>/dev/null || true)
echo "copies left: $left, marked RETIRE-CANDIDATE: $cand"
[ "$left" -le "$cand" ] || {{ .venv/bin/python {AUDIT} --repo $PWD --test {test} || true; echo "copies remain that are not marked RETIRE-CANDIDATE"; exit 1; }}
.venv/bin/python -m ruff check {test}
.venv/bin/python -m ruff format --check {test}
[ -f NOTES_{key}.txt ] && cp NOTES_{key}.txt {work}/ || true
git add -A -- storygame tests data scripts
bad=$(git diff --cached --name-only | grep -v -x -e '{test}' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {work}/{key}.patch
test -s {work}/{key}.patch
"""


def build(label: str, names: list[str]) -> dict:
    work = f"/home/bcorfman/dev/ringer-work/story-data-round9b-{label}"
    tasks = []
    for name in names:
        key = "d-" + Path(name).stem.removeprefix("test_")
        tasks.append(
            {
                "key": key,
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 900,
                "ownership": [f"tests/{name}"],
                "spec": spec(name, key),
                "check": check(name, key, work),
                "expect_files": [],
                "verified": f"tests/{name} copies no authored sentence except ones marked RETIRE-CANDIDATE, has the same passed/skipped counts as at HEAD, no fewer assertions, ruff clean, only that file changed.",
            }
        )
    return {
        "run_name": "story-data-decouple-tests",
        "workdir": work,
        "max_parallel": 6,
        "worktrees": True,
        "repo": REPO,
        "tasks": tasks,
    }


if __name__ == "__main__":
    label, *names = sys.argv[1:]
    out = Path(__file__).with_name(f"round9b-{label}-manifest.json")
    out.write_text(json.dumps(build(label, names), indent=2) + "\n", encoding="utf-8")
    print(out)
