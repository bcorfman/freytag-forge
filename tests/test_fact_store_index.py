from __future__ import annotations

from pathlib import Path

from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.knowledge import knowledge_guards_for
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
    assert isinstance(store.asserted, set)
    assert store.matching("lead_known") == ()
    assert store.matching("other_fact") == (replacement,)


def test_boolean_assertion_replaces_true_with_false_and_updates_index() -> None:
    true_fact = fact("patrol_in_house", value="true")
    false_fact = fact("patrol_in_house", value="false")
    store = FactStore()

    store.assert_fact(true_fact)
    version_before_flip = store.version
    store.assert_fact(false_fact)

    assert store.asserted == {false_fact}
    assert store.matching("patrol_in_house", "story") == (false_fact,)
    assert store.version == version_before_flip + 2


def test_boolean_assertion_replaces_false_with_true_and_updates_index() -> None:
    false_fact = fact("patrol_in_house", value="false")
    true_fact = fact("patrol_in_house", value="true")
    store = FactStore()

    store.assert_fact(false_fact)
    version_before_flip = store.version
    store.assert_fact(true_fact)

    assert store.asserted == {true_fact}
    assert store.matching("patrol_in_house", "story") == (true_fact,)
    assert store.version == version_before_flip + 2


def test_reasserting_the_same_boolean_fact_is_idempotent() -> None:
    asserted = fact("patrol_in_house", value="true")
    store = FactStore()

    store.assert_fact(asserted)
    version_after_first_assertion = store.version
    store.assert_fact(asserted)

    assert store.asserted == {asserted}
    assert store.version == version_after_first_assertion


def test_non_boolean_fact_values_are_not_retracted() -> None:
    pending = fact("case_status", value="pending")
    complete = fact("case_status", value="complete")
    store = FactStore()

    store.assert_fact(pending)
    store.assert_fact(complete)

    assert set(store.matching("case_status", "story")) == {pending, complete}


def test_boolean_facts_for_different_subjects_do_not_replace_each_other() -> None:
    story_fact = fact("patrol_in_house", "story", "true")
    rebecca_false = fact("patrol_in_house", "rebecca", "false")
    rebecca_true = fact("patrol_in_house", "rebecca", "true")
    store = FactStore(asserted={story_fact, rebecca_false})

    store.assert_fact(rebecca_true)

    assert store.matching("patrol_in_house", "story") == (story_fact,)
    assert store.matching("patrol_in_house", "rebecca") == (rebecca_true,)


def test_clone_and_model_copy_keep_boolean_replacement_indexes_working() -> None:
    true_fact = fact("patrol_in_house", value="true")
    false_fact = fact("patrol_in_house", value="false")
    original = FactStore(asserted={true_fact})
    clone = original.clone()
    copied = original.model_copy()

    clone.assert_fact(false_fact)
    copied.assert_fact(false_fact)

    assert original.matching("patrol_in_house", "story") == (true_fact,)
    assert clone.matching("patrol_in_house", "story") == (false_fact,)
    assert copied.matching("patrol_in_house", "story") == (false_fact,)


def test_in_place_asserted_mutations_rebuild_index_and_invalidate_guards() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    added = fact("added_fact")
    guards_before = knowledge_guards_for(state)
    version_before = state.facts.version

    state.facts.asserted.add(added)

    assert state.facts.matching("added_fact") == (added,)
    assert state.facts.version == version_before + 1
    guards_after_add = knowledge_guards_for(state)
    assert guards_after_add is not guards_before

    state.facts.asserted.discard(added)

    assert state.facts.matching("added_fact") == ()
    assert state.facts.version == version_before + 2
    assert knowledge_guards_for(state) is not guards_after_add


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
