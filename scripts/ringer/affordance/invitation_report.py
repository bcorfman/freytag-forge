"""Audit player-visible cue invitations against authored reveal actions."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.ringer.affordance.cue_eligibility_compare import (
    _cue_available,
    _matching_reveals,
    _scene_states,
)
from storygame.runtime.candidate_matcher import ActionEvidenceCandidate, uniquely_matched_candidate
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.story_package.loader import load_story_package

LABELS = ("eligible response", "unanswered invitation", "unknown")
_UNREVIEWED_PHRASES = (
    "is worth",
    "may be worth",
    "waits",
    "lies beside",
    "ready to answer",
    "overlooks",
    "closing in",
)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _true_fact_ids(state: Any) -> frozenset[str]:
    return frozenset(fact.predicate for fact in state.facts.asserted if str(fact.value).lower() == "true")


def _representative_command(item: Any) -> str | None:
    if not item.action_evidence or any(not group for group in item.action_evidence):
        return None
    return " ".join(group[0] for group in item.action_evidence)


def _matcher_result(state: Any, command: str, expected_id: str) -> bool:
    candidates = KnowledgeProjector().project(state, "player", command).candidates
    evidence = tuple(
        ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence)
        for candidate in candidates
        if candidate.action_evidence
    )
    matched = uniquely_matched_candidate(command, evidence)
    return matched is not None and matched.id == expected_id


def _row(package: Any, scene_id: str, state_label: str, state: Any, delivery: Any) -> tuple[str, str] | None:
    if delivery.fact_id in _true_fact_ids(state) or not _cue_available(state, delivery.fact_id):
        return None

    matching = _matching_reveals(package, scene_id, delivery)
    explanations = tuple((item, explain_reveal(state, "player", item)) for item in matching)
    details: list[str] = []
    has_eligible_match = False
    for item, explanation in explanations:
        detail = f"{item.id}:{explanation.reason}"
        if explanation.eligible:
            command = _representative_command(item)
            matched = command is not None and _matcher_result(state, command, item.id)
            detail += f" command={command!r} exact={'yes' if matched else 'no'}"
            has_eligible_match |= matched
        details.append(detail)

    reasons = {explanation.reason for _, explanation in explanations}
    if has_eligible_match:
        label = "eligible response"
    elif not matching or any(explanation.eligible for _, explanation in explanations):
        label = "unknown"
    elif reasons <= {"storylet_spent", "already_established", "prerequisite_missing", "source_inactive"}:
        label = "unanswered invitation"
    else:
        label = "unknown"

    row = " | ".join(
        (
            scene_id,
            state_label,
            delivery.fact_id,
            delivery.cue_text,
            ", ".join(details) or "-",
            label,
        )
    )
    return row, label


def _sentences(text: str) -> tuple[str, ...]:
    return tuple(sentence.strip() for sentence in _SENTENCE_END.split(" ".join(text.split())) if sentence.strip())


def _unreviewed_candidates(package: Any) -> list[str]:
    candidates: list[str] = []
    sources: list[tuple[str, str]] = []
    for delivery in package.deliveries:
        sources.append((f"delivery {delivery.fact_id} fallback_text", delivery.fallback_text))
    for item in package.knowledge.knowledge:
        if item.delivery_text:
            sources.append((f"reveal {item.id} delivery_text", item.delivery_text))
    for scene in package.scenes:
        sources.append((f"scene {scene.metadata.scene_id} entry_text", scene.metadata.entry_text))
    for source_id, text in sources:
        for sentence in _sentences(text):
            if any(phrase in sentence.casefold() for phrase in _UNREVIEWED_PHRASES):
                candidates.append(f"- {source_id}: {sentence}")
    return candidates


def report(package: Any) -> str:
    rows: list[str] = []
    counts: Counter[str] = Counter()
    for scene in package.scenes:
        scene_id = scene.metadata.scene_id
        deliveries = tuple(
            sorted(
                (delivery for delivery in package.deliveries if delivery.scene_id == scene_id and delivery.cue_text),
                key=lambda delivery: delivery.fact_id,
            )
        )
        for raw_label, state in _scene_states(package, scene_id):
            state_label = "entry" if raw_label == "S0" else raw_label.replace(" fired through ", " fired through ")
            for delivery in deliveries:
                result = _row(package, scene_id, state_label, state, delivery)
                if result is not None:
                    row, label = result
                    rows.append(row)
                    counts[label] += 1

    lines = [
        "INVITATION REPORT",
        "Legend: eligible response | unanswered invitation | unknown",
        "Rows are shown cue_text invitations whose cue is available in the reported state.",
        "",
        "scene | state | delivery fact | cue_text | matching reveals and representative commands | label",
        *rows,
        "",
        "LABEL COUNTS",
        *(f"{label}: {counts[label]}" for label in LABELS),
        "",
        "LIMITS",
        "- Covers cue_text only.",
        "- Covers only the states cue_eligibility_compare reports; it is not exhaustive.",
        "- Cannot see narrator-invented pointers.",
        "- Delivery pointer lines and entry text are not scored.",
        "",
        "UNREVIEWED CANDIDATES",
        *_unreviewed_candidates(package),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    package_dir = Path(args[0]) if args else Path("data/stories/continuity-initiative")
    print(report(load_story_package(package_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
