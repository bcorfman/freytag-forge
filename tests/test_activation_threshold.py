from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ActivationRule
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import DELETE, compiled_story_copy, patch_source

PACKAGE = Path("data/stories/continuity-initiative")


@pytest.mark.parametrize(
    ("rule", "true_facts", "expected"),
    [
        (ActivationRule(all_facts_true=("mandatory_fact",)), frozenset({"mandatory_fact"}), True),
        (ActivationRule(all_facts_true=("mandatory_fact",)), frozenset(), False),
        (
            ActivationRule(all_facts_true=("mandatory_fact",), any_of=("pool_a",), at_least=1),
            frozenset({"mandatory_fact", "pool_a"}),
            True,
        ),
    ],
)
def test_activation_rule_requires_all_mandatory_facts(
    rule: ActivationRule, true_facts: frozenset[str], expected: bool
) -> None:
    assert rule.is_satisfied(true_facts) is expected


@pytest.mark.parametrize(
    ("at_least", "true_facts", "expected"),
    [
        (2, frozenset({"mandatory_fact", "pool_a", "pool_b"}), True),
        (2, frozenset({"mandatory_fact", "pool_a", "pool_b", "pool_c"}), True),
        (2, frozenset({"mandatory_fact", "pool_a"}), False),
    ],
)
def test_activation_rule_applies_pool_threshold(at_least: int, true_facts: frozenset[str], expected: bool) -> None:
    rule = ActivationRule(all_facts_true=("mandatory_fact",), any_of=("pool_a", "pool_b", "pool_c"), at_least=at_least)

    assert rule.is_satisfied(true_facts) is expected


@pytest.mark.parametrize(
    ("true_facts",),
    [
        pytest.param(
            frozenset({"pool_a", "pool_b"}),
            id="activation_rule_full_pool_cannot_replace_missing_mandatory_fact",
        ),
        pytest.param(
            frozenset({"mandatory_fact", "pool_a"}),
            id="activation_rule_rejects_too_few_pool_facts_with_mandatory_fact",
        ),
    ],
)
def test_activation_rule_rejects_insufficient_pool_facts(true_facts: frozenset[str]) -> None:
    rule = ActivationRule(all_facts_true=("mandatory_fact",), any_of=("pool_a", "pool_b"), at_least=2)

    assert not rule.is_satisfied(true_facts)


def _copied_package(tmp_path: Path) -> Path:
    return compiled_story_copy(tmp_path)


def _change_event_activation(root: Path, event_id: str, activation: dict[str, object]) -> None:
    scene_id = event_id.removeprefix("bridge_").split("_", 1)[0].upper()
    source_file = f"source/scenes/{scene_id}.yaml"
    address = f"bridge[{event_id}]"
    patch_source(root, source_file, f"{address}.when", activation.get("all_facts_true", []))
    any_of = activation.get("any_of")
    if any_of is not None:
        patch_source(root, source_file, f"{address}.when_any", any_of)
    elif event_id == "bridge_1c_infiltration_needed":
        patch_source(root, source_file, f"{address}.when_any", DELETE)
        patch_source(root, source_file, f"{address}.at_least", DELETE)
    patch_source(root, source_file, f"{address}.at_least", activation.get("at_least", 0))


@pytest.mark.parametrize(
    ("event_id", "activation", "message"),
    [
        (
            "bridge_1b_departure",
            {"all_facts_true": ["park_pursuit_resolved"], "any_of": ["transport_route_identified"], "at_least": 0},
            "outside",
        ),
        (
            "bridge_1b_departure",
            {"all_facts_true": ["park_pursuit_resolved"], "any_of": ["transport_route_identified"], "at_least": 2},
            "outside",
        ),
        (
            "bridge_2b_archive_crisis",
            {"all_facts_true": ["janus_evidence"], "at_least": 1},
            "without a fact pool",
        ),
        ("bridge_1c_infiltration_needed", {"at_least": 0}, "vacuous"),
    ],
)
def test_loader_rejects_unsatisfiable_activation_rules(
    tmp_path: Path, event_id: str, activation: dict[str, object], message: str
) -> None:
    root = _copied_package(tmp_path)
    _change_event_activation(root, event_id, activation)

    expected_message = (
        "k_bridge_1c_infiltration.*unknown or cross-scene canonical event source"
        if event_id == "bridge_1c_infiltration_needed"
        else f"canonical route event '{event_id}'.*{message}"
    )
    with pytest.raises(SourceError, match=expected_message):
        load_story_package(root)


def test_loader_checks_pool_activation_facts_against_world(tmp_path: Path) -> None:
    root = _copied_package(tmp_path)
    _change_event_activation(
        root,
        "bridge_1b_departure",
        {
            "all_facts_true": ["park_pursuit_resolved"],
            "any_of": ["unknown_activation_fact"],
            "at_least": 1,
        },
    )

    with pytest.raises(SourceError, match="unknown_activation_fact.*not declared"):
        load_story_package(root)


def _set_true(state: RuntimeState, fact_id: str) -> None:
    state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))


@pytest.mark.parametrize(
    ("pool_facts", "fires", "exit_available"),
    [
        (("transport_route_identified", "brandon_identified", "missing_may_be_alive"), True, True),
        (("transport_route_identified",), False, False),
    ],
)
def test_scene_1b_departure_bridge_uses_threshold_pool(
    pool_facts: tuple[str, ...], fires: bool, exit_available: bool
) -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    scene = next(item for item in package.scenes if item.metadata.scene_id == "1B")
    state.current_scene_id = scene.metadata.scene_id
    state.phase = scene.metadata.freytag_phase
    _set_true(state, "park_pursuit_resolved")
    for fact_id in pool_facts:
        _set_true(state, fact_id)

    engine = RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": "The scene continues."}]})
    engine._apply_canonical_route_events()

    assert ("bridge_1b_departure" in state.fired_event_ids) is fires
    assert (
        Fact(predicate="transport_route_departure_ready", subject="story", value="true") in state.facts.asserted
    ) is fires
    assert (
        "t_1b_1c" in {transition.id for transition in engine.validator.eligible_transitions(state)}
    ) is exit_available
