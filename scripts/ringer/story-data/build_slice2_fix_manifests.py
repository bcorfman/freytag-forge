"""Build the Ringer manifests for slice 2 fixes: worldkeeper helpers, then gap_rules citations."""

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
MODEL = f"{REPO}/packages/worldkeeper/src/worldkeeper/model.py"
WTEST = f"{REPO}/packages/worldkeeper/tests/test_coherence_helpers.py"
MOD = f"{REPO}/storygame/story_package/gap_rules.py"
TEST = f"{REPO}/tests/test_gap_rules.py"
SCRIPT = f"{REPO}/scripts/gap_rules.py"
ENV = f"export TMPDIR=/tmp PYTHONPATH={REPO}:{REPO}/packages/worldkeeper/src"
PY = f"{REPO}/.venv/bin/python"
RUN = "story-data-gap-rules"
WORKDIR = "/home/bcorfman/dev/ringer-work/story-data-gap-rules"

WSPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python. You own ONLY {MODEL} (edit: add two methods to class World) and {WTEST} (create). Touch nothing else.

Add these world-state-only methods to class World in {MODEL}, directly after the existing `together` method (read `area`, `holder`, `holds` and `together` first and follow their style: short, no new dependencies):

    def characters_together(self, entity_id):
        \"\"\"Return the sorted ids of other characters in the same or nested areas as an entity.\"\"\"
  Every entity id from self.entity_ids() that is not entity_id, for which self.is_a(candidate, "character") and self.together(entity_id, candidate) are true, sorted by id, as a tuple.

    def apart(self, first_id, second_id):
        \"\"\"Return whether both entities are placed in areas and are not together.\"\"\"
  True exactly when self.area(first_id) is not None and self.area(second_id) is not None and not self.together(first_id, second_id).

TESTS in {WTEST} (pytest, compact, module-level functions; copy the WorldSchema.from_data / World(schema, MemoryBackend()) / world.seed() / world.move(...) setup style from {REPO}/packages/worldkeeper/tests/test_holds.py). Cover: characters_together returns sorted other characters in the same area and in a nested area, excludes the entity itself, excludes a character in a separate area and an unplaced one, and returns () when alone; apart is True for two placed entities in separate areas, False in the same area, False in nested areas, False when either is unplaced, and True for an item in another area than a character.

HOW TO RUN (from {REPO}; never --cov): `{ENV} && {PY} -m pytest {WTEST} {REPO}/packages/worldkeeper/tests -q --no-cov -p no:cacheprovider 2>&1 | tail -15`. Format and lint: `{PY} -m ruff format {MODEL} {WTEST} && {PY} -m ruff check {MODEL} {WTEST}`."""

WCHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {MODEL} {WTEST}
$PY -m ruff format --check {MODEL} {WTEST}
grep -n "def characters_together\\|def apart" {MODEL}
$PY -m pytest {WTEST} {REPO}/packages/worldkeeper/tests -q --no-cov -p no:cacheprovider 2>&1 | tail -6
"""

GSPEC = f"""You are an implementation worker for the freytag-forge repository at {REPO}. Boundary: NO model call, NO network call, never git commit, never uv or bare python. You own ONLY {MOD} and {TEST} (both exist; edit them). Do not touch {SCRIPT}, worldkeeper, story data, or any other file.

CONTEXT. {MOD} is a story-agnostic registry of Layer 3 gap rules (custody, co_location, no_strand) that prints evidence lines ending with a source location 'file.yaml:LINE'. Run `{ENV} && {PY} {SCRIPT} officer_presses_1a` to see it. A review found these defects; fix them.

FIX 1, citations. _source_location currently falls back to ANY line containing the id as a token, so descriptive evidence cites unrelated lines (for example 'protagonist in kitchen' cites a fact's purpose line that mentions kitchen; 'holder at baseline' cites a claim record that merely names the item). Rule: a location may be cited only for a line that DEFINES the named record: a YAML list or flow entry whose key is `id` with that value (`- id: X`, `{{id: X, ...}}`), or a mapping key line equal to the id (`X:` alone on its line, as in fact_effects). Remove the loose token fallback. When no defining line exists, the evidence line carries NO location. Look at how each _located call picks its record id and fix call sites so a location is attached only when the evidence line is genuinely about that record: a claim line cites the claim; a transition line cites the transition; an entity (item, area) cites its definition line in world.yaml if there is one; a line about a fact cites the fact's definition in knowledge.yaml only when the line states that fact's own definition or purpose, otherwise none. The line 'holder at baseline: X; after the hypothetical move: Y; engine verdict: eligible' is computed from a simulation, not quoted from a file: give it NO location. Never invent a location.

FIX 2, no_strand evidence wording. When an authored world effect that moves the item to the protagonist belongs to a fact that is already true at baseline, say so in its evidence line: 'Authored effect for <fact> moves <item> to <character>; <fact> is already true, so it cannot fire again.' When it is not yet true, keep the current wording. Behaviour (when to flag) must not change.

FIX 3, use the new worldkeeper helpers (already added to class World in {REPO}/packages/worldkeeper/src/worldkeeper/model.py): replace _other_character's loop by the first of world.characters_together(protagonist_id) (None if empty), and the co_location 'away from it' test by world.apart(protagonist, item_id). The flags produced for the Reyes anchor must not change except for evidence lines fixed by 1 and 2.

TESTS in {TEST}: keep all existing tests passing. Add: (a) for the anchor officer_presses_1a, every cited 'file:LINE' in rendered output points at a line that defines a record (the line matches `id:` followed by an id, or a bare `key:` line); read the cited file and line in the test; (b) no evidence line for the baseline-holder simulation carries a location; (c) the no_strand evidence says the effect is already true and cannot fire again for the Reyes data. Keep the HARD RULE: the module contains no story names (memory_card, kristin, patrol, laptop, k_sl_, t_1a, continuity), not even in comments.

HOW TO RUN (from {REPO}; never --cov): `{ENV} && {PY} -m pytest {TEST} {REPO}/tests/test_situation_trace.py -q --no-cov -p no:cacheprovider 2>&1 | tail -20`. Format and lint: `{PY} -m ruff format {MOD} {TEST} && {PY} -m ruff check {MOD} {TEST}`."""

GCHECK = f"""set -o pipefail
cd {REPO}
{ENV}
PY={PY}
$PY -m ruff check {MOD} {TEST}
$PY -m ruff format --check {MOD} {TEST}
if grep -n -i -E 'memory_card|kristin|patrol|laptop|k_sl_|t_1a|continuity' {MOD}; then echo 'STORY NAMES FOUND'; exit 1; fi
$PY -m pytest {TEST} {REPO}/tests/test_situation_trace.py -q --no-cov -p no:cacheprovider 2>&1 | tail -15
$PY {SCRIPT} officer_presses_1a > /tmp/gap-rules-reyes2.md
cat /tmp/gap-rules-reyes2.md | head -50
$PY - <<'PY'
import re, sys
root = "{REPO}/data/stories/continuity-initiative/"
bad = []
for line in open("/tmp/gap-rules-reyes2.md"):
    m = re.search(r"(\\S+\\.(?:yaml|md)):(\\d+)\\s*$", line)
    if not m:
        continue
    src = open(root + m.group(1)).read().splitlines()[int(m.group(2)) - 1]
    if not (re.search(r"\\bid:\\s*\\S", src) or re.match(r"^\\s*[A-Za-z0-9_]+:\\s*$", src)):
        bad.append(f"{{m.group(1)}}:{{m.group(2)}} is not a defining line: {{src.strip()[:80]}}")
if bad:
    print("CITATION CHECK FAILED"); [print(" -", b) for b in bad]; sys.exit(1)
print("CITATION CHECK OK")
PY
grep -q '^### custody' /tmp/gap-rules-reyes2.md && grep -q '^### co_location' /tmp/gap-rules-reyes2.md && grep -q '^### no_strand' /tmp/gap-rules-reyes2.md
"""


def task(key, spec, check, own, expect, verified, effort):
    return {
        "key": key,
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", f"model_reasoning_effort={effort}"],
        "max_attempts": 2,
        "timeout_s": 1800,
        "check_timeout_s": 900,
        "ownership": own,
        "expect_files": expect,
        "spec": spec,
        "check": check,
        "verified": verified,
    }


def write(name, t):
    manifest = {
        "run_name": RUN,
        "workdir": WORKDIR,
        "max_parallel": 1,
        "worktrees": False,
        "repo": REPO,
        "tasks": [t],
    }
    out = Path(__file__).with_name(name)
    out.write_text(json.dumps(manifest, indent=2) + "\n")
    print(out)


write(
    "slice2-world-helpers-manifest.json",
    task(
        "world-coherence-helpers",
        WSPEC,
        WCHECK,
        [MODEL, WTEST],
        [WTEST],
        "World.characters_together and World.apart exist, their tests pass, and all worldkeeper tests still pass",
        "medium",
    ),
)
write(
    "slice2-gap-rules-citations-manifest.json",
    task(
        "gap-rules-citations",
        GSPEC,
        GCHECK,
        [MOD, TEST],
        [MOD, TEST],
        "every file:line the gap rules cite is a line that defines the record, all three Reyes flags remain, and no story names are in the module",
        "high",
    ),
)
