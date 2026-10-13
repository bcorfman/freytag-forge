from pathlib import Path

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")


def _provider():
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    apply_scene_placements(PACKAGE, state.facts, "1B")
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )


def _apply(monkeypatch, key, *, identified=False):
    provider = _provider()
    if identified:
        provider.state.facts.assert_fact(Fact(predicate="brandon_identified", subject="story", value="true"))
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request",
        lambda *_args: {"kind": {key: "person"}, "same_as": {key: "new"}},
    )
    facts, issues = provider.apply_item_facts({key: {"condition": ["knocked out"]}})
    return provider, facts, issues


def test_unnamed_man_updates_brandon_without_creating(monkeypatch):
    provider, _facts, issues = _apply(monkeypatch, "man")

    world = provider._world()
    assert world.axis_values("brandon")["conscious"] == "unconscious"
    assert not any(entity_id.startswith("item_") for entity_id in world.schema.entities)
    assert any("mapped to existing 'Brandon Corfman'; not created" in issue for issue in issues)


def test_named_brandon_allows_new_man(monkeypatch):
    provider, _facts, _issues = _apply(monkeypatch, "man", identified=True)

    world = provider._world()
    assert world.resolve("man") != "brandon"
    assert world.is_a(world.resolve("man"), "character")


def test_specific_unknown_description_allows_new_person(monkeypatch):
    provider, _facts, _issues = _apply(monkeypatch, "man in the hoodie")

    world = provider._world()
    assert world.resolve("man in the hoodie") != "brandon"
    assert world.is_a(world.resolve("man in the hoodie"), "character")


def test_unrelated_name_allows_new_person(monkeypatch):
    provider, _facts, _issues = _apply(monkeypatch, "crate")

    world = provider._world()
    assert world.resolve("crate") is not None
    assert world.resolve("crate") != "brandon"


def test_unnamed_helper_does_not_match_protagonist():
    provider = _provider()
    world = provider._world()

    assert provider._existing_unnamed_person(world, "woman") is None
