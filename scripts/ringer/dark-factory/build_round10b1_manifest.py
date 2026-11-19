# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 10b-1: Worldkeeper answers "can the world model represent this need?" (factory step 4, station 2, question 1).

Usage: build_round10b1_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/factory-world-need-1"

OWNED = [
    "packages/worldkeeper/src/worldkeeper/model.py",
    "packages/worldkeeper/tests/test_can_represent.py",
]

SPEC = f"""You are a Python engineer. Your current working directory IS a git worktree of {REPO} (detached at HEAD). Edit files here directly. NEVER git commit, never touch {REPO} itself, never run `uv`, never call a model or the network. FIRST run: [ -e .venv ] || ln -s {REPO}/.venv .venv . Run tests as `PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 packages/worldkeeper/tests/test_can_represent.py packages/worldkeeper/tests/test_world.py` (never pass --cov). Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, double quotes, Python 3.12, no new dependencies).

BACKGROUND. The story factory asks, before any prose is written for a scene, whether the world model can represent each piece of state the scene depends on. That question reads only the world schema, so it is world-model logic and belongs in the Worldkeeper package (a project rule: world-state-only logic is a method in packages/worldkeeper with its tests there). Read `packages/worldkeeper/src/worldkeeper/model.py` (`BASE_KINDS`, `_ancestors`, `WorldSchema`, `OpResult`) and `packages/worldkeeper/tests/test_world.py` (the `make()` helper builds a small schema) before you start.

YOUR JOB. Add ONE method to `WorldSchema` in model.py (a pure read of `self.kinds` and `self.kind_enterable`; no new state, no new module, no change to any other method):

    def can_represent(self, relation: str, subject_kind: str, object_kind: str | None = None) -> OpResult:
        \"\"\"Return whether the schema can represent a relation between entities of the given kinds.\"\"\"

It returns `OpResult(True)` when representable, otherwise `OpResult(False, reason)` where the reason is a short plain sentence naming the kind or relation at fault. Rules (use `self.kind_is(kind, ancestor)`; kinds come from the schema, so story-declared kinds work):
- An unknown `relation`: not representable, reason "unknown relation <relation>".
- An unknown `subject_kind`, or an `object_kind` that is given but unknown: not representable, reason "unknown kind <kind>". Check this before the relation rules.
- "exist": the subject kind is known. `object_kind` is ignored.
- "hold": subject is a thing and object is a character (a character holds an item). If object_kind is None: not representable, reason "hold needs an object kind".
- "reach": subject is a character, object is an area. object_kind required.
- "hidden": subject is a thing, object is a thing (the hider, such as a container, supporter or furniture). object_kind required.
- "seated": subject is a character, object is a container or a supporter (these are the kinds that can be entered; a kind with `kind_enterable[kind]` true also counts). object_kind required.
- "companion": subject and object are both characters. object_kind required.
- "axis": the subject kind is known (any entity can carry a state axis). `object_kind` ignored.
- "know": subject is a character. `object_kind` is ignored (the thing known is a story fact, which is not the world model's concern).
When a rule needs an object_kind and it is missing, the reason is "<relation> needs an object kind".

TESTS: create `packages/worldkeeper/tests/test_can_represent.py`. Build schemas with `WorldSchema.from_data` (look at how test_world.py does it; include one story-declared kind, for example a kind `phone` that is a `thing`, and a kind `guard` that is a `character`). Cover: every relation with one representable pair and at least one non-representable pair (for example hold with a character as subject, reach with a thing as object, seated with a character as object, companion with a thing), an unknown relation, an unknown subject kind, an unknown object kind, a missing object kind for each relation that needs one, a story-declared kind behaving like its parent, an enterable story kind (declared with `enterable: true` under container) counting for seated, and that calling can_represent does not mutate the schema (compare `schema.kinds` and `schema.entities` before and after). Tests assert on `.ok` and check the reason text contains the kind or relation name.

HARD LIMITS. Edit only the two files above, and in model.py only add the one method (no other line changes except ones ruff format requires inside the method). Never edit files under storygame/, factory/, tests/ or docs/. Write a short NOTES_10b1.txt (worktree root, never committed) for any rule you found ambiguous and the choice you made.
"""

CHECK = f"""set -eo pipefail
[ -e .venv ] || ln -s {REPO}/.venv .venv
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
out=$(mktemp)
rc=0
.venv/bin/python -m pytest -q -p no:cacheprovider -n 0 -rs packages/worldkeeper/tests > "$out" 2>&1 || rc=$?
tail -6 "$out"
[ "$rc" -eq 0 ] || exit "$rc"
if grep -E "SKIPPED|XFAIL|xfailed" "$out"; then echo "a test skips or xfails"; exit 1; fi
grep -q "def can_represent" packages/worldkeeper/src/worldkeeper/model.py || {{ echo "can_represent missing"; exit 1; }}
test "$(grep -c 'def can_represent' packages/worldkeeper/src/worldkeeper/model.py)" -eq 1 || {{ echo "exactly one can_represent"; exit 1; }}
# model.py changed only by additions inside the one method: no removed lines
removed=$(git diff -U0 -- packages/worldkeeper/src/worldkeeper/model.py | grep -E '^-[^-]' || true)
[ -z "$removed" ] || {{ echo "model.py lines were removed or changed:"; echo "$removed"; exit 1; }}
.venv/bin/python - <<'PY'
from worldkeeper.model import WorldSchema
s = WorldSchema.from_data({{"kinds": [{{"id": "phone", "is": ["thing"]}}, {{"id": "guard", "is": ["character"]}}]}})
assert s.can_represent("hold", "phone", "guard").ok
assert not s.can_represent("hold", "guard", "guard").ok
assert s.can_represent("seated", "guard", "vehicle").ok
assert not s.can_represent("seated", "guard", "guard").ok
assert not s.can_represent("bogus", "phone").ok
assert not s.can_represent("exist", "nokind").ok
print("independent probe ok")
PY
.venv/bin/python -m ruff check packages/worldkeeper
.venv/bin/python -m ruff format --check packages/worldkeeper
git add -A -- packages
bad=$(git diff --cached --name-only | grep -v -x -e packages/worldkeeper/src/worldkeeper/model.py -e packages/worldkeeper/tests/test_can_represent.py || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached > {WORK}/can_represent.patch
test -s {WORK}/can_represent.patch
"""


def build() -> dict:
    return {
        "run_name": "factory-world-need",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "can-represent",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=medium"],
                "max_attempts": 2,
                "timeout_s": 1800,
                "check_timeout_s": 300,
                "ownership": OWNED,
                "spec": SPEC,
                "check": CHECK,
                "expect_files": [],
                "verified": "WorldSchema.can_represent exists once, additions only, worldkeeper suite green, an independent probe agrees, ruff clean, only two files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round10b1-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(out)
