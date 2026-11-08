# ruff: noqa: E501
"""Write live-smoke-manifest.json (pair 1) and live-manifest.json (pairs 2-4): experiment L, path A (richer-3a-detention).
One Ringer probe task per (arm, replicate); CONTROL runs bench from the clean shipped-commit worktree, FINAL from this working tree.
The check runs `python -m bench run --replicates 1 --confirm` (billed, judges off), refuses to re-bill when its output exists, and never fails on a
failed replicate (those are data); it fails only when the bench wrote no records. Uses no bashisms (Ringer runs checks under /bin/sh)."""

import json
from pathlib import Path

HERE = Path(__file__).parent
MAIN = "/home/bcorfman/dev/freytag-forge"
CONTROL = "/home/bcorfman/dev/ringer-work/shared-narrator-control-tree"
OUT = f"{MAIN}/bench/results/shared-narrator/live"
SCRIPT = "richer-3a-detention"
TREES = {"control": CONTROL, "final": MAIN}
base = json.loads((HERE / "u-manifest.json").read_text())
template = base["tasks"][0]


def task(arm: str, rep: int) -> dict:
    tree, key, out = TREES[arm], f"live-{arm}-r{rep}", f"{OUT}/{arm}-r{rep}"
    t = json.loads(json.dumps(template))
    t["key"] = key
    t["ownership"] = [f"{OUT}/{key}-ready.txt"]
    t["expect_files"] = [f"{OUT}/{key}-ready.txt"]
    t["spec"] = (
        "You are a trivial placeholder worker for a billed live run that Ringer's check performs itself. Boundary: do NOT run any bench command, do NOT call any model or "
        f"network service, do NOT touch any file except the one you own, never git commit. Your only job: write the single line 'ready {key}' into the file {OUT}/{key}-ready.txt "
        f"(create it; the directory exists). Nothing else is needed; the check afterwards runs replicate {rep} of the {arm.upper()} arm of experiment L, path A "
        f"(.plans/shared-narrator-instruction-conflicts-prereg.md) and writes its records under {out}. Do not read or edit anything else."
    )
    t["check"] = (
        f"cd {tree} || exit 1\n"
        f"export PYTHONPATH={tree}:{tree}/packages/worldkeeper/src TMPDIR=/tmp\n"
        f"[ ! -e {out}/summary.json ] || {{ echo 'output already exists; refusing to re-bill'; exit 1; }}\n"
        f"mkdir -p {OUT}\n"
        f".venv/bin/python -m bench run --variation bench/variations/richer-3a-live.json --scene 3A --script {SCRIPT} --replicates 1 --out {out} --confirm > {out}.log 2>&1\n"
        "rc=$?\n"
        f"tail -6 {out}.log\n"
        f'[ -s {out}/summary.json ] && [ -s {out}/all-turn-records.json ] || {{ echo "WHY: bench wrote no records (rc=$rc)"; exit 1; }}\n'
        f".venv/bin/python - <<'PY2'\nimport json\ns = json.load(open('{out}/summary.json'))\n"
        "print({k: s.get(k) for k in ('failed_replicates', 'completed_replicates', 'failure_reason') if k in s})\n"
        "print(s.get('budget'))\nPY2\nexit 0\n"
    )
    return t


for name, run, pairs in (
    ("live-smoke-manifest.json", "shared-narrator-live-smoke", [1]),
    ("live-manifest.json", "shared-narrator-live", [2, 3, 4]),
):
    m = json.loads(json.dumps(base))
    m["run_name"] = run
    m["workdir"] = f"/home/bcorfman/dev/ringer-work/{run}"
    m["max_parallel"] = 2
    m["tasks"] = [task(arm, rep) for rep in pairs for arm in ("control", "final")]
    (HERE / name).write_text(json.dumps(m, indent=2) + "\n")
    print(name, [t["key"] for t in m["tasks"]])
