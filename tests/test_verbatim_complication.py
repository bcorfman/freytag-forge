"""Verbatim pacing realizations are delivered as authored narration."""

from __future__ import annotations

from pathlib import Path
from shutil import copytree

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import StoryPackageError, load_story_package
from storygame.story_package.models import FactPredicate, PacingEvent, PacingRealization

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)


def _state(scene_id: str = "3C", turn_index: int = 3, package=PACKAGE) -> RuntimeState:
    scene = next(item for item in package.scenes if item.metadata.scene_id == scene_id)
    return RuntimeState(
        package=package, current_scene_id=scene_id, phase=scene.metadata.freytag_phase, turn_index=turn_index
    )


def test_verbatim_text_is_appended_and_committed_when_provider_ignores_it() -> None:
    state = _state()
    state.facts.assert_fact(Fact(predicate="evidence_gap_processing_numbers", subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Keep moving."}]})
    realization = next(
        realization
        for event in PACKAGE.pacing.events
        if event.id == "collapse_3c"
        for realization in event.realizations
        if realization.verbatim
    )

    proposal = engine.turn("Keep moving toward the stairs.")

    assert proposal.segments[-1].text == realization.text
    assert proposal.segments[-1].kind == "narration"
    assert state.last_turn_delivery.complication_verbatim is True
    assert sum(segment.text == realization.text for segment in proposal.segments) == 1


def test_verbatim_complication_is_not_prompted_but_non_verbatim_is() -> None:
    state = _state()
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    state.last_turn_delivery = state.last_turn_delivery.model_copy(
        update={"complication_text": "Authored pressure.", "complication_verbatim": True}
    )
    assert not any("This happens now" in rule for rule in provider._turn_rules())

    state.last_turn_delivery = state.last_turn_delivery.model_copy(update={"complication_verbatim": False})
    assert any("This happens now" in rule for rule in provider._turn_rules())


def test_verbatim_defaults_false_and_loader_rejects_non_boolean(tmp_path: Path) -> None:
    assert PacingRealization(text="A pressure.").verbatim is False
    with pytest.raises(ValueError):
        PacingRealization(text="A pressure.", verbatim="true")  # type: ignore[arg-type]

    package_copy = tmp_path / "continuity-initiative"
    copytree(PACKAGE_ROOT, package_copy)
    pacing = package_copy / "pacing.yaml"
    pacing.write_text(pacing.read_text().replace("verbatim: true", 'verbatim: "true"', 1))
    with pytest.raises(StoryPackageError):
        load_story_package(package_copy)


def test_continuity_gap_realizations_are_verbatim_but_defaults_are_not() -> None:
    expected = {
        "collapse_3c": {"evidence_gap_processing_numbers", "evidence_gap_development_record"},
        "routes_collapse_3c": {"evidence_gap_marked_site_list", "evidence_gap_copy_check"},
    }
    for event_id, gap_ids in expected.items():
        event = next(event for event in PACKAGE.pacing.events if event.id == event_id)
        assert [realization.verbatim for realization in event.realizations] == [True, True, False]
        assert {realization.when[0].fact_id for realization in event.realizations if realization.verbatim} == gap_ids


def test_collision_spends_event_without_emitting_gap_line() -> None:
    competing = PacingEvent(
        id="competing_3c_complication",
        scene_id="3C",
        at_turn=4,
        effects=(FactPredicate(fact_id="competing_3c_pressure", equals=True),),
        realizations=(PacingRealization(text="The competing complication takes the foreground."),),
    )
    package = PACKAGE.model_copy(
        update={"pacing": PACKAGE.pacing.model_copy(update={"events": (competing, *PACKAGE.pacing.events)})}
    )
    state = _state(package=package)
    state.facts.assert_fact(Fact(predicate="evidence_gap_processing_numbers", subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Keep moving."}]})

    proposal = engine.turn("Keep moving toward the stairs.")

    collapse = next(event for event in package.pacing.events if event.id == "collapse_3c")
    assert state.last_turn_delivery.complication_text == competing.realizations[0].text
    assert state.last_turn_delivery.complication_verbatim is False
    assert collapse.realizations[0].text not in " ".join(segment.text for segment in proposal.segments)
    assert "collapse_3c" in state.fired_event_ids
