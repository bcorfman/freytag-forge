# ruff: noqa: E501
"""Generate the Ringer manifest: short character names in the observation path, and the probe update."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-short-names.json"
ENV = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no model call, no billed request. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    "No story vocabulary (no Kristin, truck, laptop, drawer, Michelle) in non-test code under storygame/. "
    "Write the tests FIRST, run them, confirm they fail for the right reason, then implement until they pass. Run ruff check and ruff format on the files you edit at the end. "
)

SPEC_A = (
    ENV
    + "YOU MAY EDIT ONLY: storygame/runtime/observation.py, storygame/runtime/item_facts.py (only the observation-context call site and anything strictly needed for it), and these tests: tests/test_observation_context.py, tests/test_observation_prompt.py, tests/test_observation_mode.py, tests/test_observation_shadow.py, tests/test_observation_verifier.py, tests/test_observation_preview.py, tests/test_observation_enforcement.py, tests/test_observation_stale_requirement.py, and the NEW tests/test_observation_short_names.py. Edit an existing test only to change a pinned FULL character name to the short name, and say which in your final message. "
    "PROBLEM. The product renders a character to the narrator by the SHORT name the player knows (the shortest of the character's aliases and name; `ItemFactsProvider._entity_label(world, entity_id)` in item_facts.py does this for characters, honoring `unnamed_label`/`named_by`, and returns `world.name(entity_id)` for non-characters). The observation path built in storygame/runtime/observation.py does not: `_observed` uses `world.name(parent_id)` and `world.name(holder_id)`, and `build_observation_context` uses `world.name(observer_id)` for `observer`. So a held item reaches the narrator prompt (`- <thing>. Held by: <full name>.`), the verifier relation (`Relation(place=<full name>, holder=<full name>)`) and the Jev question with the character's full credited name, while the story text says only the short name. A live sample showed the narration saying 'Kristin' while the relation said 'Kristin Schweitzer', and the verifier rejected true holder relations. Brandon's rule: use the short name for characters everywhere. "
    "BUILD. (1) `build_observation_context` gets an optional keyword `label: Callable[[World, str], str] | None = None`; when None it uses `world.name` (the module stays pure and story-agnostic). `_observed` and the `observer` field use `label` for the placement name (parent/place), the holder, and the observer. Item and container names (thing names, `required`, `omitted_optional`) stay `world.name`, because items resolve by exact name. (2) `ItemFactsProvider._observation_context` passes `label=self._entity_label`. (3) AUDIT the whole observation path for any other place a CHARACTER's full name can reach the narrator prompt, the verifier relations or the Jev question (prompt lines in item_facts.py built from the observation context such as `_observation_thing_line`, `_player_lines`, completed actions, capture.py preview/shadow relation building) and route each through the same label. Do not change the legacy (non-observation) prompt path; it already uses the short label. Report in your final message each site you changed and each site you checked and left alone, with why. "
    "TESTS (new file tests/test_observation_short_names.py): a) real shipped package via the helpers in tests/test_observation_mode.py (`_state_at`): the protagonist's held item has place and holder equal to the protagonist's short name (the shortest of her aliases and name, computed from the package in the test, not hardcoded in storygame/), the narrator prompt contains `Held by: <short>` and never the full credited name for that relation, `relations_from_context` carries the short name, and the Jev question text built by the verifier's `_question_for` for it contains the short name and not the full name. b) a SYNTHETIC second story (different vocabulary) whose protagonist's full name is longer than its alias: same assertions. c) a non-character place (a container or seat) keeps its full declared name. d) a character with `unnamed_label` whose `named_by` fact is not yet true renders the unnamed label. e) default `label=None` behavior of `build_observation_context` is unchanged for a bare World. "
)

SPEC_B = (
    ENV
    + "YOU MAY EDIT ONLY: scripts/ringer/environment_narration/holder_wording_probe.py, scripts/ringer/environment_narration/holder_probe/cases.jsonl, scripts/ringer/environment_narration/holder_probe/cases.lock.json (both regenerated by your script) and tests/test_holder_wording_probe.py. Do NOT run `--run`. "
    "BACKGROUND. This probe (read it and its tests first) compares Jev question wordings for 25 frozen holder cases. A live sample showed the product building holder relations with the character's FULL credited name ('Kristin Schweitzer') while the narration says the SHORT name ('Kristin'). Brandon says the short name is 'definitely most of the issue'. The product is being changed (by another task) to use the short name everywhere, so the probe must now separate the two causes (full name vs doubled place) instead of testing only the doubled place. "
    "CHANGE. (1) Each case keeps `relation` as recorded (full names) and gains `relation_short`: the same relation with every character name replaced by that character's short label. Compute the labels from data/stories/continuity-initiative/world.yaml `npcs` (read with the YAML library already used by the project, no regex): label = the shortest of (*aliases, name) by len, exactly as `ItemFactsProvider._entity_label` does for a character with no `unnamed_label`; map full name to label for every npc. A name that is not an npc's name or alias stays unchanged. Note that a wrong_holder case currently uses 'Michelle McGehee' which is an ALIAS of the npc 'Dr. Michelle McGehee'; map it the same way and report in your final message which label each case ends up with (the shortest alias for that npc may be a nickname; do not special-case it). "
    "(2) Arms become THREE: `full_both` (the case's `relation` exactly as recorded: the 'before'), `short_both` (`relation_short` as is: short names, place and holder both set), `short_held_only` (`relation_short` with place dropped when it equals the holder). Questions still come from the product's `_question_for`. The old two-arm names `current` and `held_only` are gone; update every mention. (3) Planned requests: 25 cases x 3 arms x --samples (default 2) = 150; `--dry-run`, `--max-calls` checks and the USD estimate follow. `--check-corpus` still compares the held_only normalization against the frozen T7 corpus and must still report 0 changed questions across 274 relations (apply it to the corpus relations as before). (4) GATE per short arm (print each separately): G1 at least 18 of the 20 positive_held samples accept; G2 zero accept among the 30 negative samples; G3 positive accepts at least equal to the `full_both` arm's. Also print the `full_both` numbers as the before. The report must state: the 10 positive cases exposed the defect so a pass shows the fix works on known failures, not that it generalizes; and that `short_both` passing means no wording change is needed (the simpler fix). (5) Regenerate cases.jsonl and cases.lock.json with `--build-cases` (rows source is the gitignored local file, as before) and keep the case ids, order and narrations byte-identical to the current file; only the new `relation_short` field is added. Update the tests: short-label mapping from a synthetic world.yaml in tmp_path, three arms, 150 planned requests, interleaving across three arms, gate clauses per short arm, and the lock. "
)


def checks(name, tests):
    return tests


CHECK_A = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov "
    "tests/test_observation_short_names.py tests/test_observation_context.py tests/test_observation_prompt.py tests/test_observation_mode.py tests/test_observation_shadow.py "
    "tests/test_observation_verifier.py tests/test_observation_preview.py tests/test_observation_enforcement.py tests/test_observation_resume.py tests/test_observation_stale_requirement.py "
    "tests/test_runtime_capture.py tests/test_3c_world_capture_wiring.py tests/test_3c_item_facts_capture.py tests/test_environment_baseline.py tests/test_shadow_report.py 2>&1 | tee /tmp/short-a.out | tail -8 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/short-a.out && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/quick_suite.py > /tmp/short-a-quick.out 2>&1; grep -E 'passed' /tmp/short-a-quick.out | tail -1; ! grep -Eq '[0-9]+ (failed|error)' /tmp/short-a-quick.out && "
    "! git diff -U0 -- storygame | grep -E '^\\+' | grep -iE '(kristin|laptop|truck|drawer|michelle)|\\bre\\.(compile|search|match|sub|findall|fullmatch)' && "
    ".venv/bin/python -m ruff check storygame tests/test_observation_short_names.py && .venv/bin/python -m ruff format --check storygame tests/test_observation_short_names.py"
)

CHECK_B = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov tests/test_holder_wording_probe.py 2>&1 | tee /tmp/short-b.out | tail -5 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/short-b.out && "
    "P=scripts/ringer/environment_narration/holder_wording_probe.py && "
    ".venv/bin/python $P --check-corpus | tee /tmp/short-b-corpus.out && grep -q 'changed questions: 0' /tmp/short-b-corpus.out && "
    ".venv/bin/python $P --dry-run | grep -q 'planned requests: 150' && "
    'test "$(wc -l < scripts/ringer/environment_narration/holder_probe/cases.jsonl)" = 25 && '
    "grep -q 'relation_short' scripts/ringer/environment_narration/holder_probe/cases.jsonl && "
    "git show HEAD:scripts/ringer/environment_narration/holder_probe/cases.jsonl | .venv/bin/python -c \"import sys,json; old=[json.loads(l) for l in sys.stdin]; new=[json.loads(l) for l in open('scripts/ringer/environment_narration/holder_probe/cases.jsonl')]; assert [c['id'] for c in old]==[c['id'] for c in new]; assert all(o['narration']==n['narration'] and o['relation']==n['relation'] for o,n in zip(old,new)); print('cases preserved')\" && "
    ".venv/bin/python -m ruff check scripts/ringer/environment_narration/holder_wording_probe.py tests/test_holder_wording_probe.py && "
    ".venv/bin/python -m ruff format --check scripts/ringer/environment_narration/holder_wording_probe.py tests/test_holder_wording_probe.py"
)


def task(key, spec, check, ownership, expect, verified, timeout_check):
    return {
        "key": key,
        "task_type": "code-fix",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": timeout_check,
        "ownership": ownership,
        "expect_files": expect,
        "spec": spec,
        "check": check,
        "verified": verified,
    }


manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-short-names",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        task(
            "short-names-in-observation-path",
            SPEC_A,
            CHECK_A,
            [
                "storygame/runtime/observation.py",
                "storygame/runtime/item_facts.py",
                "tests/test_observation_short_names.py",
            ],
            [f"{REPO}/tests/test_observation_short_names.py"],
            "characters appear by their short name in the observation prompt, relations and Jev question",
            1800,
        ),
        task(
            "holder-probe-short-name-arms",
            SPEC_B,
            CHECK_B,
            [
                "scripts/ringer/environment_narration/holder_wording_probe.py",
                "scripts/ringer/environment_narration/holder_probe/cases.jsonl",
                "scripts/ringer/environment_narration/holder_probe/cases.lock.json",
                "tests/test_holder_wording_probe.py",
            ],
            [f"{REPO}/scripts/ringer/environment_narration/holder_probe/cases.jsonl"],
            "three-arm holder probe with short-name relations, offline only",
            600,
        ),
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
