"""Phase-3 read-only runtime narrative package and selector coverage."""

from __future__ import annotations

import pytest

from storygame.authoring.causal_contracts import validate_causal_compiled_story
from storygame.authoring.compiler import _causal_story_as_compiled_story, load_runtime_narrative_fixture
from storygame.persistence.runtime_state_sqlite import RuntimeStateSqliteStore
from storygame.runtime.context import RuntimeContextBuilder
from storygame.runtime.contracts import RuntimeFailure, StoryletRealization, TurnResult
from storygame.runtime.facts import Fact
from storygame.runtime.narrative import RuntimeNarrativeProjection, StoryletSelector, narrative_package_from_story
from storygame.runtime.state import bootstrap_runtime_state, runtime_state_bytes
from storygame.runtime.validation import validate_and_commit
from tests.test_storylet_contract_phase1 import _storylet_story


def _projection(*, tied: bool = False) -> RuntimeNarrativeProjection:
    raw = _storylet_story()
    if tied:
        raw["storylets"][0]["priority"] = 60  # type: ignore[index]
    story = validate_causal_compiled_story(raw)
    return RuntimeNarrativeProjection(_causal_story_as_compiled_story(story), narrative_package_from_story(story))


def _eligible_state():
    state = bootstrap_runtime_state(_projection())
    state.world.location = "relay"
    state.facts.retract_fact(Fact(predicate="at", subject="player", object="dock"))
    state.facts.assert_fact(Fact(predicate="at", subject="player", object="relay"))
    state.facts.assert_fact(Fact(predicate="present", subject="engineer", object="relay"))
    state.facts.assert_fact(Fact(predicate="knows", subject="player", object="failure"))
    state.facts.retract_fact(Fact(predicate="scene_pressure", subject="scene", value="0"))
    state.facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value="20"))
    for beat_id in ("setup", "rise"):
        state.beat_runtime[beat_id].completed_tags.add(f"{beat_id}_completed")
    return state


def test_selector_is_deterministic_read_only_and_filters_location_presence_and_completion() -> None:
    state = _eligible_state()
    before = runtime_state_bytes(state)
    selector = StoryletSelector(state.narrative_package, state.facts)

    selected = selector.select(active_beat_ids=("crisis",), location_id="relay")

    assert [storylet.id for storylet in selected] == ["engineer_faces_cost", "crew_debates_cost"]
    assert runtime_state_bytes(state) == before
    state.facts.retract_fact(Fact(predicate="storylet_completed", subject="engineer_faces_cost", value="false"))
    state.facts.assert_fact(Fact(predicate="storylet_completed", subject="engineer_faces_cost", value="true"))
    assert [storylet.id for storylet in selector.select(active_beat_ids=("crisis",), location_id="relay")] == [
        "crew_debates_cost"
    ]


def test_selector_breaks_ties_by_id_and_deprioritizes_recently_used_storylets() -> None:
    state = bootstrap_runtime_state(_projection(tied=True))
    state.world.location = "relay"
    state.facts.assert_fact(Fact(predicate="present", subject="engineer", object="relay"))
    state.facts.assert_fact(Fact(predicate="knows", subject="player", object="failure"))
    state.facts.retract_fact(Fact(predicate="scene_pressure", subject="scene", value="0"))
    state.facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value="20"))
    selector = StoryletSelector(state.narrative_package, state.facts)
    assert [item.id for item in selector.select(active_beat_ids=("crisis",), location_id="relay")] == [
        "crew_debates_cost",
        "engineer_faces_cost",
    ]
    state.facts.retract_fact(Fact(predicate="storylet_recently_used", subject="crew_debates_cost", value="false"))
    state.facts.assert_fact(Fact(predicate="storylet_recently_used", subject="crew_debates_cost", value="true"))
    assert [item.id for item in selector.select(active_beat_ids=("crisis",), location_id="relay")] == [
        "engineer_faces_cost",
        "crew_debates_cost",
    ]


def test_context_exposes_only_eligible_opportunities_and_keeps_freeform_available() -> None:
    state = _eligible_state()

    payload = RuntimeContextBuilder().build(state, "I try an unrelated idea.").payload

    opportunity = payload["narrative_opportunities"]
    assert opportunity["freeform_allowed"] is True
    assert [item["id"] for item in opportunity["storylets"]] == [
        "engineer_faces_cost",
        "crew_debates_cost",
    ]
    assert "tradeoff" not in str(opportunity)
    state.facts.assert_fact(Fact(predicate="knows", subject="engineer", object="tradeoff"))
    assert "tradeoff" not in str(RuntimeContextBuilder().build(state, "Wait.").payload["facts"])
    state.facts.retract_fact(Fact(predicate="present", subject="engineer", object="relay"))
    assert RuntimeContextBuilder().build(state, "Wait.").payload["narrative_opportunities"]["storylets"] == []


def test_runtime_bootstrap_remains_cross_genre_compatible() -> None:
    for genre in ("mystery", "fantasy", "sci-fi", "relationship"):
        state = bootstrap_runtime_state(load_runtime_narrative_fixture(genre))
        assert state.facts.has("at", "player", state.world.location)
    mystery = bootstrap_runtime_state(load_runtime_narrative_fixture("mystery"))
    assert mystery.narrative_package is not None
    assert len(mystery.narrative_package.reviewed_candidate_sha256 or "") == 64


def _realization(**changes: object) -> StoryletRealization:
    values: dict[str, object] = {
        "storylet_id": "engineer_faces_cost",
        "realization_mode": "negotiation",
        "consequence_ids": ("commit_repair",),
        "completion_evidence": ("tradeoff",),
    }
    values.update(changes)
    return StoryletRealization(**values)


def test_storylet_realization_commits_declared_consequences_and_completion_atomically() -> None:
    state = _eligible_state()

    committed = validate_and_commit(
        state,
        TurnResult(narration="The engineer accepts the costly repair.", storylet_realization=_realization()),
    )

    assert committed.facts.has("knows", "player", "tradeoff")
    assert committed.facts.has("storylet_completed", "engineer_faces_cost", value="true")
    assert committed.facts.has("storylet_recently_used", "engineer_faces_cost", value="true")
    assert not state.facts.has("knows", "player", "tradeoff")


@pytest.mark.parametrize(
    "changes, code",
    [
        ({"storylet_id": "unknown"}, "UNKNOWN_STORYLET"),
        ({"realization_mode": "travel"}, "INVALID_STORYLET_MODE"),
        ({"consequence_ids": ("unknown",)}, "UNKNOWN_STORYLET_CONSEQUENCE"),
        ({"completion_evidence": ("failure",)}, "INVALID_STORYLET_COMPLETION"),
    ],
)
def test_storylet_realization_rejects_unknown_or_unauthorized_declarations(
    changes: dict[str, object], code: str
) -> None:
    state = _eligible_state()
    before = runtime_state_bytes(state)

    with pytest.raises(RuntimeFailure) as error:
        validate_and_commit(
            state,
            TurnResult(narration="An invalid dramatic claim.", storylet_realization=_realization(**changes)),
        )

    assert error.value.code == code
    assert runtime_state_bytes(state) == before


def test_ineligible_storylet_and_freeform_turn_preserve_fact_authority() -> None:
    state = _eligible_state()
    state.facts.retract_fact(Fact(predicate="present", subject="engineer", object="relay"))
    before = runtime_state_bytes(state)

    with pytest.raises(RuntimeFailure, match="ineligible"):
        validate_and_commit(
            state,
            TurnResult(narration="The absent engineer decides.", storylet_realization=_realization()),
        )

    assert runtime_state_bytes(state) == before
    freeform = validate_and_commit(state, TurnResult(narration="You wait and watch the empty relay."))
    assert runtime_state_bytes(freeform) == before


def test_aborted_storylet_opens_declared_failure_forward_opportunity() -> None:
    state = _eligible_state()

    committed = validate_and_commit(
        state,
        TurnResult(
            narration="The engineer refuses, forcing the crew to talk it through.",
            storylet_realization=_realization(consequence_ids=(), completion_evidence=(), abort_evidence=("failure",)),
        ),
    )

    assert committed.facts.has("storylet_aborted", "engineer_faces_cost", value="true")
    assert committed.facts.has("storylet_discovered", "crew_debates_cost", value="true")


def test_storylet_selection_facts_survive_integrity_checked_save_load(tmp_path) -> None:
    state = validate_and_commit(
        _eligible_state(),
        TurnResult(narration="The engineer accepts the costly repair.", storylet_realization=_realization()),
    )
    store = RuntimeStateSqliteStore(tmp_path / "runtime.sqlite", namespace="test")
    try:
        store.save("session", state)
        restored = store.load("session", _projection())
    finally:
        store.close()

    assert restored.facts.has("storylet_completed", "engineer_faces_cost", value="true")
    assert restored.facts.has("storylet_recently_used", "engineer_faces_cost", value="true")
