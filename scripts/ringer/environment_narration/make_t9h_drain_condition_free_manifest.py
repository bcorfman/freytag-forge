# ruff: noqa: E501
"""Write the Ringer manifest for steps 0 and 1 of the drain condition experiment (free)."""

import json
from pathlib import Path

ROOT = "/home/bcorfman/dev/freytag-forge"
PY = f"{ROOT}/.venv/bin/python"
ED = "scripts/ringer/environment_narration"
CHECK = f"{ROOT}/{ED}/check_t9h_drain_condition_free.sh"
OUT = "bench/results/environment-narration/t9h-drain-condition"
DESIGN = f"{ROOT}/.plans/grounded-llm-environment-narration/t9h-drain-condition-experiment-design.md"

COMMON = (
    f"Working directory: {ROOT} (Python 3.12). Run Python as `{PY}` only (never uv). Run tests with: `export "
    f"PYTHONPATH={ROOT} TMPDIR=/tmp; env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN {PY} -m pytest -q "
    "-p no:cacheprovider --no-cov <files>`. FREE WORK ONLY: no network, no model call, no Worker, no credentials, never "
    "read or print .env. Do not git commit. NO regular expressions in new code and never parse narration text to decide "
    "anything (the corpus is for a human or a model to read; the only deterministic check is on typed fields). Match the "
    "surrounding code's style. The working tree holds unrelated uncommitted edits: touch ONLY the files you own, never run "
    "git checkout, stash, reset or clean, and never modify anything under bench/results/ (read it; write only to the "
    "--out directory a mode is given). At the end run ruff check --fix and ruff format on the .py files you own. "
    f"Read first (read-only): {DESIGN}, sections 1, 3 and 4. Do not edit the check script. Where a needed field is not "
    "recorded, say so in your final summary instead of inventing it."
)

TASKS = [
    {
        "key": "step0-corpus",
        "check": "corpus",
        "owns": [f"{ED}/drain_condition_corpus.py", "tests/test_drain_condition_corpus.py"],
        "brief": (
            "Build `drain_condition_corpus.py`, the Step 0 tool that assembles ONE corpus of recorded drain narrations "
            "(inspecting the storm drain) for later labeling, plus a blind adjudication sheet. Modes: `--build --out DIR` "
            "writes DIR/corpus.json {schema, built_from: [...paths], rows: [...]}; `--blind-sheet --corpus FILE --out DIR` "
            "writes DIR/blind_sheet.md and DIR/blind_key.json (opaque ids `row-001`.. in a fixed-seed shuffle; the sheet "
            "shows ONLY the narration text and nothing else: no arm, source, run name, attempt number, outcome, score, "
            "provisional label or file path, and the sheet title and prose must not mention any of those words) and "
            "DIR/labels_template.json (null labels per opaque id with the six names opens_or_enters_drain, "
            "invents_ajar_or_cover_state, asserts_definite_contents, speculative_only, wrong_place, "
            "capture_prose_disagree); `--freeze-labels --labels FILE` writes labels.freeze.json beside it with the file's "
            "SHA-256, refusing if any label is null or a freeze with a different hash exists; `--join --corpus FILE "
            "--labels FILE --key FILE --out FILE` (requires a matching freeze) writes the adjudicated corpus with each "
            "row's final label and a disagreement list against the provisional label.\n"
            "ROWS, each {id, source_file (repo-relative), source_ref (replicate/turn/attempt or sample/row), run, arm "
            "(control, candidate, or null), narration (the player-visible text: for the drain-details runs the joined "
            "`segments[].text` of the JSON `response_text`; for engine runs the attempt's `narration` string), "
            "item_facts_raw (the parsed item_facts object when the reply JSON is available, else null), "
            "provisional_label ({opens_or_enters_drain, invents_ajar_or_cover_state, asserts_definite_contents, "
            "speculative_only, wrong_place, capture_prose_disagree, forbidden} or null), label_source}. SOURCES: (1) the "
            "49 rows of bench/results/environment-narration/t9h-drain-details/screen and /confirm: rows.json plus "
            "sheet.md/blind_key.json + sheet.md/labels.json for the screen, and sheet/blind_key.json + sheet/labels.json "
            "for the confirmation (labels are keyed by opaque sample id; the key maps it to a row_index into rows.json); "
            "`forbidden` is true when opens_or_enters_drain, invents_ajar_or_cover_state or asserts_definite_contents is "
            "true; label_source `claude-blind-provisional`. Exactly 49 labeled rows, 18 forbidden. (2) The drain turn "
            "(input `inspect the storm drain`) first and second `enforce_attempts[].narration` of every replicate in "
            "t9h-hidden/smoke, t9h-latency/{hedge-short,all-on,on-2,off-2} and t9h-drain/smoke/{off,on}, each under "
            "`rows/rows.json` (turns are lists under each replicate's `turns`): provisional_label null, item_facts_raw "
            "null (their raw replies cannot be attributed to an attempt because the recorder appended late completions "
            "to the wrong turn; say so in a `notes` field on those rows). The t9h-drain/smoke/on r0 reply that says "
            "'slightly ajar' stays unlabeled here too. Dedupe identical rows by source_ref only, never by text. Expect "
            "about 100 rows; report the exact count per source in the summary.\n"
            "TESTS: build twice gives identical output; the 49/18 carry-over; blind sheet leaks nothing (assert a list of "
            "forbidden words against a fixture sheet); fixed-seed shuffle; freeze refuses null labels and a changed "
            "hash; join requires the freeze and reports disagreements; a fixture rows.json shaped like the real ones."
        ),
    },
    {
        "key": "step1-heldout",
        "check": "heldout",
        "owns": [
            f"{ED}/drain_condition_heldout.py",
            f"{ED}/x1_condition_count.py",
            "tests/test_drain_condition_heldout.py",
            "tests/test_x1_condition_count.py",
        ],
        "brief": (
            "Two small tools for design Step 1.\n"
            "(A) `x1_condition_count.py`: the offline measurement of approach X1. For a corpus of narrations that carry "
            "the narrator's parsed reply, count how often the reply proposes a `condition` for a thing that does not "
            "declare that condition. Story-agnostic: take the declared state axes of each thing from the story package's "
            "world declarations (load the package like tests/test_scene_1b_grounding.py does and read what the world "
            "model exposes for a thing's declared states, e.g. the 'It can be: destroyed' axis of the Transit token); a "
            "proposed condition value is `undeclared` when it is not one of the thing's declared values. Input: the 49 "
            "labeled rows, read from bench/results/environment-narration/t9h-drain-details/{screen,confirm} exactly as "
            "described for rows.json plus sheet blind_key.json and labels.json (screen: sheet.md/ directory; confirm: "
            "sheet/). Do not import drain_condition_corpus.py (another worker writes it in parallel); read the files "
            "directly. CLI `--corpus-build-only --out DIR` writes DIR/x1_count.json with labeled_forbidden, "
            "labeled_clean, forbidden_with_condition, clean_with_condition, forbidden_with_undeclared_condition, "
            "clean_with_undeclared_condition, a breakdown by forbidden kind (ajar_or_cover, contents), and per-row ids. "
            "Known answer to reproduce (it was measured by hand): 18 forbidden, 31 clean, 11 forbidden rows carry a "
            "`condition` entry on the storm drain, 0 clean rows do; of the 18, 10 of 11 ajar-or-cover rows and 1 of 7 "
            "contents rows carry one. Report the undeclared-condition counts separately and say whether they equal the "
            "raw ones. This is an offline measurement, never a runtime gate.\n"
            "(B) `drain_condition_heldout.py`: assemble a held-out set that is NOT the drain, so a later condition "
            "check can be shown to generalize across things and stories. Modes `--build --out DIR` writes DIR/heldout.json "
            "{rows}; `--blind-sheet --heldout FILE --out DIR` writes a blind sheet and key like the corpus tool (narration "
            "only, shuffled with a fixed seed, no source or thing name that reveals the label). Row fields: id, thing "
            "(the declared thing the narration is about, never 'storm drain'), source_file, source_ref, narration, "
            "authored (bool), authored_note. SOURCES: (1) real recorded narrations about declared things other than the "
            "drain, taken from bench/results/environment-narration/ (survey enforce-stage1, shadow-sample*, defect-probe-* "
            "and other rows.json files; the drawer, the passenger seat, the glove box, doors and the truck appear; the "
            "plan records a first attempt that 'opens the drawer in prose'): up to 60 rows, spread across at least 3 "
            "things, preferring first attempts that the verifier or a human flagged and a similar number of ordinary "
            "ones; record exactly where each came from; do NOT pick by reading for a defect keyword in the text, pick "
            "by recorded fields (turn outcome, rejected attempt, command kind). (2) At most 14 AUTHORED rows, minimal "
            "edits of real rows (a clean row edited to state the thing is ajar or lifted, a clean row edited to state "
            "what is inside it, and the unedited originals as negatives), each with authored=true and a note naming the "
            "source row and the edit. At least 40 rows total. Labels are NOT assigned here; a person reads them.\n"
            "TESTS: x1 reproduces 18/31/11/0 on the real files, and on a tiny synthetic package a thing that declares "
            "a state axis does not count its declared value as undeclared; held-out build is deterministic, excludes the "
            "drain, caps authored rows at 14, and the blind sheet leaks no thing name or source."
        ),
    },
]


def task(entry: dict) -> dict:
    owned = [f"{ROOT}/{path}" for path in entry["owns"]]
    return {
        "key": entry["key"],
        "task_type": "code-feature",
        "engine": "codex",
        "model": "gpt-5.6-luna",
        "engine_args": ["-c", "model_reasoning_effort=high"],
        "full_access": True,
        "max_attempts": 2,
        "timeout_s": 3600,
        "check_timeout_s": 900,
        "ownership": owned,
        "expect_files": owned,
        "verified": "tests green, ruff clean, the build runs and reproduces the known counts",
        "spec": (
            f"{COMMON}\n\nFILES YOU OWN (edit only these): {', '.join(owned)}. You may READ anything. NEVER modify "
            f"anything else.\n\n{entry['brief']}\n\nHOW TO VERIFY BEFORE YOU FINISH: run `bash {CHECK} "
            f"{entry['check']}`. Do not edit the check. Finish with a short summary: what you built, the exact CLI, "
            "exact row counts per source, and any field that was not recorded."
        ),
        "check": f"bash {CHECK} {entry['check']}",
    }


manifest = {
    "run_name": "t9h-drain-condition-steps-0-1",
    "workdir": "/home/bcorfman/dev/ringer-work/t9h-drain-condition-steps-0-1",
    "max_parallel": 2,
    "worktrees": False,
    "repo": ROOT,
    "tasks": [task(entry) for entry in TASKS],
}
out = Path(__file__).with_name("run-t9h-drain-condition-free.json")
out.write_text(json.dumps(manifest, indent=2) + "\n")
print(out)
