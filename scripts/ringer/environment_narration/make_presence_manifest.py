# ruff: noqa: E501
"""Generate the Ringer manifest for the speaker-presence fix (a recording sentence must not make a speaker present)."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-presence-fix.json"
SRC = "storygame/runtime/cloudflare.py"
TEST = "tests/test_speaker_presence.py"

TABLE = {
    "1A": {"kristin": True, "michelle": True, "patrol_officer": False},
    "1B": {"kristin": True, "brandon": True, "michelle": False},
    "1C": {"kristin": True, "brandon": True, "michelle": False},
    "2A": {"kristin": True, "brandon": True},
    "2B": {"kristin": True, "brandon": False, "michelle": False},
    "2C": {"kristin": True, "brandon": True, "michelle": True, "rebecca": False},
    "3A": {"kristin": True, "michelle": True, "brandon": True, "senior_official": False, "rebecca": False},
    "3B": {"kristin": True, "michelle": True, "brandon": True, "rebecca": False, "charles": False},
    "3C": {"kristin": True, "michelle": True, "rebecca": True, "brandon": False},
}

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. "
    "export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>` (tests that build the provider set CLOUDFLARE_WORKER_URL themselves with monkeypatch). "
    f"YOU MAY EDIT ONLY: {SRC} (only `CloudflareTurnProvider._is_present` and one new private module-level helper next to it) and the NEW file {TEST}. No network, no live model call. Do not git commit. NEVER print or write any credential. "
    "NO NEW regular expressions: you may keep the existing re.* calls (split, search, findall, search) in the presence logic exactly as they are (moving them into the helper is fine) but add no others. No story vocabulary (no Kristin, Michelle, truck, drawer) in non-test code. "
    "Write the tests FIRST, run them, confirm they fail for the right reason, then implement. Run ruff check and ruff format on both files at the end. "
    "PROBLEM. `_is_present(speaker_id)` decides from the authored beat prose whether an NPC is on stage. It splits the prose into sentences, skips any sentence that contains a word from `_ABSENCE_OR_EVIDENCE` (missing, recording, evidence, card, disappeared, ...), and says present when an unskipped sentence matches `<alias> (up to 2 words) <presence action>`. "
    "In scene 1A the sentence 'On the card, Kristin finds a damaged voice recording Michelle attempted to send shortly before she disappeared' is skipped, but the NEXT sentence 'In it, Michelle says government officials have been tracking her ...' has no evidence word of its own and matches 'Michelle says', so the missing Michelle counts as present. The consequence: a missing person is given 'may say this aloud' lines, one of which (the protagonist's own earned event) the narrator then quotes as speech. "
    "FIX (exactly this rule). A sentence is also treated as evidence-bound (skipped) when the sentence IMMEDIATELY BEFORE it (in the same sentence list) mentions an alias of the same speaker AND was skipped for containing a word from `_ABSENCE_OR_EVIDENCE`. The inheritance is NOT transitive: a sentence skipped only by inheritance does not make the following sentence evidence-bound. A predecessor that does not mention the speaker, or that was not skipped, changes nothing. Put the sentence logic into one pure module-level helper (for example `_speaker_present_in_prose(prose: str, aliases: tuple[str, ...]) -> bool`) that `_is_present` calls with the joined beat prose and the entity's name and aliases; keep the protagonist shortcut and the docstring accurate (update it to mention the inheritance rule). "
    "TESTS in the new file (hermetic): (1) the helper on short synthetic prose with made-up names and vocabulary (two different made-up casts): a recording sentence about X followed by 'In it, X says ...' -> False; a plain present sentence 'X says hello to Y.' -> True; predecessor evidence sentence about someone ELSE followed by 'X says hello.' -> True; a predecessor that mentions X but has no evidence word -> unchanged True; non-transitive case: evidence sentence mentioning X, then an inherited-skip sentence mentioning X, then 'X speaks to Y.' -> True. "
    "(2) REAL PACKAGE PIN: load data/stories/continuity-initiative with storygame.story_package.loader.load_story_package, for every scene build `state = RuntimeState.bootstrap(package)`, set `state.current_scene_id` to the scene id, build the provider with `storygame.runtime.capture.build_capture_provider(state)` (monkeypatch CLOUDFLARE_WORKER_URL to https://w.example) and compare `provider._is_present(npc_id)` for every NPC in the scene's participant_ids with this exact expected table, which is the CURRENT behavior except that 1A michelle must become False: "
    + json.dumps({**TABLE, "1A": {**TABLE["1A"], "michelle": False}})
    + " (kristin is the protagonist and is always present). If your rule changes ANY other entry, do not edit the table: narrow the rule until only 1A michelle changes, and if that is impossible stop and report which entries flip and why. "
    "(3) `provider._speaker_contexts('inspect the drawer')` on the 1A bootstrap state has no 'michelle' key. "
    "Finally run these existing suites and report the result: tests/test_cloudflare_transport.py tests/test_knowledge_projection.py tests/test_narration_safety.py tests/test_late_scene_repro.py tests/test_canonical_event_delivery.py tests/test_concealment_repro.py tests/test_3c_adopted_package.py tests/test_bench.py. Existing tests that pin Michelle as a present speaker in scene 1A, if any, may be updated only with a one-line reason in your final report; list each."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov {TEST} tests/test_cloudflare_transport.py tests/test_knowledge_projection.py tests/test_narration_safety.py tests/test_late_scene_repro.py tests/test_canonical_event_delivery.py tests/test_concealment_repro.py tests/test_3c_adopted_package.py tests/test_bench.py tests/test_observation_mode.py tests/test_observation_prompt.py 2>&1 | tee /tmp/presence.out | tail -6 && "
    "! grep -Eq '[0-9]+ (failed|error)' /tmp/presence.out && "
    f"test -s {TEST} && "
    f"test $(git diff -U0 -- {SRC} | grep -E '^\\+' | grep -cE '\\bre\\.[a-z]+\\(') -le 5 && "
    f"! git diff -U0 -- {SRC} | grep -E '^\\+' | grep -iE '(kristin|michelle|truck|drawer|laptop)' && "
    "git diff --stat | tail -3 && "
    f".venv/bin/python -m ruff check {SRC} {TEST} && .venv/bin/python -m ruff format --check {SRC} {TEST}"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-presence-fix",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "speaker-presence-recording-sentence",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 3000,
            "check_timeout_s": 1500,
            "ownership": [SRC, TEST],
            "expect_files": [f"{REPO}/{TEST}"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "a speaker mentioned only through a recording sentence is not present; every other scene and NPC keeps its presence",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
