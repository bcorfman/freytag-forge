from __future__ import annotations

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector, RevealCandidate
from storygame.runtime.reveal_eligibility import (
    ALREADY_ESTABLISHED,
    ELIGIBLE,
    NOT_REACHABLE,
    NOT_VISIBLE,
    PREREQUISITE_MISSING,
    SOURCE_INACTIVE,
    STORYLET_SPENT,
    explain_reveal,
)
from storygame.runtime.state import RuntimeState
from storygame.story_package.models import (
    Audience,
    FactDefinition,
    FactPredicate,
    KnowledgeDefinition,
    RevealSource,
    RouteOperation,
    RouteRealization,
    Storylet,
    StoryletRoute,
)
from tests.test_observation_preview import _synthetic_package

FACT_ID = "repeatable_fact"
SOURCE_ID = "SL-1A-A"


def _item(
    *,
    repeatable: bool = False,
    audience: Audience | None = None,
    requires: tuple[FactPredicate, ...] = (),
    reach_entity_ids: tuple[str, ...] = (),
    source: RevealSource | None = None,
) -> KnowledgeDefinition:
    return KnowledgeDefinition(
        id="repeatable_claim",
        statement="The synthetic object has a useful detail.",
        entity_ids=("lens",),
        reach_entity_ids=reach_entity_ids,
        aliases=("useful detail",),
        audience=audience or Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        requires=requires,
        establishes=(RouteOperation(op="assert", fact_id=FACT_ID, value=True),),
        source=source or RevealSource(kind="storylet_realization", storylet_id=SOURCE_ID, realization_id="r1"),
        action_evidence=(("inspect",), ("object",)),
        delivery_text="The synthetic object has a useful detail.",
        repeatable=repeatable,
    )


def _package(item: KnowledgeDefinition):
    base = _synthetic_package()
    world = base.world.model_copy(update={"facts": (*base.world.facts, FACT_ID, "needed_fact")})
    catalog = base.knowledge.model_copy(
        update={
            "facts": (
                *base.knowledge.facts,
                FactDefinition(id=FACT_ID, purpose="repeatable test"),
                FactDefinition(id="needed_fact", purpose="test requirement"),
            ),
            "knowledge": (item,),
        }
    )
    route = StoryletRoute(
        id=SOURCE_ID,
        scene_id="1A",
        title="Synthetic route",
        earliest_turn=0,
        target_turn=0,
        latest_turn=99,
        pressure_role="test",
        realizations=(
            RouteRealization(
                id="r1",
                dramatic_intent="test",
                operations=item.establishes,
            ),
        ),
    )
    storylet = Storylet(
        id=SOURCE_ID,
        scene_id="1A",
        title="Synthetic storylet",
        source_links=("opening",),
        sections={"opening": "A synthetic storylet."},
        earliest_turn=0,
        target_turn=0,
        latest_turn=99,
    )
    routes = base.storylet_routes.model_copy(update={"storylets": (route,)})
    indexes = base.knowledge_indexes.model_copy(
        update={
            "by_id": {item.id: item},
            "facts_to_knowledge": {FACT_ID: (item.id,)},
            "source_to_knowledge": {f"storylet:{SOURCE_ID}:r1": (item.id,)},
            "scene_to_candidates": {"1A": (item.id,)},
        }
    )
    return base.model_copy(
        update={
            "world": world,
            "knowledge": catalog,
            "knowledge_indexes": indexes,
            "storylets": (storylet,),
            "storylet_routes": routes,
        }
    )


def _state(item: KnowledgeDefinition) -> RuntimeState:
    state = RuntimeState.bootstrap(_package(item))
    state.active_event_ids.add(SOURCE_ID)
    return state


def _establish(state: RuntimeState) -> None:
    state.facts.assert_fact(Fact(predicate=FACT_ID, subject="story", value="true"))


def test_repeatable_defaults_false_and_false_entries_stay_spent_or_established_ineligible() -> None:
    item = _item()
    assert item.repeatable is False
    assert "repeatable" not in item.model_dump()

    established_state = _state(item)
    _establish(established_state)
    assert explain_reveal(established_state, "player", item).reason == ALREADY_ESTABLISHED

    spent_state = _state(item)
    spent_state.fired_event_ids.add(SOURCE_ID)
    assert explain_reveal(spent_state, "player", item).reason == STORYLET_SPENT


def test_repeatable_entry_remains_eligible_after_establishment_spending_and_source_inactivation() -> None:
    item = _item(repeatable=True)
    state = _state(item)
    _establish(state)
    state.fired_event_ids.add(SOURCE_ID)
    state.active_event_ids.remove(SOURCE_ID)

    result = explain_reveal(state, "player", item)

    assert result.eligible
    assert result.reason == ELIGIBLE


def test_repeatable_entry_with_unestablished_effects_is_ineligible_when_source_is_inactive() -> None:
    item = _item(repeatable=True)
    state = _state(item)
    state.active_event_ids.remove(SOURCE_ID)

    result = explain_reveal(state, "player", item)

    assert not result.eligible
    assert result.reason == SOURCE_INACTIVE


def test_repeatable_entry_with_unestablished_effects_is_ineligible_when_storylet_is_spent() -> None:
    item = _item(repeatable=True)
    state = _state(item)
    state.fired_event_ids.add(SOURCE_ID)

    result = explain_reveal(state, "player", item)

    assert not result.eligible
    assert result.reason == STORYLET_SPENT


def test_repeatable_entry_is_eligible_when_another_route_established_its_effects() -> None:
    item = _item(repeatable=True)
    state = _state(item)
    _establish(state)
    state.active_event_ids.remove(SOURCE_ID)

    result = explain_reveal(state, "player", item)

    assert result.eligible
    assert result.reason == ELIGIBLE


def test_non_repeatable_entry_still_requires_an_active_source() -> None:
    item = _item()
    state = _state(item)
    state.active_event_ids.remove(SOURCE_ID)

    result = explain_reveal(state, "player", item)

    assert not result.eligible
    assert result.reason == SOURCE_INACTIVE


@pytest.mark.parametrize(
    ("item", "audience_id", "expected"),
    [
        (
            _item(repeatable=True, requires=(FactPredicate(fact_id="needed_fact", equals=True),)),
            "player",
            PREREQUISITE_MISSING,
        ),
        (_item(repeatable=True, reach_entity_ids=("remote_marker",)), "player", NOT_REACHABLE),
        (_item(repeatable=True, audience=Audience(kind="public", player_visible=False)), "player", NOT_VISIBLE),
    ],
)
def test_repeatable_entry_still_obeys_requires_reach_and_audience(item, audience_id: str, expected: str) -> None:
    state = _state(item)
    _establish(state)
    state.fired_event_ids.add(SOURCE_ID)
    state.active_event_ids.remove(SOURCE_ID)

    result = explain_reveal(state, audience_id, item)

    assert result.reason == expected
    assert not result.eligible


def test_repeatable_entry_survives_cloudflare_established_filter() -> None:
    item = _item(repeatable=True)
    state = _state(item)
    _establish(state)
    state.fired_event_ids.add(SOURCE_ID)
    state.active_event_ids.remove(SOURCE_ID)
    candidate = RevealCandidate(
        id=item.id,
        statement=item.statement,
        must_convey=item.must_convey,
        action_evidence=item.action_evidence,
        delivery_text=item.delivery_text,
    )
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    assert provider._eligible_reveal_candidates((candidate,)) == (candidate,)
    assert KnowledgeProjector()._candidates(state, "player", ()) == (candidate,)  # noqa: SLF001


class _ScriptedProvider(CloudflareTurnProvider):
    def _dispatch(self, _system: str, _context: dict[str, object]) -> object:
        response = {
            "segments": [{"kind": "narration", "text": "The room remains quiet."}],
            "selected_knowledge_ids": [],
        }
        return self._accept_proposal(response, parse_turn_proposal(response))


def test_repeatable_entry_delivers_three_times_through_the_engine() -> None:
    item = _item(repeatable=True)
    state = _state(item)
    provider = _ScriptedProvider(worker_url="", token="", state=state)
    engine = RuntimeEngine(state, provider)

    results = [engine.turn("Inspect the object.") for _ in range(3)]

    for result in results:
        assert [segment.text for segment in result.segments].count(item.delivery_text) == 1
    assert Fact(predicate=FACT_ID, subject="story", value="true") in state.facts.asserted
    assert state.fired_event_ids == {SOURCE_ID}
