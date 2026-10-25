from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.models import (
    Audience,
    Character,
    CharacterPlacement,
    FactDefinition,
    Item,
    ItemPlacement,
    KindDeclaration,
    KnowledgeCatalog,
    KnowledgeDefinition,
    KnowledgeIndexes,
    Location,
    Npc,
    PacingSource,
    RevealSource,
    RouteOperation,
    Scene,
    SceneBeat,
    SceneFrame,
    SceneMetadata,
    ScenePacing,
    StoryletRoutesSource,
    StoryPackage,
    WorldSource,
)


def _synthetic_package() -> StoryPackage:
    scene = Scene(
        metadata=SceneMetadata(
            scene_id="1A",
            location_id="room_a",
            freytag_phase="exposition",
            objective="find the key",
            item_ids=("lamp", "stone_statue", "truck", "driver_seat", "passenger_seat", "laptop"),
            entry_text="A room waits.",
            item_placements={
                "lamp": ItemPlacement(parent="room_b"),
                "stone_statue": ItemPlacement(parent="room_a"),
                "truck": ItemPlacement(parent="room_b"),
                "driver_seat": ItemPlacement(parent="truck"),
                "passenger_seat": ItemPlacement(parent="truck"),
                "laptop": ItemPlacement(parent="passenger_seat"),
            },
            character_placements={"hero": CharacterPlacement(parent="room_a")},
        ),
        prose="A room.",
        beats={
            "opening": SceneBeat(
                id="1A.1", anchor="opening", title="Opening", prose="A room.", details=("One.", "Two.", "Three.")
            )
        },
        opening_beat=SceneBeat(
            id="1A.1", anchor="opening", title="Opening", prose="A room.", details=("One.", "Two.", "Three.")
        ),
    )
    knowledge = KnowledgeDefinition(
        id="k_statue",
        statement="The statue bears a blue mark.",
        entity_ids=("stone_statue",),
        reach_entity_ids=("stone_statue",),
        aliases=("blue statue",),
        audience=Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        establishes=(RouteOperation(op="assert", fact_id="statue_known", value=True),),
        source=RevealSource(kind="scene_entry"),
    )
    world = WorldSource(
        story_id="synthetic",
        protagonist_id="hero",
        locations=(Location(id="room_a", name="Room A"), Location(id="room_b", name="Room B")),
        npcs=(Npc(id="hero", name="Ari"),),
        items=(
            Item(id="lamp", name="lamp"),
            Item(id="stone_statue", name="stone statue"),
            Item(id="truck", name="truck", kind="vehicle"),
            Item(id="driver_seat", name="driver's seat", kind="seat", seat_for="truck"),
            Item(id="passenger_seat", name="passenger seat", kind="seat", seat_for="truck"),
            Item(id="laptop", name="laptop"),
        ),
        kinds=(KindDeclaration(id="seat", is_=("supporter",), enterable=True),),
        facts=("scene_1a_entry_known", "statue_known"),
    )
    catalog = KnowledgeCatalog(
        schema_version="2.0",
        facts=(
            FactDefinition(id="scene_1a_entry_known", purpose="entry"),
            FactDefinition(id="statue_known", purpose="statue"),
        ),
        scene_frames=(SceneFrame(scene_id="1A", situation="The room is ready.", pressure="Find the key"),),
        knowledge=(knowledge,),
    )
    indexes = KnowledgeIndexes(
        by_id={knowledge.id: knowledge},
        facts_to_knowledge={},
        source_to_knowledge={},
        scene_to_candidates={"1A": ()},
        alias_to_knowledge={},
        audience_to_known_terms={},
        prerequisite_dependents={},
    )
    return StoryPackage(
        story_id="synthetic",
        protagonist_id="hero",
        characters=(Character(id="hero", name="Ari", bio="A traveler."),),
        scenes=(scene,),
        world=world,
        pacing=PacingSource(
            budget_seconds=10,
            scenes=(ScenePacing(scene_id="1A", min_turns=0, nudge_after_turns=1, handoff_after_turns=1),),
            transitions=(),
        ),
        storylets=(),
        storylet_routes=StoryletRoutesSource(
            story_id="synthetic", canonical_scene_chain=("1A",), sole_ending_scene_id="1A", storylets=()
        ),
        knowledge=catalog,
        knowledge_indexes=indexes,
        deliveries=(),
    )


def _provider(monkeypatch, *, referred: str, command: str, dependency: str | None = None):
    package = _synthetic_package()
    state = RuntimeState.bootstrap(package)
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    if dependency is not None:
        provider.dependency_names = lambda: [dependency]
    monkeypatch.setattr(
        CloudflareTurnProvider,
        "_request_item_facts",
        lambda *_args: {"refers": [referred], "same_as": {}},
    )
    provider.prepare_turn(command)
    provider._example_player_input = command
    return provider


def test_distant_referred_object_is_not_in_things(monkeypatch):
    provider = _provider(monkeypatch, referred="lamp", command="Wait.")

    assert "- lamp." not in provider._things_block(narration=True)


def test_literal_distant_object_stays_in_things(monkeypatch):
    provider = _provider(monkeypatch, referred="lamp", command="Look at the lamp.")

    assert "- lamp." in provider._things_block(narration=True)


def test_referred_object_in_protagonist_room_stays_in_things(monkeypatch):
    provider = _provider(monkeypatch, referred="stone statue", command="Wait.")

    assert "- stone statue." in provider._things_block(narration=True)


def test_distant_dependency_stays_in_things(monkeypatch):
    provider = _provider(monkeypatch, referred="lamp", command="Wait.", dependency="lamp")

    assert "- lamp." in provider._things_block(narration=True)


def test_distant_referred_vehicle_drops_expanded_companions(monkeypatch):
    provider = _provider(monkeypatch, referred="truck", command="Wait.")

    things = provider._things_block(narration=True)

    assert all(f"- {name}." not in things for name in ("truck", "driver's seat", "passenger seat", "laptop"))


def test_literal_distant_vehicle_stays_in_things(monkeypatch):
    provider = _provider(monkeypatch, referred="truck", command="Look at the truck.")

    things = provider._things_block(narration=True)

    assert "- truck." in things
