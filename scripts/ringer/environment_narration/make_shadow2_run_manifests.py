# ruff: noqa: E501
"""Generate the Ringer manifests for the second billed shadow sample."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path("/home/bcorfman/dev/freytag-forge")
HERE = Path(__file__).resolve().parent
PREREG = ".plans/grounded-llm-environment-narration/t8-shadow-sample2-prereg.md"


def _sample2_strings(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("shadow-sample", "shadow-sample2").replace("shadow_sample.sh", "shadow_sample2.sh")
    if isinstance(value, list):
        return [_sample2_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: _sample2_strings(item) for key, item in value.items()}
    return value


def _approval_sentence(stage: str) -> tuple[str, str]:
    if stage == "smoke":
        old = (
            f"The human approved it in {PREREG}: about 40 calls, expected cost about one cent, "
            "hard ceiling $0.05 enforced by the local Worker's ledger."
        )
        new = (
            "This run is approved in the sample-2 preregistration "
            "(.plans/grounded-llm-environment-narration/t8-shadow-sample2-prereg.md), and the runner must not "
            "start unless the human's go for this stage was given in the task statement (the manifest is only "
            "launched by the orchestrator after the go). It uses about 67 calls, cap 100 calls, ceiling $0.05."
        )
    else:
        old = (
            f"The human approved it in {PREREG}: about 350 calls, expected cost about nine cents, "
            "hard ceiling $0.25 enforced by the local Worker's ledger."
        )
        new = (
            "This run is approved in the sample-2 preregistration "
            "(.plans/grounded-llm-environment-narration/t8-shadow-sample2-prereg.md), and the runner must not "
            "start unless the human's go for this stage was given in the task statement (the manifest is only "
            "launched by the orchestrator after the go). It uses about 670 calls, cap 900 calls, ceiling $0.30; "
            "expected about thirteen cents."
        )
    return old, new


def _check(stage: str) -> str:
    if stage == "smoke":
        ceiling = 50000
        expected_replicates = 1
    else:
        ceiling = 300000
        expected_replicates = 10
    base = f"bench/results/environment-narration/shadow-sample2/{stage}"
    return f"""cd {REPO} && set -o pipefail && test -f {base}/rows/rows.json && test -f {base}/rows/summary.json && test -f {base}/spent.json && .venv/bin/python - <<'PY'
import json
base='{base}'
rows=json.load(open(base+'/rows/rows.json'))
summary=json.load(open(base+'/rows/summary.json'))
assert summary['shadow'] is True, 'shadow not on'
print('replicates',len(rows),'turns',sum(len(r.get('turns',[])) for r in rows),'calls',summary['calls_made'],'stopped',summary['stopped_reason'],'errors',summary['errors'],'observation_turns',summary.get('observation_turns'),'verifier_requests',summary.get('shadow_verifier_requests'))
spent=json.load(open(base+'/spent.json'))
print('spent',spent)
assert spent['spent_micro_usd'] <= {ceiling}, 'cap exceeded'
if summary.get('stopped_reason') is None:
    assert len(rows) == {expected_replicates}, 'unexpected replicate count'
    assert all(len(row.get('turns', [])) == 13 for row in rows), 'incomplete route'
PY
(set -a; . ./.env; set +a; .venv/bin/python - <<'PY'
import os
base='{base}'
text=''.join(open(os.path.join(directory, filename)).read() for directory, _, filenames in os.walk(base) for filename in filenames)
for name in ('CLOUDFLARE_AI_TOKEN','CLOUDFLARE_ACCOUNT_ID','CLOUDFLARE_WORKER_TOKEN'):
    value=os.environ.get(name,'').strip()
    assert not value or value not in text, name+' value leaked into outputs'
print('no credential in outputs')
PY
)"""


def _manifest(stage: str) -> dict[str, Any]:
    source = HERE / ("run-shadow-smoke.json" if stage == "smoke" else "run-shadow-full.json")
    manifest = _sample2_strings(json.loads(source.read_text(encoding="utf-8")))
    manifest["workdir"] = f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow2-{stage}"
    task = manifest["tasks"][0]
    task["key"] = f"billed-shadow-sample2-{stage}"
    old, new = _approval_sentence(stage)
    task["spec"] = task["spec"].replace(old, new)
    task["check"] = _check(stage)
    return manifest


def main() -> None:
    for stage in ("smoke", "full"):
        target = HERE / f"run-shadow2-{stage}.json"
        target.write_text(json.dumps(_manifest(stage), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
