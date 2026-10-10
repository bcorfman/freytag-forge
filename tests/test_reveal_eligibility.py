from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.reveal_eligibility import (
    ALREADY_ESTABLISHED,
    ELIGIBLE,
    NOT_VISIBLE,
    PREREQUISITE_MISSING,
    SOURCE_INACTIVE,
    STORYLET_SPENT,
    explain_reveal,
)
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import predicate_matches
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import Audience, FactPredicate, KnowledgeDefinition, RevealSource, RouteOperation

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _old_established(item: KnowledgeDefinition, state: RuntimeState) -> bool:
    def effect_matches(effect: object) -> bool:
        expected = str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value)
        matched = any(
            (fact.value if fact.value is not None else fact.object) == expected
            for fact in state.facts.matching(effect.fact_id)
        )
        return matched if effect.op == "assert" else not matched

    return all(effect_matches(effect) for effect in item.establishes)


def _old_visible_to(item: KnowledgeDefinition, audience_id: str) -> bool:
    if item.audience.kind == "world_only":
        return False
    if audience_id == "player":
        return item.audience.player_visible
    return item.audience.kind == "public" or audience_id in item.audience.character_ids


def _old_eligible(state: RuntimeState, audience_id: str, item: KnowledgeDefinition) -> bool:
    if _old_established(item, state) or not _old_visible_to(item, audience_id):
        return False
    if item.source.storylet_id in state.fired_event_ids:
        return False
    if not all(predicate_matches(predicate, state.facts) for predicate in item.requires):
        return False
    return item.source.kind == "storylet_realization" and item.source.storylet_id in state.active_event_ids


def _scene_state(scene_id: str) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState(package=PACKAGE, current_scene_id=scene_id, phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact(scene_id)
    return state


def _assert_reference_matches(state: RuntimeState) -> None:
    for item in PACKAGE.knowledge.knowledge:
        actual = explain_reveal(state, "player", item).eligible
        assert actual == _old_eligible(state, "player", item), item.id

    projector = KnowledgeProjector(max_candidates=4)
    actual_ids = tuple(item.id for item in projector._candidates(state, "player", ()))  # noqa: SLF001
    expected = [
        item
        for knowledge_id in PACKAGE.knowledge_indexes.scene_to_candidates[state.current_scene_id]
        for item in (PACKAGE.knowledge_indexes.by_id[knowledge_id],)
        if _old_eligible(state, "player", item)
    ]
    expected.sort(key=lambda item: (-item.relevance.priority, item.id))
    assert actual_ids == tuple(item.id for item in expected[:4])


def test_real_package_matches_the_old_filter_at_each_scene_entry() -> None:
    for scene in PACKAGE.scenes:
        _assert_reference_matches(_scene_state(scene.metadata.scene_id))


def test_real_package_matches_the_old_filter_after_each_storylet_fires() -> None:
    for scene in PACKAGE.scenes:
        scene_id = scene.metadata.scene_id
        for storylet in PACKAGE.storylet_routes.storylets:
            if storylet.scene_id != scene_id:
                continue
            state = _scene_state(scene_id)
            state.fired_event_ids.add(storylet.id)
            _assert_reference_matches(state)


def test_real_package_matches_the_old_filter_with_each_fact_toggled() -> None:
    for scene in PACKAGE.scenes:
        for fact_id in PACKAGE.fact_ids:
            state = _scene_state(scene.metadata.scene_id)
            state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
            _assert_reference_matches(state)


def _synthetic_state() -> RuntimeState:
    return RuntimeState.model_construct(
        package=SimpleNamespace(),
        current_scene_id="1A",
        phase="exposition",
        active_event_ids=set(),
        fired_event_ids=set(),
        facts=FactStore(),
    )


def _item(
    *,
    audience: Audience | None = None,
    requires: tuple[FactPredicate, ...] = (),
    source: RevealSource | None = None,
    establishes: tuple[RouteOperation, ...] | None = None,
) -> KnowledgeDefinition:
    return KnowledgeDefinition(
        id="k_test",
        statement="A test claim.",
        aliases=("test claim",),
        audience=audience or Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        requires=requires,
        establishes=establishes or (RouteOperation(op="assert", fact_id="test_fact", value=True),),
        source=source or RevealSource(kind="storylet_realization", storylet_id="SL-1A-A", realization_id="r1"),
    )


@pytest.mark.parametrize(
    ("reason", "setup"),
    [
        (ELIGIBLE, lambda state, item: state.active_event_ids.add("SL-1A-A")),
        (
            ALREADY_ESTABLISHED,
            lambda state, item: state.facts.assert_fact(Fact(predicate="test_fact", subject="story", value="true")),
        ),
        (NOT_VISIBLE, lambda state, item: None),
        (STORYLET_SPENT, lambda state, item: state.fired_event_ids.add("SL-1A-A")),
        (PREREQUISITE_MISSING, lambda state, item: state.active_event_ids.add("SL-1A-A")),
        (SOURCE_INACTIVE, lambda state, item: None),
    ],
)
def test_synthetic_package_covers_every_reason(reason: str, setup) -> None:
    state = _synthetic_state()
    item = _item(
        audience=Audience(kind="public", player_visible=reason != NOT_VISIBLE),
        requires=(FactPredicate(fact_id="needed_fact"),) if reason == PREREQUISITE_MISSING else (),
        source=RevealSource(
            kind="storylet_realization",
            storylet_id="SL-1A-A",
            realization_id="r1",
        )
        if reason != SOURCE_INACTIVE
        else RevealSource(kind="canonical_route_event", canonical_event_id="event"),
    )
    setup(state, item)
    result = explain_reveal(state, "player", item)
    assert result.reason == reason
    assert result.eligible is (reason == ELIGIBLE)
