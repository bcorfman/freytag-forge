# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Build the Ringer manifest for round 6f: repair the one ported test that deletes the only producer of a transition trigger."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/story-data-round6f"
OWNED = ["tests/test_audit_budget.py"]

SPEC = (
    "You are a Python test engineer. Your current working directory IS a git worktree of "
    + REPO
    + " (detached at HEAD). Edit files here directly. NEVER git commit, never touch "
    + REPO
    + " itself, never run `uv`, never call a billed model or the network. FIRST run: [ -e .venv ] || ln -s "
    + REPO
    + """/.venv .venv ; run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <files>` (never pass --cov); ruff as `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12).

YOU OWN ONLY tests/test_audit_budget.py. Edit no other file.

PROBLEM. tests/test_audit_budget.py::test_established_knowledge_makes_the_deep_prompt_longer fails. Its helper `_package(..., with_knowledge=False)` builds a mutated copy of the default story's source tree (data/stories/continuity-initiative/source/) by hiding a claim from the player, deleting the fact's `delivery`, emptying scene 1A's match `deliveries`, and setting scene 1A `bridge` to `[]`. Deleting the whole bridge removes the only producer of the scene's transition trigger fact `michelle_lead_actionable`, so the loader now (correctly) rejects the tree with: `scene 1A transition 't_1a_1b' trigger 'michelle_lead_actionable' is not asserted by a bridge event, pacing event or delivery cost`. The compiler used to repair such trees silently; that repair was removed on purpose and must NOT come back.

TASK. Change ONLY the `with_knowledge=False` branch of `_package` (and, if needed, a comment) so the without-knowledge tree still loads and still differs from the with-knowledge tree exactly in that the deep statement is not established knowledge. Keep the producer of `michelle_lead_actionable` (for example keep the bridge event but re-point or reduce what it needs, or move the producer to another source field such as a beat's `sets`; read scenes/1A.yaml `bridge`, `beats` and `exit`, and storygame/story_source/*.py or schema-contract section 4 to see which source fields count as producers and what a bridge requires, e.g. a bridge-required fact needs a FactDelivery). Do not weaken the test assertions: `assert with_knowledge["established_entries"] > without_knowledge["established_entries"]` and `assert with_knowledge["narration_chars"] > without_knowledge["narration_chars"]` stay exactly as they are, and the with-knowledge path (`with_knowledge=True`, `alternate=True`) must behave exactly as today. Do not edit anything under storygame/, data/ or docs/.
"""
)

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs tests/test_audit_budget.py > "$out" 2>&1 || rc=$?
tail -30 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED" "$out"; then echo "a test skips"; exit 1; fi
grep -q 'assert with_knowledge\\["established_entries"\\] > without_knowledge\\["established_entries"\\]' tests/test_audit_budget.py || {{ echo "assertion weakened"; exit 1; }}
grep -q 'assert with_knowledge\\["narration_chars"\\] > without_knowledge\\["narration_chars"\\]' tests/test_audit_budget.py || {{ echo "assertion weakened"; exit 1; }}
.venv/bin/python -m ruff check tests/test_audit_budget.py
.venv/bin/python -m ruff format --check tests/test_audit_budget.py
git add -A -- storygame tests data docs
bad=$(git diff --cached --name-only | grep -v -e '^tests/test_audit_budget.py$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/r6f-audit-budget.patch
test -s {WORK}/r6f-audit-budget.patch
"""


def build() -> dict:
    return {
        "run_name": "story-data-round6-checks",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "r6f-audit-budget",
                "task_type": "code-fix",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 1800,
                "check_timeout_s": 600,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "tests/test_audit_budget.py passes with its two assertions unchanged; only that file changed; ruff clean.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round6f-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
