"""Probe 3C relay wording against the real runtime narration guard."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from bench.core import (  # noqa: E402
    load_variation,
    package_and_state,
    resolve_variation,
)
from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal  # noqa: E402
from storygame.runtime.facts import Fact  # noqa: E402
from storygame.runtime.knowledge import KnowledgeProjector  # noqa: E402
from storygame.runtime.narration_safety import NarrationSafetyValidator  # noqa: E402
from storygame.runtime.validation import ProposalValidationError  # noqa: E402

VARIATION_PATH = ROOT / "bench/variations/stage7-3c-control.json"
REPORT_DIR = ROOT / "bench/results/stage7-3c-relay-wording"
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")

TEXTS = (
    ("1", "Brandon's relay is open."),
    ("2", "Brandon is at the relay."),
    ("3", "Brandon's relay is holding."),
    ("4", "Brandon's relay held open."),
    ("5", "The relay is open."),
    ("6", "Brandon keeps the relay open."),
    (
        "7",
        "The broadcast chamber lights are steady. Michelle's evidence package is ready to send. "
        "Water is entering the outer access level.",
    ),
    (
        "8",
        "The broadcast chamber lights are steady. Brandon is at the relay. Michelle's evidence package "
        "is ready to send. Water is entering the outer access level.",
    ),
    (
        "9",
        "The broadcast chamber lights are steady. Brandon's relay is open. Michelle's evidence package "
        "is ready to send. Water is entering the outer access level.",
    ),
    ("10", "Michelle sends the evidence package to the independent networks."),
    ("11", "Kristin looks around the broadcast chamber."),
)


def entry_state() -> tuple[Any, Any]:
    variation = load_variation(VARIATION_PATH)
    package, state = package_and_state(variation, "3C")
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return package, state


def run_guard(text: str) -> dict[str, object]:
    _package, state = entry_state()
    proposal = ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=text),))
    try:
        NarrationSafetyValidator().validate(
            state,
            deepcopy(state),
            proposal,
            KnowledgeProjector(),
            "Look around.",
        )
    except ProposalValidationError as error:
        return {"accepted": False, "error": str(error)}
    return {"accepted": True, "error": None}


def loader_result(text: str) -> tuple[bool, str | None]:
    entry_variation = load_variation(ROOT / "bench/variations/stage7-3c-entry-package.json")
    entry_replacement = entry_variation["overrides"]["plot.md"]["replacements"][0]
    replacement = {
        "old": entry_replacement["old"],
        "new": f'entry_text: "{text}\\n\\n"',
    }
    variation = {
        "name": f"relay-wording-{abs(hash(text))}",
        "story_package": "data/stories/continuity-initiative",
        "overrides": {"plot.md": {"replacements": [replacement]}},
    }
    try:
        resolve_variation(variation, ROOT / "bench/variations/stage7-3c-control.json")
    except Exception as error:  # loader errors are part of this probe's result
        return False, str(error)
    return True, None


def main() -> int:
    results: list[dict[str, object]] = []
    loader: dict[str, dict[str, object]] = {}
    for identifier, text in TEXTS:
        outcome = run_guard(text)
        results.append({"id": identifier, "text": text, **outcome})
        if identifier in {"7", "8", "9"}:
            accepted, error = loader_result(text)
            loader[identifier] = {"accepted": accepted, "error": error}

    controls = {item["id"]: item for item in results if item["id"] in {"10", "11"}}
    trustworthy = controls["10"]["accepted"] is False and controls["11"]["accepted"] is True
    report_json = REPORT_DIR / "report.json"
    report_md = REPORT_DIR / "report.md"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Stage 7 3C relay wording probe",
        "",
        "| ID | Guard | Loader (7–9 only) | Text / error |",
        "|---:|:---:|:---:|---|",
    ]
    for item in results:
        loader_cell = "—"
        if item["id"] in loader:
            load = loader[item["id"]]
            loader_cell = "accepted" if load["accepted"] else f"rejected: {load['error']}"
        error = item["error"] or "—"
        verdict = "accepted" if item["accepted"] else "rejected"
        lines.append(f"| {item['id']} | {verdict} | {loader_cell} | {item['text']} — {error} |")
    lines.extend(
        [
            "",
            "Reading: wording that avoids the relay guard describes Brandon's location (or omits the relay claim) "
            "rather than stating that the relay is open. The standalone location phrasing and the longer scene "
            "text with that phrasing are accepted by the guard; the loader result separately shows which full "
            "entry texts are legal scene prose. Controls: ID 10 must reject and ID 11 must accept.",
            "",
            f"Control trustworthiness: {'PASS' if trustworthy else 'LOUD FAILURE — probe is not trustworthy'}.",
        ]
    )
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not trustworthy:
        print("LOUD FAILURE: control results are opposite of the required outcomes", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
