# ruff: noqa: E501
"""Generate the Ringer manifest: one shared character short name, and mention-only held relations."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-option1.json"
ENV = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    "No network, no model call, no billed request. Do not git commit. NEVER print or write any credential. NO regular expressions in new code. "
    "No story vocabulary (no Kristin, Michelle, truck, laptop, drawer, memory card) in non-test code under storygame/. "
    "Write the tests FIRST, run them, confirm they fail for the right reason, then implement until they pass. Run ruff check and ruff format on the files you edit at the end. "
    "Edit an existing test only when it pins behavior this task legitimately changes, and name each such test in your final message. "
)

SPEC_A = (
    ENV
    + "YOU MAY EDIT ONLY: storygame/runtime/character_names.py (NEW), storygame/runtime/item_facts.py, storygame/runtime/cloudflare.py, storygame/runtime/seating.py, storygame/runtime/taking.py (only if its import must change), tests/test_character_short_name.py (NEW), and existing tests under tests/ that pin the old rule. "
    "PROBLEM. A character's SHORT name (what the story and the narrator call them) is computed as the SHORTEST of the character's name and aliases (`min(..., key=len)`) in four copies: `_protagonist_name` and `_character_label(..., shortest=True)` in storygame/runtime/item_facts.py, `_protagonist_name` in storygame/runtime/seating.py, and `CloudflareTurnProvider._protagonist_name` in storygame/runtime/cloudflare.py. For the shipped story that renders Dr. Michelle McGehee as 'Shelly', a nickname only the protagonist uses, although her FIRST declared alias is 'Michelle'; it renders the patrol officer as 'the officer' instead of 'patrol officer'. Brandon's decision: the short name is the FIRST declared alias, and the character's name only when there are no aliases. (`_character_label` without `shortest` already returns `aliases[0]`; the first alias is the author's declared preferred short form.) "
    "BUILD. (1) New module storygame/runtime/character_names.py with one function `short_name(npc) -> str`: the first alias when the npc has aliases, otherwise `npc.name`. Pure, story-agnostic. (2) Route all four sites through it: `_protagonist_name` in item_facts.py and seating.py and cloudflare.py (keep each function's fallback when there is no npc: item_facts returns None, seating returns the protagonist id, cloudflare returns the protagonist id), and `_character_label(..., shortest=True)` in item_facts.py (keep the `unnamed_label`/`named_by` behavior untouched; the `shortest` parameter keeps its name and meaning 'the short form'). Do NOT leave a second copy of the rule anywhere under storygame/ (grep for `key=len` and `aliases` to confirm). (3) Do not change `aliases[0]` behavior of the non-short path. "
    "TESTS (tests/test_character_short_name.py): short_name with aliases returns the first alias even when a later alias or the name is shorter; with no aliases returns the name; a SYNTHETIC story (different vocabulary) whose second alias is a shorter nickname, checking `ItemFactsProvider._entity_label` and the protagonist name used by the narrator system prompt ('The player is <short>.') and by seating's already-seated line; a character with `unnamed_label` still shows the label before `named_by` is true; the shipped story: the non-protagonist character with a nickname alias renders as her first alias in `_entity_label`, computed in the test from the package's world data (no hardcoded name in storygame/). Then find and update every existing test whose expectation relied on the shortest-alias rule (grep tests/ for 'shortest', 'key=len', 'min(' near aliases, and run the full quick suite to find failures). "
)

SPEC_B = (
    ENV
    + "YOU MAY EDIT ONLY: storygame/runtime/observation_verifier.py, tests/test_observation_verifier.py, tests/test_observation_short_names.py, tests/test_observation_shadow.py, tests/test_observation_preview.py, tests/test_observation_enforcement.py, tests/test_observation_stale_requirement.py, tests/test_observation_resume.py, tests/test_observation_mode.py, tests/test_observation_prompt.py, and the NEW tests/test_observation_held_relations.py. "
    "BACKGROUND. `relations_from_context` in storygame/runtime/observation_verifier.py turns each required thing into a Relation(thing, place, holder) that the Jev verifier checks against the displayed narration. A live probe (150 requests) showed Jev does not read 'held by <character>' reliably: only 12 to 15 of 20 true held relations were accepted (18 needed), concentrated in narrations that say the item is 'in her hand'. All 66 place relations of the earlier sample agreed with the hand labels. Custody is tracked deterministically by the engine, so Brandon decided (option 1): the verifier requires only that a required thing is MENTIONED as present, and its PLACE when it has one; it does not require a holder relation. Brandon also said the wording 'short name, place dropped when it equals the holder' is still valuable, so keep that rendering. "
    "BUILD. (1) In `relations_from_context`, a visible thing that has a holder (its `holder` is not None) yields a MENTION-ONLY relation: Relation(thing=name) with place None and holder None. A visible thing without a holder keeps place (holder stays None). A required name with no matching visible thing stays Relation(thing=name) as today. (2) In `_location_text` (the question text builder), when a relation carries BOTH a place and a holder and they are equal, render only 'held by <holder>' (drop the place). A relation with only a holder, only a place, or two different values renders as today. Keep QUESTION_VERSION unless the question text of any relation that the product now builds changes (a mention-only relation has no location text, as a relation with neither field already renders); if you judge the version must change, change it and say why. (3) Do not touch the criteria wording in `_question_for`. (4) Do NOT drop a relation: a held required item must still be verified as mentioned, so a narration that never mentions it is still rejected. "
    "TESTS (tests/test_observation_held_relations.py plus edits to existing pinned expectations): a) real shipped package via `_state_at` from tests/test_observation_mode.py: the protagonist's held item yields a relation with place None and holder None, and an unheld item on a seat keeps its place; b) a SYNTHETIC second story (different vocabulary, a held item and a seated item): same; c) the Jev question text for a mention-only relation contains no 'held by' and no 'at place'; d) the question for Relation(thing, place=X, holder=X) says 'held by X' and not 'at place'; e) the question for Relation(thing, place=X, holder=Y) still says both, and place-only and holder-only still render as before; f) the shadow record and the enforcement preview with a fake ask: a held item whose narration never mentions it is still rejected (verdict reject via the fake) while the held item mentioned is accepted; the number of relations equals the number of required things. Update existing tests that pinned holder values in relations (for example in tests/test_observation_short_names.py the relation holder expectation) to the new rule and name them. "
)


def check(tests, extra=""):
    return (
        "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
        f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {tests} 2>&1 | tee /tmp/opt1.out | tail -8 && "
        "! grep -Eq '[0-9]+ (failed|error)' /tmp/opt1.out && "
        "env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/quick_suite.py > /tmp/opt1-quick.out 2>&1; grep -E 'passed' /tmp/opt1-quick.out | tail -1; ! grep -Eq '[0-9]+ (failed|error)' /tmp/opt1-quick.out && "
        "! git diff -U0 -- storygame | grep -E '^\\+' | grep -iE '(kristin|michelle|laptop|truck|drawer)|\\bre\\.(compile|search|match|sub|findall|fullmatch)' && "
        + extra
        + ".venv/bin/python -m ruff check . && .venv/bin/python -m ruff format --check ."
    )


def task(key, spec, chk, ownership, expect, verified):
    return {
        "key": key,
        "task_type": "code-fix",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 1800,
        "ownership": ownership,
        "expect_files": expect,
        "spec": spec,
        "check": chk,
        "verified": verified,
    }


manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-option1",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        task(
            "one-short-name-rule",
            SPEC_A,
            check(
                "tests/test_character_short_name.py tests/test_observation_short_names.py tests/test_boarding_already_seated.py tests/test_boarding.py tests/test_seating.py",
                "test -f storygame/runtime/character_names.py && ! grep -rn 'key=len' storygame/runtime/item_facts.py storygame/runtime/seating.py && ! grep -n 'min((\\*' storygame/runtime/cloudflare.py && ",
            ),
            [
                "storygame/runtime/character_names.py",
                "storygame/runtime/item_facts.py",
                "storygame/runtime/cloudflare.py",
                "storygame/runtime/seating.py",
                "tests/test_character_short_name.py",
            ],
            [f"{REPO}/storygame/runtime/character_names.py", f"{REPO}/tests/test_character_short_name.py"],
            "one short-name rule, the first alias, used by the narrator, seating and observation paths",
        ),
        task(
            "mention-only-held-relations",
            SPEC_B,
            check(
                "tests/test_observation_held_relations.py tests/test_observation_verifier.py tests/test_observation_short_names.py tests/test_observation_shadow.py tests/test_observation_preview.py tests/test_observation_enforcement.py tests/test_observation_resume.py tests/test_observation_stale_requirement.py tests/test_holder_wording_probe.py",
            ),
            ["storygame/runtime/observation_verifier.py", "tests/test_observation_held_relations.py"],
            [f"{REPO}/tests/test_observation_held_relations.py"],
            "held required items are verified as mentioned only; equal place and holder render as held by",
        ),
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
