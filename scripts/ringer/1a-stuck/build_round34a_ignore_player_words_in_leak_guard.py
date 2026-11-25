# ruff: noqa: E501
"""Round 34a: the narration term-leak guard ignores a term the player typed in the same command (owner decision 2026-11-24, R1b-2)."""

import json
from pathlib import Path

WORK = "/home/bcorfman/dev/ringer-work/factory-34a"
REPO = "/home/bcorfman/dev/freytag-forge"
PY = f"{REPO}/.venv/bin/python"
TESTS = (
    "tests/test_narration_safety.py tests/test_leak_terms.py tests/test_leak_terms_enforced.py tests/test_narration_retry.py "
    "tests/test_narration_fixed_thing_terms.py tests/test_scene_2a_grounding.py tests/test_early_1a_photo_sentences.py "
    "tests/test_engine_error_line.py tests/test_copied_files_pilot.py"
)

SPEC = (
    "You are an engineer on freytag-forge. Your current working directory IS a git worktree of the repo (detached at HEAD). Edit files here directly. "
    "NEVER git commit, NEVER call a model, NEVER use the network, never run `uv`. "
    f"Use the interpreter {PY} only (if `.venv` is missing here, run `ln -s {REPO}/.venv .venv` first). Never pass --cov. Write NOTES.txt (never committed) with each ambiguity and your choice. "
    "Read AGENTS.md first, then docs/contributor-guide.md only as needed.\n\n"
    "You may edit ONLY: storygame/runtime/narration_safety.py, tests/test_narration_safety.py, and any of these existing test files but only to update an assertion that pinned the OLD behaviour described below: "
    + TESTS.replace("tests/test_narration_safety.py ", "")
    + ". You may also add ONE sentence to docs/markdown-story-authoring/knowledge-and-disclosure.md where it describes the leak guard (skip it if no such passage exists). Touch nothing else, and do not change any story data.\n\n"
    "DECISION (owner, 2026-11-24). Today the guard in `NarrationSafetyValidator._validate_segments` (storygame/runtime/narration_safety.py, roughly lines 195 to 270) raises `ProposalValidationError(code='narration_known_term_leak', term=...)` when narration names an entity form or known term the player has not earned, even when the player typed that same word in this turn's command ('Look for Michelle's coded note' then narration says 'Michelle' or 'coded note'). Saved evidence shows 43 of 68 recorded term-leak rejections were exactly this case: narration repeating the player's own words, which reveals nothing the player did not already say. The owner decided: ignore the player's own words. "
    "Change both `narration_known_term_leak` raise sites (the unavailable-entity check and the unavailable-knowledge check) so that a form that occurs in the player's own command for this turn (`player_input`, which `_validate_segments` already receives) is skipped. Use the same normalisation and matching helpers the file already uses (`self._normalize`, `self._contains`, `self._contains_optional_plural`) so the match is word-boundary, case-insensitive and tolerates a plural; compute the normalised command once before the segment loop. "
    "Scope it narrowly: it must NOT change any other guard code (`uncited_knowledge`, `protected_narration_leak`, `disclosure_guard_leak`, grounding and speaker checks, `narration_known_term_leak` for a DIFFERENT term that the player did not type), and it must not weaken the protected-term loop (`indexes.protected_terms`). A term typed by the player does not make OTHER unearned terms in the same narration acceptable. If the player's command is empty or whitespace, nothing is skipped.\n\n"
    "TEST FIRST. In tests/test_narration_safety.py (follow the style of the existing term-leak tests there and in tests/test_leak_terms_enforced.py; build state through the existing helpers, do not invent new fixtures if one exists) add a small table-driven test: (1) narration names an unearned entity form that the command contains -> accepted; (2) same for an unearned known term the command contains -> accepted; (3) the plural or possessive form in the command ('Michelle's') still counts; (4) the same narration with a command that does NOT contain the term -> still rejected with narration_known_term_leak and the right `term`; (5) the command contains term A but the narration also names unearned term B -> rejected for B; (6) a protected term or an uncited-knowledge case with the term in the command is still rejected with its own code (pick one real existing protected-term fixture); (7) empty command skips nothing. Write them failing first, then change the code. Keep the new tests parametrized rather than copied; add no more than about 40 lines of tests. "
    "Then run the focused suites listed in the check and update only the assertions that the new behaviour legitimately changes (a test that expected a rejection when the player's own command contained the term); say which in NOTES.txt. If a test expecting a rejection fails for any OTHER reason, stop and describe it in NOTES.txt instead of changing it."
)

CHECK = f"""set -eo pipefail
WORK={WORK}
mkdir -p "$WORK/out"
[ -e .venv ] || ln -s {REPO}/.venv .venv
git reset -q
git add -A -- . ':(exclude)NOTES.txt'
bad=$(git diff --cached --name-only --diff-filter=d | grep -vE '^(storygame/runtime/narration_safety\\.py|tests/test_narration_safety\\.py|tests/test_leak_terms\\.py|tests/test_leak_terms_enforced\\.py|tests/test_narration_retry\\.py|tests/test_narration_fixed_thing_terms\\.py|tests/test_scene_2a_grounding\\.py|tests/test_early_1a_photo_sentences\\.py|tests/test_engine_error_line\\.py|tests/test_copied_files_pilot\\.py|docs/markdown-story-authoring/knowledge-and-disclosure\\.md)$' || true)
[ -z "$bad" ] || {{ echo "files outside ownership staged: $bad"; exit 1; }}
git diff --cached --name-only --diff-filter=d | grep -q '^storygame/runtime/narration_safety\\.py$' || {{ echo "narration_safety.py was not changed"; exit 1; }}
git diff --cached --name-only --diff-filter=d | grep -q '^tests/test_narration_safety\\.py$' || {{ echo "no test added in tests/test_narration_safety.py"; exit 1; }}
start=$(date +%s)
{PY} -m pytest -q -p no:cacheprovider -n 4 {TESTS}
took=$(( $(date +%s) - start ))
echo "focused tests took $took s (budget 300 s)"
[ "$took" -le 300 ] || {{ echo "over the 300 s budget"; exit 1; }}
PYFILES=$(git diff --cached --name-only --diff-filter=d | grep '\\.py$' || true)
{PY} -m ruff check $PYFILES
{PY} -m ruff format --check $PYFILES
git diff --cached > "$WORK/out/r1b2-ignore-player-words.patch"
test -s "$WORK/out/r1b2-ignore-player-words.patch"
"""

manifest = {
    "run_name": "qual-r1b2-ignore-player-words",
    "workdir": WORK,
    "max_parallel": 1,
    "worktrees": True,
    "repo": REPO,
    "tasks": [
        {
            "key": "ignore-player-words",
            "task_type": "code-feature",
            "engine": "codex",
            "engine_args": ["-c", "model_reasoning_effort=high"],
            "max_attempts": 2,
            "timeout_s": 2400,
            "check_timeout_s": 900,
            "ownership": [
                "storygame/runtime/narration_safety.py",
                "tests/test_narration_safety.py",
                "tests/test_leak_terms.py",
                "tests/test_leak_terms_enforced.py",
                "tests/test_narration_retry.py",
                "tests/test_narration_fixed_thing_terms.py",
                "tests/test_scene_2a_grounding.py",
                "tests/test_early_1a_photo_sentences.py",
                "tests/test_engine_error_line.py",
                "tests/test_copied_files_pilot.py",
                "docs/markdown-story-authoring/knowledge-and-disclosure.md",
            ],
            "spec": SPEC,
            "check": CHECK,
            "expect_files": [],
            "verified": "Narration repeating a term the player typed is no longer rejected as a term leak; every other guard is unchanged.",
        }
    ],
}
Path(__file__).with_name("round34a-ignore-player-words-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
