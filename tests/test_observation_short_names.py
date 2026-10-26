from __future__ import annotations

from worldkeeper import MemoryBackend, World, WorldSchema

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest, build_observation_context
from storygame.runtime.observation_verifier import _question_for, relations_from_context
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.models import Npc
from tests.test_observation_mode import PACKAGE, _state_at
from tests.test_observation_preview import _synthetic_package


def _strings(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        return tuple(text for item in value.values() for text in _strings(item))
    if isinstance(value, (list, tuple)):
        return tuple(text for item in value for text in _strings(item))
    return ()


def _provider(state: RuntimeState, request: ObservationRequest) -> ItemFactsProvider:
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.observation_request = request
    return provider


def _artifacts(state: RuntimeState, request: ObservationRequest):
    provider = _provider(state, request)
    world = world_for(state.package, state.facts)
    context = provider._observation_context(world)
    assert context is not None
    return world, provider, context, provider._section_user_prompt({"scene_setting": {}})


def _assert_holder_projection(state: RuntimeState, item_id: str, full_name: str, short_name: str) -> None:
    request = ObservationRequest("Inspect the item.", "look", item_id)
    world, _provider_instance, context, prompt = _artifacts(state, request)
    item = next(thing for thing in context.visible_things if thing.name == world.name(item_id))
    relation = next(relation for relation in relations_from_context(context) if relation.thing == item.name)
    question = " ".join(_strings(_question_for(relation)))

    assert context.observer == short_name
    assert item.place == short_name
    assert item.holder == short_name
    assert f"Held by: {short_name}." in prompt
    assert f"Held by: {full_name}." not in prompt
    assert relation.holder == short_name
    assert short_name in question
    assert full_name not in question


def test_shipped_story_uses_short_protagonist_name_in_observation_path() -> None:
    state = _state_at("outside_house", already_aboard=True)
    world = world_for(PACKAGE, state.facts)
    protagonist = next(npc for npc in PACKAGE.world.npcs if npc.id == PACKAGE.world.protagonist_id)
    short_name = min((*protagonist.aliases, protagonist.name), key=len)
    full_name = world.name(PACKAGE.world.protagonist_id)
    assert world.move("kristin_laptop", PACKAGE.world.protagonist_id).ok

    _world, _provider_instance, context, prompt = _artifacts(
        state,
        ObservationRequest("Examine my laptop.", "look", "kristin_laptop"),
    )
    laptop = next(thing for thing in context.visible_things if thing.name == "Kristin's laptop")
    relation = relations_from_context(context)[0]
    question = " ".join(_strings(_question_for(relation)))

    assert short_name != full_name
    assert laptop.place == short_name
    assert laptop.holder == short_name
    assert "Held by: " + short_name + "." in prompt
    assert "Held by: " + full_name + "." not in prompt
    assert relation.holder == short_name
    assert short_name in question
    assert full_name not in question


def test_synthetic_story_uses_alias_for_holder_and_keeps_supporter_name() -> None:
    package = _synthetic_package()
    npc = Npc(id="hero", name="Ari Longfeather", aliases=("Ari",))
    package = package.model_copy(update={"world": package.world.model_copy(update={"npcs": (npc,)})})
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.move("lens", "hero").ok

    _assert_holder_projection(state, "lens", "Ari Longfeather", "Ari")
    assert world.move("lens", "tray").ok

    supporter_context = build_observation_context(
        world,
        "hero",
        ObservationRequest("Inspect the survey tray.", "look", "tray"),
        label=lambda current_world, entity_id: "Ari" if entity_id == "hero" else current_world.name(entity_id),
    )
    lens = next(thing for thing in supporter_context.visible_things if thing.name == "calibrated lens")
    assert lens.place == world.name("tray")


def test_unnamed_character_uses_unnamed_label_until_named_fact_is_true() -> None:
    package = _synthetic_package()
    npc = Npc(
        id="hero",
        name="Ari Longfeather",
        aliases=("Ari",),
        unnamed_label="the surveyor",
        named_by="hero_named",
    )
    package = package.model_copy(update={"world": package.world.model_copy(update={"npcs": (npc,)})})
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.move("lens", "hero").ok

    _world, _provider_instance, context, _prompt = _artifacts(
        state,
        ObservationRequest("Inspect the lens.", "look", "lens"),
    )

    lens = next(thing for thing in context.visible_things if thing.name == "calibrated lens")
    assert context.observer == "the surveyor"
    assert lens.place == "the surveyor"
    assert lens.holder == "the surveyor"


def test_default_label_keeps_bare_world_names_unchanged() -> None:
    schema = WorldSchema.from_data(
        {
            "entities": [
                {"id": "room", "name": "the observatory", "kind": "area"},
                {"id": "observer", "name": "Rhea Vale", "kind": "character"},
                {"id": "seat", "name": "the brass observation seat", "kind": "supporter"},
                {"id": "lens", "name": "calibrated lens", "kind": "thing"},
            ]
        }
    )
    world = World(schema, MemoryBackend())
    assert world.seed().ok
    assert world.move("observer", "room").ok
    assert world.move("lens", "seat").ok

    context = build_observation_context(
        world,
        "observer",
        ObservationRequest("Inspect the seat.", "look", "seat"),
    )
    lens = next(thing for thing in context.visible_things if thing.name == "calibrated lens")

    assert context.observer == world.name("observer")
    assert lens.place == world.name("seat")
