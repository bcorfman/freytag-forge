# ruff: noqa: E501
"""Generate the Ringer manifests for the post-change shadow re-run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path("/home/bcorfman/dev/freytag-forge")
HERE = Path(__file__).resolve().parent
PREREG = ".plans/grounded-llm-environment-narration/t8-shadow-postchange-rerun-prereg.md"


def _replace_everywhere(value: Any, old: str, new: str) -> tuple[Any, int]:
    if isinstance(value, str):
        count = value.count(old)
        return value.replace(old, new), count
    if isinstance(value, list):
        replaced = []
        count = 0
        for item in value:
            item, item_count = _replace_everywhere(item, old, new)
            replaced.append(item)
            count += item_count
        return replaced, count
    if isinstance(value, dict):
        replaced = {}
        count = 0
        for key, item in value.items():
            new_key, key_count = _replace_everywhere(key, old, new)
            new_item, item_count = _replace_everywhere(item, old, new)
            replaced[new_key] = new_item
            count += key_count + item_count
        return replaced, count
    return value, 0


def _replace_required(value: Any, old: str, new: str) -> Any:
    value, count = _replace_everywhere(value, old, new)
    assert count, f"required replacement did not match: {old!r}"
    return value


def _replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, f"expected one replacement for {old!r}"
    return text.replace(old, new)


def _approval_sentence(stage: str) -> tuple[str, str]:
    if stage == "smoke":
        old = (
            "This run is a top-up approved in the sample-2 preregistration "
            "(.plans/grounded-llm-environment-narration/t8-shadow-sample2-topup-prereg.md), and the runner must not "
            "start unless the human's go for this stage was given in the task statement (the manifest is only "
            "launched by the orchestrator after the go). It uses about 46 calls, cap 70 calls, ceiling $0.03."
        )
        new = (
            "This run is a re-run of the top-up route under the corrected shadow order, approved in the "
            f"preregistration {PREREG}, and the runner must not start unless the human's go for this stage was "
            "given in the task statement (the manifest is only launched by the orchestrator after the go). It uses "
            "about 50 calls, cap 70 calls, ceiling $0.03."
        )
    else:
        old = (
            "This run is a top-up approved in the sample-2 preregistration "
            "(.plans/grounded-llm-environment-narration/t8-shadow-sample2-topup-prereg.md), and the runner must not "
            "start unless the human's go for this stage was given in the task statement (the manifest is only "
            "launched by the orchestrator after the go). It uses about 460 calls, cap 600 calls, ceiling $0.20; "
            "expected about nine cents."
        )
        new = (
            "This run is a re-run of the top-up route under the corrected shadow order, approved in the "
            f"preregistration {PREREG}, and the runner must not start unless the human's go for this stage was "
            "given in the task statement (the manifest is only launched by the orchestrator after the go). It uses "
            "about 495 calls, cap 600 calls, ceiling $0.20; expected about nine cents."
        )
    return old, new


def _manifest(stage: str) -> dict[str, Any]:
    source = HERE / f"run-shadow2-topup-{stage}.json"
    manifest = json.loads(source.read_text(encoding="utf-8"))
    task = manifest["tasks"][0]
    old_approval, new_approval = _approval_sentence(stage)
    task["spec"] = _replace_once(task["spec"], old_approval, new_approval)
    task["key"] = _replace_once(
        task["key"],
        f"billed-shadow-sample2-topup-{stage}",
        f"billed-shadow-sample3-postchange-{stage}",
    )
    manifest = _replace_required(manifest, "shadow-sample2-topup", "shadow-sample3-postchange")
    manifest = _replace_required(manifest, "shadow_sample2_topup.sh", "shadow_sample3_postchange.sh")
    manifest = _replace_required(manifest, f"shadow2-topup-{stage}", f"shadow3-postchange-{stage}")
    return manifest


def main() -> None:
    for stage in ("smoke", "full"):
        target = HERE / f"run-shadow3-postchange-{stage}.json"
        target.write_text(json.dumps(_manifest(stage), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
