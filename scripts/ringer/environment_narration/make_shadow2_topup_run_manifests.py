# ruff: noqa: E501
"""Generate the Ringer manifests for the second shadow sample top-up."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path("/home/bcorfman/dev/freytag-forge")
HERE = Path(__file__).resolve().parent
PREREG = ".plans/grounded-llm-environment-narration/t8-shadow-sample2-topup-prereg.md"


def _topup_strings(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("shadow-sample2", "shadow-sample2-topup").replace(
            "shadow_sample2.sh", "shadow_sample2_topup.sh"
        )
    if isinstance(value, list):
        return [_topup_strings(item) for item in value]
    if isinstance(value, dict):
        return {key: _topup_strings(item) for key, item in value.items()}
    return value


def _approval_sentence(stage: str) -> tuple[str, str]:
    if stage == "smoke":
        old = (
            "This run is approved in the sample-2 preregistration "
            "(.plans/grounded-llm-environment-narration/t8-shadow-sample2-prereg.md), and the runner must not "
            "start unless the human's go for this stage was given in the task statement (the manifest is only "
            "launched by the orchestrator after the go). It uses about 67 calls, cap 100 calls, ceiling $0.05."
        )
        new = (
            "This run is a top-up approved in the sample-2 preregistration "
            f"({PREREG}), and the runner must not start unless the human's go for this stage was given in the "
            "task statement (the manifest is only launched by the orchestrator after the go). It uses about 46 "
            "calls, cap 70 calls, ceiling $0.03."
        )
    else:
        old = (
            "This run is approved in the sample-2 preregistration "
            "(.plans/grounded-llm-environment-narration/t8-shadow-sample2-prereg.md), and the runner must not "
            "start unless the human's go for this stage was given in the task statement (the manifest is only "
            "launched by the orchestrator after the go). It uses about 670 calls, cap 900 calls, ceiling $0.30; "
            "expected about thirteen cents."
        )
        new = (
            "This run is a top-up approved in the sample-2 preregistration "
            f"({PREREG}), and the runner must not start unless the human's go for this stage was given in the "
            "task statement (the manifest is only launched by the orchestrator after the go). It uses about 460 "
            "calls, cap 600 calls, ceiling $0.20; expected about nine cents."
        )
    return old, new


def _check(stage: str) -> str:
    if stage == "smoke":
        ceiling = 30000
        expected_replicates = 1
    else:
        ceiling = 200000
        expected_replicates = 10
    base = f"bench/results/environment-narration/shadow-sample2-topup/{stage}"
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
    assert all(len(row.get('turns', [])) == 9 for row in rows), 'incomplete route'
    for row in rows:
        assert row['turns'][-1]['input'] == 'inspect the passenger seat', 'wrong final command'
        assert row['turns'][7]['input'] == 'pick up my laptop', 'wrong eighth command'
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
    source = HERE / f"run-shadow2-{stage}.json"
    manifest = _topup_strings(json.loads(source.read_text(encoding="utf-8")))
    manifest["workdir"] = f"/home/bcorfman/dev/ringer-work/grounded-environment-narration-shadow2-topup-{stage}"
    task = manifest["tasks"][0]
    task["key"] = f"billed-shadow-sample2-topup-{stage}"
    old, new = _approval_sentence(stage)
    task["spec"] = task["spec"].replace(
        "It plays the 'observe' route",
        "It plays the 'observe_topup' route (9 commands): inspect the drawer, pull out the drawer, "
        "feel under the drawer, feel under the drawer, go outside, inspect the truck, enter the truck, "
        "pick up my laptop, inspect the passenger seat",
    )
    old = _topup_strings(old)
    assert old in task["spec"], "sample-2 approval sentence not found in the source spec"
    task["spec"] = task["spec"].replace(old, new)
    task["check"] = _check(stage)
    return manifest


def main() -> None:
    for stage in ("smoke", "full"):
        target = HERE / f"run-shadow2-topup-{stage}.json"
        target.write_text(json.dumps(_manifest(stage), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
