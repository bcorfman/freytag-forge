from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.contracts import FactOperation, NarrationSegment, ResolvedTurnProposal, StoryEventProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProgressionValidator, ProposalValidationError
from storygame.runtime.world_model import (
    WORLD_EFFECTS_APPLIED,
    WorldEffectRefusal,
    apply_world_effects,
    world_for,
    world_schema_data,
)
from storygame.story_package.loader import StoryPackageError, load_story_package
from storygame.story_package.models import WorldEffect

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)


def effect_package(*effects: dict) -> object:
    fact_id = "facility_proof"
    world = PACKAGE.world.model_copy(
        update={"fact_effects": {fact_id: tuple(WorldEffect.model_validate(effect) for effect in effects)}}
    )
    return PACKAGE.model_copy(update={"world": world})


def asserted(fact_id: str, value: str = "true") -> Fact:
    return Fact(predicate=fact_id, subject="story", value=value)


@pytest.mark.component
def test_world_schema_data_is_plain_and_covers_authored_entities() -> None:
    data = world_schema_data(PACKAGE)

    def plain(value):
        assert value is None or isinstance(value, (dict, list, str, bool, int))
        if isinstance(value, dict):
            for child in value.values():
                plain(child)
        elif isinstance(value, list):
            for child in value:
                plain(child)

    plain(data)
    entities = {entity["id"]: entity for entity in data["entities"]}
    assert {entity["kind"] for entity in entities.values()} == {
        "area",
        "character",
        "thing",
        "container",
        "vehicle",
        "desk",
    }
    for entity in PACKAGE.world.locations:
        assert entities[entity.id]["kind"] == "area"
    for entity in PACKAGE.world.npcs:
        assert entities[entity.id]["kind"] == "character"
    for item in PACKAGE.world.items:
        assert entities[item.id]["kind"] == item.kind
        if item.fixed is None:
            assert "fixed" not in entities[item.id]
        else:
            assert entities[item.id]["fixed"] is item.fixed


@pytest.mark.component
def test_world_for_uses_the_given_fact_store() -> None:
    facts = FactStore()
    world = world_for(PACKAGE, facts)
    world.seed()

    assert world.backend is facts


@pytest.mark.component
def test_bootstrap_seeds_world_facts() -> None:
    state = RuntimeState.bootstrap(PACKAGE)

    assert any(fact.predicate.startswith("wk_") for fact in state.facts.asserted)


@pytest.mark.component
def test_every_world_effect_shape_is_applied() -> None:
    package = effect_package(
        {"move": "memory_card", "parent": "mcgehee_home"},
        {"move": "memory_card", "parent": "n_test_box_1", "under": True},
        {"reveal": "memory_card"},
        {"accompany": "michelle", "with": "kristin"},
        {"set_axis": "kristin", "value": "captive"},
    )
    facts = FactStore(asserted={asserted("facility_proof")})
    world = world_for(package, facts)
    world.seed()
    assert world.create("test box", "mcgehee_home", kind="container").ok

    refusals = apply_world_effects(package, facts)

    assert not refusals
    assert world_for(package, facts).parent("memory_card") == "n_test_box_1"
    assert world_for(package, facts).relation("memory_card") == "under"
    assert world_for(package, facts).companions("kristin") == ("michelle",)
    assert world_for(package, facts).axis_values("kristin")["captive"] == "captive"


@pytest.mark.component
def test_world_effects_apply_once_and_mark_the_fact() -> None:
    package = effect_package({"move": "memory_card", "parent": "los_angeles_park"})
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(asserted("facility_proof"))

    assert apply_world_effects(package, state.facts) == ()
    state_world = world_for(package, state.facts)
    assert state_world.parent("memory_card") == "los_angeles_park"
    assert Fact(predicate=WORLD_EFFECTS_APPLIED, subject="story", object="facility_proof") in state.facts.asserted

    state_world.reveal("memory_card")
    assert state_world.move("memory_card", "regional_facility").ok
    assert apply_world_effects(package, state.facts) == ()
    assert world_for(package, state.facts).parent("memory_card") == "regional_facility"


@pytest.mark.component
def test_refused_effect_is_logged_and_marked(caplog) -> None:
    package = effect_package({"set_axis": "kristin", "value": "not-an-axis"})
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(asserted("facility_proof"))

    with caplog.at_level("WARNING"):
        refusals = apply_world_effects(package, state.facts)

    assert len(refusals) == 1
    assert isinstance(refusals[0], WorldEffectRefusal)
    assert "world effect refused" in caplog.text
    assert Fact(predicate=WORLD_EFFECTS_APPLIED, subject="story", object="facility_proof") in state.facts.asserted


@pytest.mark.component
def test_runtime_state_apply_proposal_applies_asserted_world_effects() -> None:
    package = effect_package({"move": "memory_card", "parent": "los_angeles_park"})
    state = RuntimeState.bootstrap(package)
    proposal = ResolvedTurnProposal(
        segments=(NarrationSegment(kind="narration", text="The evidence shifts."),),
        operations=(FactOperation(operation="assert", fact=asserted("facility_proof")),),
    )

    state.apply_proposal(proposal)
    assert world_for(package, state.facts).parent("memory_card") == "los_angeles_park"


@pytest.mark.component
def test_pacing_applies_effects_from_fact_asserted_directly() -> None:
    package = effect_package({"move": "memory_card", "parent": "los_angeles_park"})
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(asserted("facility_proof"))

    RuntimeEngine(state, lambda _: {})._activate_pacing()
    assert world_for(package, state.facts).parent("memory_card") == "los_angeles_park"


@pytest.mark.component
def test_canonical_route_path_applies_world_effects(monkeypatch) -> None:
    package = effect_package({"move": "memory_card", "parent": "los_angeles_park"})
    package = package.model_copy(
        update={
            "storylet_routes": package.storylet_routes.model_copy(update={"bridge_events": (), "resolution_events": ()})
        }
    )
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(asserted("facility_proof"))
    engine = RuntimeEngine(state, lambda _: {})

    engine._apply_canonical_route_events()

    assert world_for(package, state.facts).parent("memory_card") == "los_angeles_park"


@pytest.mark.component
def test_world_facts_and_effect_markers_survive_sqlite_save_load(tmp_path) -> None:
    package = effect_package({"move": "memory_card", "parent": "los_angeles_park"})
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(asserted("facility_proof"))
    apply_world_effects(package, state.facts)
    store = RuntimeStateSqliteStore(tmp_path / "state.sqlite")
    store.save("session", state)

    restored = store.load("session", package)

    assert any(fact.predicate.startswith("wk_") for fact in restored.facts.asserted)
    assert Fact(predicate=WORLD_EFFECTS_APPLIED, subject="story", object="facility_proof") in restored.facts.asserted
    assert world_for(package, restored.facts).parent("memory_card") == "los_angeles_park"


@pytest.mark.component
@pytest.mark.parametrize("predicate", ["wk_parent", WORLD_EFFECTS_APPLIED])
def test_provider_rejects_world_fact_mutations(predicate: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    validator = ProgressionValidator(PACKAGE)
    fact = Fact(predicate=predicate, subject="story", value="true")
    operation = FactOperation(operation="assert", fact=fact)
    proposal = ResolvedTurnProposal(
        segments=(NarrationSegment(kind="narration", text="No change."),),
        operations=(operation,),
    )

    with pytest.raises(ProposalValidationError, match="world facts") as proposal_error:
        validator.validate_effects(state, proposal)
    assert proposal_error.value.code == "world_fact_mutation"

    route = PACKAGE.storylet_routes.storylets[0]
    state.active_event_ids.add(route.id)
    realization = route.realizations[0]
    event = StoryEventProposal(event_id=route.id, realization_id=realization.id, operations=(operation,))
    event_proposal = ResolvedTurnProposal(
        segments=(NarrationSegment(kind="narration", text="No change."),),
        events=(event,),
    )
    with pytest.raises(ProposalValidationError, match="world facts") as event_error:
        validator.validate_effects(state, event_proposal)
    assert event_error.value.code == "world_fact_mutation"


def copy_package(tmp_path: Path) -> Path:
    root = tmp_path / "story"
    shutil.copytree(PACKAGE_ROOT, root)
    return root


@pytest.mark.component
def test_loader_reads_on_assert_effects_and_rejects_bad_world_effects(tmp_path) -> None:
    root = copy_package(tmp_path)
    world_path = root / "world.yaml"
    data = yaml.safe_load(world_path.read_text())
    fact_id = data["facts"][0]
    data["facts"][0] = {"id": fact_id, "on_assert": [{"move": "memory_card", "parent": "los_angeles_park"}]}
    world_path.write_text(yaml.safe_dump(data, sort_keys=False))
    package = load_story_package(root)
    assert package.world.facts == PACKAGE.world.facts
    assert all(isinstance(fact, str) for fact in package.world.facts)
    assert package.world.fact_effects[fact_id][0].move == "memory_card"

    unknown_root = copy_package(tmp_path / "unknown")
    unknown_path = unknown_root / "world.yaml"
    unknown_data = yaml.safe_load(unknown_path.read_text())
    unknown_data["facts"][0] = {"id": fact_id, "on_assert": [{"move": "not_an_entity", "parent": "los_angeles_park"}]}
    unknown_path.write_text(yaml.safe_dump(unknown_data, sort_keys=False))
    with pytest.raises(StoryPackageError, match="unknown entity"):
        load_story_package(unknown_root)

    for index, bad_effect in enumerate(
        ({"teleport": "memory_card"}, {"move": "memory_card"}, {"reveal": "memory_card", "under": True})
    ):
        bad_root = copy_package(tmp_path / f"bad-{index}")
        bad_path = bad_root / "world.yaml"
        bad_data = yaml.safe_load(bad_path.read_text())
        bad_data["facts"][0] = {"id": fact_id, "on_assert": [bad_effect]}
        bad_path.write_text(yaml.safe_dump(bad_data, sort_keys=False))
        with pytest.raises(StoryPackageError):
            load_story_package(bad_root)


@pytest.mark.component
def test_shipped_package_declares_no_world_effects() -> None:
    assert set(PACKAGE.world.fact_effects) == {"memory_card_recovered"}
