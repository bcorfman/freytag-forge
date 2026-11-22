# ruff: noqa: E501  (spec strings are prose briefs for a worker)
"""Round 18a: a free gap rule that finds twin reveals (identical earn_when, both eligible at once). FREE: no model call.

Why: round 15d replicate 0 lost four commands to two reveals (k_sl_1a_b_r0 and k_sl_1a_b_r0w) that share one earn_when
sentence and could both be eligible. The semantic matcher answers yes to both, and the engine refuses when more than one
matches. Triage cannot see this, and nothing static caught it. The factory's gap-delta gate (station 5) runs every rule in
RULES, so a new rule makes the gate fail any change that adds a twin. One Codex task. Usage: build_round18a_twin_reveals_manifest.py
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
WORK = "/home/bcorfman/dev/ringer-work/twin-reveals-rule"

OWNED = ["storygame/story_package/gap_rules.py", "tests/test_gap_rules.py"]

SPEC = """You are a Python engineer. Your current working directory IS a git worktree of @REPO@ (detached at HEAD). Edit files here directly. NEVER git commit, never touch @REPO@ itself, never run `uv`, NEVER call a model, NEVER use the network, NEVER run npm, playwright or the bench. FIRST run: [ -e .venv ] || ln -s @REPO@/.venv .venv . Environment for every command: `export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp`. Ruff: `.venv/bin/python -m ruff check <files>` and `.venv/bin/python -m ruff format <files>` (line length 120, Python 3.12). Never pass --cov to pytest. Run tests as `.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_gap_rules.py tests/test_factory_gap_delta.py`.

BACKGROUND. `storygame/story_package/gap_rules.py` holds deterministic, read-only story gap rules (`RULES`, `run_gap_rules`, `RuleResult`; read the whole file and `tests/test_gap_rules.py` first, especially `_no_producer_results` and the seeded-defect-and-clean-variant tests). The factory's station 5 gap-delta gate (`factory/checks/gap_delta.py`) runs every rule in `RULES` for every anchor and fails a change that adds a rule result, so a new rule becomes a free gate automatically. Do not edit `factory/`.

THE DEFECT CLASS. In live play the engine asks a semantic matcher whether the player's command performs each eligible reveal's `earn_when` sentence (`KnowledgeDefinition.earn_when` in `storygame/story_package/models.py`). If the matcher says yes to MORE THAN ONE reveal the engine refuses the command (`_semantic_authored_handoff` in `storygame/runtime/cloudflare.py`: `if len(matched) != 1`). Two reveals with the same `earn_when` sentence are matched together whenever both are eligible at the same time, so the player's correct command is refused. In scene 1A two reveals, `k_sl_1a_b_r0` (requires `patrol_in_house` false) and `k_sl_1a_b_r0w` (requires it true), share one sentence. That is safe ONLY because their `requires` can never both hold: the fact store now keeps one value of a boolean fact (asserting "true" retracts "false" and the reverse; see `FactStore.assert_fact` in `storygame/runtime/facts.py`). Delete either `when` and the pair becomes a twin that the engine refuses.

BUILD a new rule `twin_reveals` in `gap_rules.py`, registered in `RULES`. Story-agnostic: the module must contain no story-specific words (a test, `test_module_has_no_story_specific_words`, enforces it). Scope: reveals that are available in the scene(s) the anchor's exits leave (`exit_transitions` gives them; use each exit's source scene); when the anchor has no exit (a pacing event or incident), use that record's own scene. Consider every `KnowledgeDefinition` in the package whose `earn_when` is a non-blank string and whose `available_in_scenes` includes a scoped scene. Two such reveals are TWINS when (1) their `earn_when` sentences are equal after casefolding, trimming and collapsing runs of whitespace, AND (2) their `requires` predicates do NOT contradict each other, where "contradict" means: some `fact_id` appears in one reveal's `requires` with `equals` True and in the other's with `equals` False (or the reverse; compare boolean values, treat string "true"/"false" the same way the package does). A pair with no contradiction can be eligible together, so report it. Report each pair once, in a stable order. Result shape: `RuleResult(rule="twin_reveals", anchor=anchor, subject="<id_a>,<id_b>" (sorted), summary="<id_a> and <id_b> share the earn_when sentence and can be eligible together, so the matcher can match both and the engine refuses the command.", evidence=(...))`, where evidence quotes the shared sentence and cites each reveal's source location with the existing `_located` helper (and the `requires` of each). Keep it to the smallest correct code, reusing helpers already in the file.

TESTS in `tests/test_gap_rules.py` (extend the file; no new test file; follow the seeded-defect-and-clean-variant style using `compiled_story_copy` and `_edit_source`): (a) the real package gives NO `twin_reveals` result for every transition id and every pacing event id (use the existing helpers that enumerate anchors, or build the list from `load_story_package`); (b) a seeded defect: in a copy of the story remove the `when` of the two card-recovery variants of reveal `sl_1a_e` in `source/scenes/1A.yaml` (variants `r1` and `r2`, claim ids `k_sl_1a_b_r0` and `k_sl_1a_b_r0w`, found with the file's `_claim` helper) so they no longer contradict, then `run_gap_rules(root, "t_1a_1b", ["twin_reveals"])` returns exactly one result naming both ids; (c) the clean variant: removing only ONE of the two `when`s still gives no result only if the remaining requires still contradict, so instead assert that restoring the original data gives none; (d) two reveals with different `earn_when` sentences and no contradiction give no result (edit one sentence in the seeded copy); (e) the rule is registered and `render_rule_results` renders it; (f) the new tests keep the whole file under 20 seconds (it ran in about 7 seconds with its sibling before you started). If the seeded copy fails to load for an unrelated reason, report it in the notes and choose another seeding.

HARD LIMITS. Edit only the two files above. Do not edit story data, `factory/`, `scripts/`, `storygame/runtime/` or any other test. If an existing test fails because of the new rule, STOP and describe it in the notes. Write NOTES_18A.txt (worktree root, never committed) listing every ambiguity and your choice."""

CHECK = """set -eo pipefail
WORK=@WORK@
mkdir -p "$WORK/out"
export PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp
[ -e .venv ] || ln -s @REPO@/.venv .venv
git add -A -- storygame tests
bad=$(git diff --cached --name-only | grep -vxF -e storygame/story_package/gap_rules.py -e tests/test_gap_rules.py || true)
[ -z "$bad" ] || { echo "files outside ownership staged: $bad"; exit 1; }
probe="$WORK/out/probe.out"
.venv/bin/python - > "$probe" 2>&1 <<'PY' || true
import tempfile
from pathlib import Path

import yaml

from storygame.story_package.gap_rules import RULES, run_gap_rules
from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import compiled_story_copy

assert "twin_reveals" in RULES, "rule not registered"
real = Path("data/stories/continuity-initiative")
pkg = load_story_package(real)
anchors = [t.id for t in pkg.pacing.transitions] + [e.id for e in pkg.pacing.events]
for anchor in anchors:
    found = run_gap_rules(real, anchor, ["twin_reveals"])
    assert not found, (anchor, found)
with tempfile.TemporaryDirectory() as tmp:
    root = compiled_story_copy(Path(tmp))
    path = root / "source" / "scenes" / "1A.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for reveal in data["reveals"]:
        for variant in reveal["variants"].values():
            if variant.get("claim_id") in ("k_sl_1a_b_r0", "k_sl_1a_b_r0w"):
                variant.pop("when", None)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    found = run_gap_rules(root, "t_1a_1b", ["twin_reveals"])
    assert len(found) == 1 and "k_sl_1a_b_r0" in found[0].subject and "k_sl_1a_b_r0w" in found[0].subject, found
print("probe ok")
PY
cat "$probe"
grep -q "probe ok" "$probe" || { echo "probe failed (fails before the rule exists, on purpose)"; exit 1; }
start=$(date +%s)
.venv/bin/python -m pytest -q -p no:cacheprovider -n 8 tests/test_gap_rules.py tests/test_factory_gap_delta.py tests/test_factory_stations.py tests/test_factory_checks.py
took=$(( $(date +%s) - start ))
echo "gap and station tests took $took s (baseline 8 s, budget 60 s)"
[ "$took" -le 60 ] || { echo "over the 60 s budget"; exit 1; }
start=$(date +%s)
.venv/bin/python scripts/quick_suite.py --also tests/test_gap_rules.py
took=$(( $(date +%s) - start ))
echo "quick suite took $took s (baseline 157 s, budget 450 s)"
[ "$took" -le 450 ] || { echo "quick suite over the 450 s budget"; exit 1; }
.venv/bin/python -m ruff check storygame/story_package/gap_rules.py tests/test_gap_rules.py
.venv/bin/python -m ruff format --check storygame/story_package/gap_rules.py tests/test_gap_rules.py
git diff --cached > "$WORK/out/twin-reveals.patch"
test -s "$WORK/out/twin-reveals.patch"
"""


def build() -> dict:
    def fill(text: str) -> str:
        return text.replace("@REPO@", REPO).replace("@WORK@", WORK)

    return {
        "run_name": "twin-reveals-rule",
        "workdir": WORK,
        "max_parallel": 1,
        "worktrees": True,
        "repo": REPO,
        "tasks": [
            {
                "key": "twin-reveals",
                "task_type": "code-feature",
                "engine": "codex",
                "engine_args": ["-c", "model_reasoning_effort=high"],
                "max_attempts": 2,
                "timeout_s": 2400,
                "check_timeout_s": 900,
                "ownership": OWNED,
                "spec": fill(SPEC),
                "check": fill(CHECK),
                "expect_files": [],
                "verified": "A twin_reveals gap rule is registered; the real story has no result for any transition or pacing-event anchor; a seeded twin pair in 1A gives exactly one result; module stays story-agnostic; quick suite green under 450 s; ruff clean; two files changed.",
            }
        ],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("round18a-twin-reveals-manifest.json")
    out.write_text(json.dumps(build(), indent=2) + "\n")
    print(out)
