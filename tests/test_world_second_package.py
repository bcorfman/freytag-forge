from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from worldkeeper import MemoryBackend, OpResult, World, WorldSchema

from bench.item_facts import package_seed
from bench.judge_input import _revealed_item_names
from storygame.audit import audit_package
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import (
    ScenePlacementRefusal,
    apply_scene_placements,
    apply_world_effects,
    world_for,
    world_schema_data,
)
from storygame.story_package.loader import StoryPackageError, load_story_package

ROOT = Path(__file__).parents[1]
STORIES = (ROOT / "data/stories/continuity-initiative", ROOT / "tests/fixtures/stories/lighthouse-keeper")


@pytest.fixture(params=STORIES, ids=lambda path: path.name)
def package(request):
    return load_story_package(request.param)


def _fact(fact_id: str) -> Fact:
    return Fact(predicate=fact_id, subject="story", value="true")


def _signature(package, facts):
    world = world_for(package, facts)
    ids = set(world.schema.entities)
    stored_facts = facts.asserted if hasattr(facts, "asserted") else facts.matching("wk_kind")
    ids.update(fact.subject for fact in stored_facts if fact.predicate == "wk_kind")
    return {
        entity_id: (
            world.parent(entity_id),
            world.relation(entity_id),
            world.is_hidden(entity_id),
            tuple(sorted(world.axis_values(entity_id).items())),
            world.conditions(entity_id),
            world.place_text(entity_id),
            world.place_label(entity_id),
            world.status(entity_id),
            world.owner(entity_id),
            world.name(entity_id),
            world.companions(entity_id),
        )
        for entity_id in sorted(ids)
    }


def _played(package):
    state = RuntimeState.bootstrap(package)
    found = "memory_card_recovered" if package.story_id == "continuity_initiative" else "brass_key_found"
    state.facts.assert_fact(_fact(found))
    apply_world_effects(package, state.facts)
    world = world_for(package, state.facts)
    area = package.scenes[0].metadata.location_id
    created = world.create("tin cup", parent=area)
    assert created.ok and created.id and created.id.startswith("n_tin_cup")
    container = "michelle_drawer" if package.story_id == "continuity_initiative" else "sea_chest"
    thing = "memory_card" if package.story_id == "continuity_initiative" else "logbook"
    assert world.set_axis(container, "open").ok
    assert world.set_conditions(thing, ["damp", "marked"]).ok
    assert world.move(thing, area).ok
    return state, created.id


def test_packages_load_schema_bootstrap_and_contents(package):
    schema = world_schema_data(package)
    assert schema["kinds"]
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    scene = package.scenes[0].metadata
    assert world.parent(package.protagonist_id) == scene.location_id
    for item_id, placement in scene.item_placements.items():
        if hasattr(placement, "parent") and placement.parent:
            assert world.parent(item_id) == placement.parent
            if placement.under:
                assert world.relation(item_id) == "under"
            if placement.text:
                assert world.place_text(item_id) == placement.text
    container = "michelle_drawer" if package.story_id == "continuity_initiative" else "sea_chest"
    for content in world.contents(container):
        assert world.resolve(world.name(content)) == content


def test_refused_protagonist_placement_is_returned_and_logged(monkeypatch, caplog):
    package = load_story_package(STORIES[1])
    original_place = World.place

    def refuse_protagonist(self, item_id, parent_id, **kwargs):
        if item_id == package.world.protagonist_id:
            return OpResult(False, reason="refused for the test")
        return original_place(self, item_id, parent_id, **kwargs)

    monkeypatch.setattr(World, "place", refuse_protagonist)
    with caplog.at_level("WARNING"):
        refusals = apply_scene_placements(package, FactStore(), "1A")

    assert refusals == (ScenePlacementRefusal("1A", "ada", "cottage", "refused for the test"),)
    assert "refused for the test" in caplog.text


def test_found_effect_and_scene_change_carry_the_hidden_item(package):
    state = RuntimeState.bootstrap(package)
    found = "memory_card_recovered" if package.story_id == "continuity_initiative" else "brass_key_found"
    hidden = "memory_card" if package.story_id == "continuity_initiative" else "brass_key"
    state.facts.assert_fact(_fact(found))
    apply_world_effects(package, state.facts)
    world = world_for(package, state.facts)
    assert world.parent(hidden) == package.protagonist_id
    assert not world.is_hidden(hidden)
    assert world.place_text(hidden)
    transition = package.pacing.transitions[0]
    from storygame.runtime.contracts import ResolvedTurnProposal, SceneTransitionProposal

    state.apply_proposal(
        ResolvedTurnProposal(
            segments=({"kind": "narration", "text": "Go to the next place."},),
            transition=SceneTransitionProposal(transition_id=transition.id),
        )
    )
    world = world_for(package, state.facts)
    assert world.area(hidden) == package.scenes[1].metadata.location_id
    assert world.area(package.protagonist_id) == package.scenes[1].metadata.location_id


def test_tree_survives_sqlite_snapshot_and_clone(package, tmp_path):
    state, created_id = _played(package)
    before = _signature(package, state.facts)
    store = RuntimeStateSqliteStore(tmp_path / "state.sqlite")
    store.save("session", state)
    restored = store.load("session", package)
    assert _signature(package, restored.facts) == before
    assert world_for(package, restored.facts).resolve("tin cup") == created_id

    snapshot = state.snapshot()
    world_for(package, state.facts).set_status(created_id, "missing")
    state.restore_snapshot(snapshot)
    assert _signature(package, state.facts) == before
    clone = state.facts.clone()
    assert _signature(package, clone) == before


def test_worldkeeper_memory_backend_matches_fact_store(package):
    schema = WorldSchema.from_data(world_schema_data(package))
    memory = World(schema, MemoryBackend())
    facts = FactStore()
    adapted = world_for(package, facts)
    for world in (memory, adapted):
        world.seed()
        world.place(package.protagonist_id, package.scenes[0].metadata.location_id)
        world.apply_effects(
            [
                {
                    "move": "memory_card" if package.story_id == "continuity_initiative" else "brass_key",
                    "parent": package.protagonist_id,
                }
            ]
        )
        world.move(package.protagonist_id, package.scenes[0].metadata.location_id)
        world.set_axis("michelle_drawer" if package.story_id == "continuity_initiative" else "sea_chest", "open")
        world.create("tin cup", parent=package.scenes[0].metadata.location_id)
    assert _signature(package, memory.backend) == _signature(package, facts)
    assert memory.parent(package.protagonist_id) == adapted.parent(package.protagonist_id)
    container = "michelle_drawer" if package.story_id == "continuity_initiative" else "sea_chest"
    assert memory.axis_values(container) == adapted.axis_values(container)


def test_narrator_bench_and_audit_boundaries(package):
    state = RuntimeState.bootstrap(package)
    provider = CloudflareTurnProvider(worker_url="offline", token="", state=state)
    hidden_name = "Michelle's memory card" if package.story_id == "continuity_initiative" else "brass key"
    assert hidden_name not in " ".join(provider._placement_rules())
    found = "memory_card_recovered" if package.story_id == "continuity_initiative" else "brass_key_found"
    state.facts.assert_fact(_fact(found))
    assert hidden_name in " ".join(provider._placement_rules())
    seeded, _ = package_seed(package, state, "1A")
    assert hidden_name not in seeded
    candidate_id = "k_sl_1a_b_r0" if package.story_id == "continuity_initiative" else "k_find_key"
    turn = {"authored_handoff_candidate_id": candidate_id, "scene_id": "1A"}
    assert hidden_name in _revealed_item_names(turn, package)
    if package.story_id == "lighthouse_keeper":
        assert audit_package(package_root(package))["scenes"] == ["1A", "1B"]


def package_root(package):
    return STORIES[1] if package.story_id == "lighthouse_keeper" else STORIES[0]


def test_loader_rejects_unknown_lighthouse_parent(tmp_path):
    root = tmp_path / "lighthouse"
    shutil.copytree(STORIES[1], root)
    path = root / "plot.md"
    path.write_text(
        path.read_text().replace(
            "parent: parlour, text: on the parlour windowsill",
            "parent: nowhere, text: on the parlour windowsill",
        ),
        encoding="utf-8",
    )
    with pytest.raises(StoryPackageError, match="unknown parent"):
        load_story_package(root)
