# ruff: noqa: E501
"""Write the Ringer manifests for experiment G: gu-smoke-manifest.json (sample 1) and gu-manifest.json (samples 2-4, 5-8, 9-12).
Derived from u-manifest.json so the placeholder-worker and check conventions are identical."""

import json
from pathlib import Path

here = Path(__file__).parent
base = json.loads((here / "u-manifest.json").read_text())
template = base["tasks"][0]
R = "/home/bcorfman/dev/freytag-forge/bench/results/shared-narrator/g"


def task(first, last):
    key = f"gu-{first}-{last}"
    t = json.loads(json.dumps(template))
    t["key"] = key
    t["ownership"] = [f"{R}/{key}-ready.txt"]
    t["expect_files"] = [f"{R}/{key}-ready.txt"]
    t["spec"] = (
        "You are a trivial placeholder worker for a billed replay that Ringer's check performs itself. Boundary: do NOT run any replay, "
        "do NOT call any model or network service, do NOT touch any file except the one you own, never git commit. Your only job: write "
        f"the single line 'ready {key}' into the file {R}/{key}-ready.txt (create it; the directory exists). Nothing else is needed; the "
        f"check afterwards replays samples {first} to {last} of the frozen GU payloads (experiment GU in "
        f".plans/shared-narrator-instruction-conflicts-prereg.md) and writes {R}/{key}-rows.json. Do not read or edit anything else."
    )
    count = (last - first + 1) * 3
    t["check"] = (
        "set -o pipefail\ncd /home/bcorfman/dev/freytag-forge\n"
        "export PYTHONPATH=/home/bcorfman/dev/freytag-forge:/home/bcorfman/dev/freytag-forge/packages/worldkeeper/src TMPDIR=/tmp\n"
        f"[ ! -e {R}/{key}-rows.json ] || {{ echo 'rows file already exists; refusing to re-bill'; exit 1; }}\n"
        f"/home/bcorfman/dev/freytag-forge/.venv/bin/python scripts/ringer/shared-narrator/gu_replay.py {R}/{key}-rows.json {first} {last} --confirm 2>&1 | tee {R}/{key}.log | tail -5\n"
        "/home/bcorfman/dev/freytag-forge/.venv/bin/python - <<'PY'\nimport json,sys\n"
        f"r=json.load(open('{R}/{key}-rows.json'))\n"
        "errs=[(x['arm'],x['n'],x['sample']) for x in r if x.get('error')]\n"
        "print('rows',len(r),'errors',len(errs),errs)\n"
        f"sys.exit(0 if len(r)=={count} else 'expected {count} rows, got %d'%len(r))\nPY\n"
    )
    return t


for name, run, blocks in (
    ("gu-smoke-manifest.json", "shared-narrator-gu-smoke", [(1, 1)]),
    ("gu-manifest.json", "shared-narrator-gu", [(2, 4), (5, 8), (9, 12)]),
):
    m = json.loads(json.dumps(base))
    m["run_name"] = run
    m["workdir"] = f"/home/bcorfman/dev/ringer-work/{run}"
    m["tasks"] = [task(a, b) for a, b in blocks]
    (here / name).write_text(json.dumps(m, indent=2) + "\n")
    print(name, [t["key"] for t in m["tasks"]])
