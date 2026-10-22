"""Check the CI change that moves coverage from every push to a nightly run."""

import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
TEST = ROOT / ".github/workflows/test.yml"
NIGHTLY = ROOT / ".github/workflows/coverage-nightly.yml"
COV_FLAG = re.compile(r"--cov(?![-\w])")


def fail(message: str) -> None:
    sys.exit(f"FAIL: {message}")


def runs(job: dict) -> list[str]:
    return [step["run"] for step in job.get("steps", []) if "run" in step]


def triggers(doc: dict) -> dict:
    return doc.get("on", doc.get(True)) or {}


if not NIGHTLY.exists():
    fail(f"{NIGHTLY} does not exist")
test = yaml.safe_load(TEST.read_text(encoding="utf-8"))
nightly = yaml.safe_load(NIGHTLY.read_text(encoding="utf-8"))

jobs = test["jobs"]
for job_id, job in jobs.items():
    for needed in [job["needs"]] if isinstance(job.get("needs"), str) else job.get("needs", []):
        if needed not in jobs:
            fail(f"test.yml job '{job_id}' needs missing job '{needed}'")
    for command in runs(job):
        if COV_FLAG.search(command) or "coverage combine" in command or "coverage report" in command:
            fail(f"test.yml job '{job_id}' still runs coverage: {command!r}")
    for step in job.get("steps", []):
        if "coverage" in str(step.get("with", {}).get("name", "")).lower():
            fail(f"test.yml job '{job_id}' still uploads coverage data")
    if "overage" in job.get("name", ""):
        fail(f"test.yml job '{job_id}' is still named for coverage: {job['name']!r}")
if "test-shard" not in jobs:
    fail("test.yml lost the test-shard job")
shard = jobs["test-shard"]
if shard["strategy"]["matrix"]["shard"] != [0, 1, 2, 3, 4, 5]:
    fail("test-shard matrix must stay [0..5] so tests/shard_durations.json balance holds")
shard_cmd = " ".join(runs(shard))
for needle in ("--shard-index", "--shard-count 6", "--no-cov", "-n 4"):
    if needle not in shard_cmd:
        fail(f"test-shard command lacks {needle!r}: {shard_cmd!r}")
if "test-shard" not in jobs["deploy-staging"]["needs"]:
    fail("deploy-staging must wait for test-shard")

on = triggers(nightly)
cron = [item["cron"] for item in on.get("schedule", [])]
if len(cron) != 1 or not re.fullmatch(r"\d+ [0-9,]+ \* \* \*", cron[0]):
    fail(f"coverage-nightly.yml needs exactly one daily cron, got {cron}")
if "workflow_dispatch" not in on:
    fail("coverage-nightly.yml needs workflow_dispatch")
if "push" in on or "pull_request" in on:
    fail("coverage-nightly.yml must not run on push or pull_request")
if nightly.get("permissions") != {"contents": "read"}:
    fail("coverage-nightly.yml permissions must be contents: read")
njobs = nightly["jobs"]
shard_jobs = [j for j in njobs.values() if "strategy" in j]
gate_jobs = [j for j in njobs.values() if "strategy" not in j]
if len(shard_jobs) != 1 or len(gate_jobs) != 1:
    fail("coverage-nightly.yml needs one sharded job and one gate job")
n_shard, gate = shard_jobs[0], gate_jobs[0]
if n_shard["strategy"]["matrix"]["shard"] != [0, 1, 2, 3, 4, 5]:
    fail("nightly shard matrix must be [0..5]")
cmd = " ".join(runs(n_shard))
for needle in ("--cov", "--shard-index", "--shard-count 6", "--cov-fail-under=0"):
    if needle not in cmd:
        fail(f"nightly shard command lacks {needle!r}: {cmd!r}")
shard_id = next(k for k, v in njobs.items() if v is n_shard)
if shard_id not in ([gate["needs"]] if isinstance(gate["needs"], str) else gate["needs"]):
    fail("nightly gate must need the shard job")
gate_cmd = " ".join(runs(gate))
if "coverage combine" not in gate_cmd or "coverage report" not in gate_cmd:
    fail("nightly gate must combine and report coverage")
if "coverage-shard-" not in NIGHTLY.read_text(encoding="utf-8"):
    fail("nightly must upload and download coverage-shard-* artifacts")

status = subprocess.run(
    ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True
).stdout.splitlines()
changed = {line[3:] for line in status}
allowed = {".github/workflows/test.yml", ".github/workflows/coverage-nightly.yml"}
extra = {p for p in changed - allowed if not p.startswith("scripts/ringer/stage7/ci-coverage-nightly")}
if extra:
    fail(f"unexpected changed files: {sorted(extra)}")
if allowed - changed:
    fail(f"expected changes missing: {sorted(allowed - changed)}")
print("ok")
