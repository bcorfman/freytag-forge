"""Deterministic persona harnesses for the authored story package."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import StoryPackage
from storygame.story_package.obligations import required_storylet_ids

PERSONAS = {
    "thorough": "Act on the strongest available lead.",
    "staller": "Wait and watch the room.",
    "wrong_lead": "Follow the side thread.",
}

_RESOLUTION_FACT = "resolution_complete"


def _turn_cap(package: StoryPackage) -> int:
    return sum(window.handoff_after_turns for window in package.pacing.scenes) + len(package.pacing.scenes)


class _ScriptedProvider:
    """Return one grounded, package-authored candidate selected by the persona."""

    def __init__(self, package: StoryPackage, state: RuntimeState) -> None:
        self.package = package
        self.state = state
        self.selected: tuple[str, ...] = ()
        self.handoff_ids: list[tuple[str, ...]] = []

    def __call__(self, _player_input: str) -> dict[str, object]:
        self.handoff_ids.append(self.state.staged_handoff_fact_ids)
        text = "A concrete authored consequence lands."
        if self.selected:
            knowledge = self.package.knowledge_indexes.by_id[self.selected[0]]
            text = knowledge.delivery_text or knowledge.statement
        return {
            "segments": [{"kind": "narration", "text": text, "grounding_ids": list(self.selected)}],
            "selected_knowledge_ids": list(self.selected),
        }


class _StaticResponse:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _StaticResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _stub_urlopen(_request: object, **_kwargs: object) -> _StaticResponse:
    return _StaticResponse(
        {"narration": json.dumps({"segments": [{"kind": "narration", "text": "Kristin waits and watches."}]})}
    )


def _legacy_package(package: StoryPackage) -> StoryPackage:
    """Make the first authored storylet reveal use the legacy delivery path."""

    legacy_id = next(
        item.id
        for item in package.knowledge.knowledge
        if item.source.kind == "storylet_realization" and item.delivery_text
    )

    def update_item(item: Any) -> Any:
        return item.model_copy(update={"delivery_text": None}) if item.id == legacy_id else item

    knowledge = package.knowledge.model_copy(
        update={"knowledge": tuple(update_item(item) for item in package.knowledge.knowledge)}
    )
    indexes = package.knowledge_indexes.model_copy(
        update={"by_id": {item.id: update_item(item) for item in package.knowledge.knowledge}}
    )
    return package.model_copy(update={"knowledge": knowledge, "knowledge_indexes": indexes})


def _true_facts(state: RuntimeState) -> frozenset[str]:
    return frozenset(fact.predicate for fact in state.facts.asserted if str(fact.value).lower() == "true")


def _resolution_complete(state: RuntimeState) -> bool:
    return _RESOLUTION_FACT in _true_facts(state)


def _bridge(package: StoryPackage, state: RuntimeState):
    true_facts = _true_facts(state)
    return next(
        (
            event
            for event in package.storylet_routes.bridge_events
            if event.scene_id == state.current_scene_id
            and event.id not in state.fired_event_ids
            and not event.activation.is_satisfied(true_facts)
        ),
        None,
    )


def _candidate_new_facts(package: StoryPackage, candidate_id: str, true_facts: frozenset[str]) -> set[str]:
    return {
        effect.fact_id
        for effect in package.knowledge_indexes.by_id[candidate_id].establishes
        if effect.fact_id not in true_facts
    }


def _candidate_survives_turn(package: StoryPackage, state: RuntimeState, candidate) -> bool:
    definition = package.knowledge_indexes.by_id[candidate.id]
    if definition.source.storylet_id in required_storylet_ids(package):
        return True
    route = next(route for route in package.storylet_routes.storylets if route.id == definition.source.storylet_id)
    turns_since_entry = state.turn_index - state.scene_entered_at_turn
    return route.latest_turn >= turns_since_entry + 1


def _select_thorough(package: StoryPackage, state: RuntimeState, candidates) -> str | None:
    candidates = tuple(candidate for candidate in candidates if _candidate_survives_turn(package, state, candidate))
    required = required_storylet_ids(package)
    true_facts = _true_facts(state)
    bridge = _bridge(package, state)
    missing = set(bridge.activation.minimal_undelivered_facts(true_facts)) if bridge else set()

    def rank(candidate) -> tuple[int, bool, bool, str]:
        definition = package.knowledge_indexes.by_id[candidate.id]
        new_facts = _candidate_new_facts(package, candidate.id, true_facts)
        return (
            len(new_facts & missing),
            definition.source.storylet_id in required,
            bool(new_facts),
            candidate.id,
        )

    return max(candidates, key=rank).id if candidates else None


def _select_wrong_lead(package: StoryPackage, state: RuntimeState, candidates) -> str | None:
    required = required_storylet_ids(package)
    optional = [
        candidate
        for candidate in candidates
        if package.knowledge_indexes.by_id[candidate.id].source.storylet_id not in required
        and _candidate_survives_turn(package, state, candidate)
    ]
    return optional[0].id if optional else None


def _scene_row(scene_id: str) -> dict[str, object]:
    return {
        "scene_id": scene_id,
        "turns_to_exit": 0,
        "cue_count": 0,
        "cue_fact_ids": [],
        "deadline_staged": False,
        "costs_applied": [],
        "complication_texts": [],
        "layer_reached": "none",
    }


def _record_delivery(
    row: dict[str, object],
    package: StoryPackage,
    handoff_ids: tuple[str, ...],
    state: RuntimeState,
    selected: str | None,
    stayed_in_scene: bool,
) -> None:
    delivery = state.last_turn_delivery
    cue_fact_id = delivery.cue_fact_id
    if cue_fact_id:
        row["cue_count"] = int(row["cue_count"]) + 1
        row["cue_fact_ids"].append(cue_fact_id)
    if delivery.handoff_staged:
        row["deadline_staged"] = True
        costs = row["costs_applied"]
        for item in package.deliveries:
            if item.fact_id in handoff_ids:
                costs.extend(cost.fact_id for cost in item.costs if cost.op == "assert")
    if (
        delivery.complication_text
        and selected is None
        and stayed_in_scene
        and delivery.complication_text not in row["complication_texts"]
    ):
        row["complication_texts"].append(delivery.complication_text)
    if row["deadline_staged"]:
        row["layer_reached"] = "deadline"
    elif row["cue_count"]:
        row["layer_reached"] = "cue"
    elif row["complication_texts"]:
        row["layer_reached"] = "complication"


def _run(
    name: str,
    package: StoryPackage,
    provider_factory: Callable[[RuntimeState], tuple[Callable[[str], object], object]],
    state: RuntimeState | None = None,
) -> dict[str, object]:
    state = state or RuntimeState.bootstrap(package)
    provider, recorder = provider_factory(state)
    engine = RuntimeEngine(state, provider)
    rows = {scene.metadata.scene_id: _scene_row(scene.metadata.scene_id) for scene in package.scenes}
    rejected_turns: list[int] = []

    for _ in range(_turn_cap(package)):
        if _resolution_complete(state):
            break
        engine._activate_pacing()
        projection = engine.projector.project(state, "player", "")
        if name == "thorough":
            selected = _select_thorough(package, state, projection.candidates)
        elif name == "wrong_lead":
            selected = _select_wrong_lead(package, state, projection.candidates)
        else:
            selected = None
        if isinstance(recorder, _ScriptedProvider):
            recorder.selected = (selected,) if selected else ()
        scene_id = state.current_scene_id
        try:
            engine.turn(PERSONAS[name])
        except (ProposalValidationError, RuntimeContractError):
            rejected_turns.append(state.turn_index + 1)
            if isinstance(recorder, _ScriptedProvider):
                recorder.selected = ()
            engine.turn(PERSONAS[name])
        row = rows[scene_id]
        row["turns_to_exit"] = int(row["turns_to_exit"]) + 1
        handoff_ids = recorder.handoff_ids[-1] if hasattr(recorder, "handoff_ids") else ()
        _record_delivery(row, package, handoff_ids, state, selected, state.current_scene_id == scene_id)

    ordered_rows = [rows[scene.metadata.scene_id] for scene in package.scenes]
    return {
        "persona": name,
        "resolution_complete": _resolution_complete(state),
        "rejected_turns": rejected_turns,
        "scenes": ordered_rows,
    }


def _scripted_factory(package: StoryPackage):
    def factory(state: RuntimeState) -> tuple[Callable[[str], object], object]:
        actual_package = _legacy_package(package)
        provider = _ScriptedProvider(actual_package, state)
        return provider, provider

    return factory


def _staller_factory(state: RuntimeState) -> tuple[Callable[[str], object], object]:
    from storygame.runtime import cloudflare

    original_urlopen = cloudflare.urlopen
    cloudflare.urlopen = _stub_urlopen
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    handoff_ids: list[tuple[str, ...]] = []

    def wrapped(player_input: str) -> object:
        handoff_ids.append(state.staged_handoff_fact_ids)
        return provider(player_input)

    class _Recorder:
        def __init__(self) -> None:
            self.handoff_ids = handoff_ids

        def restore(self) -> None:
            cloudflare.urlopen = original_urlopen

    recorder = _Recorder()
    return wrapped, recorder


def run_persona(name: str, package: StoryPackage) -> dict[str, object]:
    """Run one deterministic persona against a package and return its summary."""

    if name not in PERSONAS:
        raise ValueError(f"unknown persona: {name}")
    if name == "staller":
        state = RuntimeState.bootstrap(package)
        provider, recorder = _staller_factory(state)
        try:
            return _run(name, package, lambda _state: (provider, recorder), state)
        finally:
            recorder.restore()
    return _run(name, package, _scripted_factory(package))


def _load_real_package() -> StoryPackage:
    return load_story_package(Path(__file__).resolve().parents[1] / "data/stories/continuity-initiative")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    package = _load_real_package()
    summary = {name: run_persona(name, package) for name in PERSONAS}
    args.out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
