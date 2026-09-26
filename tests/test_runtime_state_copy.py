"""Runtime state copy behavior."""

from copy import deepcopy
from pathlib import Path

from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState, TurnRecord
from storygame.story_package.loader import load_story_package


def test_deepcopy_shares_the_package() -> None:
    state = RuntimeState.bootstrap(load_story_package(Path("data/stories/continuity-initiative")))

    assert deepcopy(state).package is state.package
    assert state.model_copy(deep=True).package is state.package


def test_deepcopy_isolates_mutable_state() -> None:
    state = RuntimeState.bootstrap(load_story_package(Path("data/stories/continuity-initiative")))
    copied = deepcopy(state)
    fact = Fact(predicate="copy_isolated", subject="story", value="true")

    copied.facts.assert_fact(fact)
    copied.turn_records.append(TurnRecord(id="copy-isolated"))
    copied.active_event_ids.add("copy-isolated")

    assert fact not in state.facts.asserted
    assert state.turn_records == []
    assert "copy-isolated" not in state.active_event_ids
