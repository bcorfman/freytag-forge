# ruff: noqa: E501
"""Generate the Ringer manifest that keeps the schema pin meaningful after the seat declaration."""

from __future__ import annotations

import json
from pathlib import Path

REPO = "/home/bcorfman/dev/freytag-forge"
OUT = Path(REPO) / "scripts/ringer/environment_narration/build-schema-pin.json"
TEST = "tests/test_package_view_scope.py"

SPEC = (
    "You are working in freytag-forge (Python 3.12). Working directory: /home/bcorfman/dev/freytag-forge. export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp; run `.venv/bin/python` (never uv). "
    "Run tests with `env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python -m pytest -q -p no:cacheprovider --no-cov <files>`. "
    f"YOU MAY EDIT ONLY {TEST}. No network. Do not git commit. NO regular expressions. "
    "BACKGROUND. `test_unmodified_package_schema_is_byte_identical` pins `EXPECTED_SCHEMA_HASH` (eed592a10904acddc8c0b8cb3831a9803cc058a7a96906c240d1a1c977132f7d) = the hash of `world_source_schema_data(PACKAGE.world)` for the shipped continuity-initiative package, to prove that the loader plumbing for the optional `view` and `contents_complete` fields changes nothing for packages that do not use them. "
    "The shipped data/stories/continuity-initiative/world.yaml now (deliberately, already done, do not touch it) declares `contents_complete: true` on exactly one entity, `truck_passenger_seat`, so the hash of the shipped package changed (new hash 708bda2...). "
    "FIX. Keep the test's guarantee instead of replacing the hash: compute the schema data of the shipped package (`world_source_schema_data(PACKAGE.world)` as the file's `_schema_hash` helper does), remove the `contents_complete` key from the entity whose id is `truck_passenger_seat` in a deep copy of that data, hash the copy the same way, and assert it equals the ORIGINAL EXPECTED_SCHEMA_HASH. Also assert that in the real data `truck_passenger_seat` has `contents_complete` True and that no other entity has a `contents_complete` or `view` key. Keep the second assertion of the test (a copied package loads to the same hash as the shipped one). Refactor `_schema_hash` minimally (for example accept the schema dict) without changing its other callers. Run ruff check and ruff format on the file. "
    "Run the whole file and then `.venv/bin/python scripts/quick_suite.py` (CLOUDFLARE_WORKER_URL and CLOUDFLARE_WORKER_TOKEN unset) and report exact counts."
)

CHECK = (
    "cd /home/bcorfman/dev/freytag-forge && export PYTHONPATH=/home/bcorfman/dev/freytag-forge TMPDIR=/tmp && set -o pipefail && "
    f"env -u CLOUDFLARE_WORKER_URL -u CLOUDFLARE_WORKER_TOKEN .venv/bin/python scripts/quick_suite.py 2>&1 | tee /tmp/pin-quick.out | grep -E 'passed|failed|FAILED' | tail -5 && "
    "! grep -Eq '[0-9]+ failed|FAILED' /tmp/pin-quick.out && grep -Eq '[0-9]+ passed' /tmp/pin-quick.out && "
    f"grep -q 'eed592a10904acddc8c0b8cb3831a9803cc058a7a96906c240d1a1c977132f7d' {TEST} && ! grep -q '708bda2' {TEST} && "
    f".venv/bin/python -m ruff check {TEST} && .venv/bin/python -m ruff format --check {TEST}"
)

manifest = {
    "run_name": "grounded-environment-narration",
    "workdir": "/home/bcorfman/dev/ringer-work/grounded-environment-narration-schema-pin",
    "max_parallel": 1,
    "worktrees": False,
    "repo": REPO,
    "tasks": [
        {
            "key": "keep-schema-pin-meaningful",
            "task_type": "code-fix",
            "engine": "codex",
            "model": "gpt-5.6-luna",
            "engine_args": ["-c", "model_reasoning_effort=medium"],
            "full_access": True,
            "max_attempts": 2,
            "timeout_s": 1800,
            "check_timeout_s": 1500,
            "ownership": [TEST],
            "expect_files": [f"{REPO}/{TEST}"],
            "spec": SPEC,
            "check": CHECK,
            "verified": "the schema pin still proves the loader changes nothing for packages without the new fields, and the seat declaration is asserted separately",
        }
    ],
}

if __name__ == "__main__":
    OUT.write_text(json.dumps(manifest, indent=2) + "\n")
