from __future__ import annotations

from pathlib import Path

from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def fact(predicate: str, subject: str = "story", value: str = "true") -> Fact:
    return Fact(predicate=predicate, subject=subject, value=value)


def test_index_tracks_assert_retract_and_direct_replacement() -> None:
    first = fact("lead_known")
    second = fact("lead_known", "rebecca")
    store = FactStore(asserted={first})

    assert store.matching("lead_known") == (first,)
    store.assert_fact(second)
    assert store.matching("lead_known", "rebecca") == (second,)

    store.retract_fact(first)
    assert store.matching("lead_known") == (second,)

    replacement = fact("other_fact")
    store.asserted = {replacement}
    assert store.matching("lead_known") == ()
    assert store.matching("other_fact") == (replacement,)


def test_index_is_independent_through_clone_and_pydantic_round_trips() -> None:
    original = FactStore(asserted={fact("z_fact"), fact("a_fact")})

    clone = original.clone()
    clone.assert_fact(fact("clone_only"))
    assert original.matching("clone_only") == ()
    assert clone.matching("clone_only") == (fact("clone_only"),)

    restored = FactStore.model_validate(original.model_dump(mode="json"))
    json_restored = FactStore.model_validate_json(original.model_dump_json())
    assert restored.matching("a_fact") == original.matching("a_fact")
    assert json_restored.matching("z_fact") == original.matching("z_fact")


def test_snapshot_restore_rebuilds_the_fact_index() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    snapshot = state.snapshot()
    temporary = fact("temporary_fact")
    state.facts.assert_fact(temporary)
    assert state.facts.matching("temporary_fact") == (temporary,)

    state.restore_snapshot(snapshot)

    assert state.facts.matching("temporary_fact") == ()
    restored = fact("restored_fact")
    state.facts.assert_fact(restored)
    assert state.facts.matching("restored_fact") == (restored,)
