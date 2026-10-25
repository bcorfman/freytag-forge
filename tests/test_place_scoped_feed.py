from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import storygame.runtime.cloudflare as cloudflare
from storygame.runtime.capture import build_capture_provider
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for
from storygame.story_package.loader import StoryPackageError, load_story_package
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

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
GOLDENS = json.loads((ROOT / "tests/fixtures/place_feed/baseline_prompts.json").read_text())


class _Response:
    def __init__(self) -> None:
        self.body = json.dumps(
            {"narration": json.dumps({"segments": [{"kind": "narration", "text": "Fixture."}]})}
        ).encode()

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _stub_transport(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    captured: list[dict[str, object]] = []

    def open_request(request, **_kwargs: object) -> _Response:
        captured.append(json.loads(request.data))
        return _Response()

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "")
    monkeypatch.setattr(cloudflare, "urlopen", open_request)
    import storygame.runtime.jev as jev

    monkeypatch.setattr(
        jev.JevClient,
        "from_environment",
        classmethod(lambda cls: SimpleNamespace(ask=lambda *_args: {})),
    )
    return captured


def _state_at(place_id: str | None, *, scene_id: str = "1A") -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    if scene_id != "1A":
        state.current_scene_id = scene_id
        state.phase = next(
            scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id
        )
        state._assert_scene_entry_fact(scene_id)
        apply_scene_placements(PACKAGE, state.facts, scene_id)
    if place_id is not None:
        result = world_for(PACKAGE, state.facts).move(PACKAGE.world.protagonist_id, place_id)
        assert result.ok, result.reason
    return state


def _turn_prompt(monkeypatch: pytest.MonkeyPatch, state: RuntimeState, command: str = "Look around.") -> dict:
    captured = _stub_transport(monkeypatch)
    provider = build_capture_provider(state)
    provider._selected_names = list(provider.item_facts)
    provider(command)
    assert captured
    return captured[-1]


def _opening_prompt(monkeypatch: pytest.MonkeyPatch, state: RuntimeState) -> dict:
    captured = _stub_transport(monkeypatch)
    provider = build_capture_provider(state)
    provider.opening()
    assert captured
    return captured[-1]


@pytest.mark.parametrize(
    ("label", "place", "command"),
    (
        ("1a_mcgehee_home_look_around", "mcgehee_home", "Look around."),
        ("1a_kitchen_look_around", "kitchen", "Look around."),
    ),
)
def test_in_scene_prompts_are_byte_identical_to_baselines(
    monkeypatch: pytest.MonkeyPatch, label: str, place: str, command: str
) -> None:
    prompt = _turn_prompt(monkeypatch, _state_at(place), command)
    expected = GOLDENS[label]["requests"][0]
    assert prompt["system"] == expected["system"]
    assert prompt["user"] == expected["user"]


@pytest.mark.parametrize(("label", "scene_id"), (("1b_entry_opening", "1B"), ("2a_entry_opening", "2A")))
def test_entry_prompts_are_byte_identical_to_baselines(
    monkeypatch: pytest.MonkeyPatch, label: str, scene_id: str
) -> None:
    prompt = _opening_prompt(monkeypatch, _state_at(None, scene_id=scene_id))
    expected = GOLDENS[label]["requests"][0]
    assert prompt["system"] == expected["system"]
    assert prompt["user"] == expected["user"]


@pytest.mark.parametrize("place", ("outside_house", "truck_driver_seat"))
def test_outside_feed_uses_the_visible_place_and_local_things(monkeypatch: pytest.MonkeyPatch, place: str) -> None:
    prompt = _turn_prompt(monkeypatch, _state_at(place))
    user = prompt["user"]
    assert "Michelle's house stands behind a low gate." in user
    assert "Kristin's truck" in user
    assert "Kristin's laptop" in user
    assert "house gate" in user
    if place == "outside_house":
        assert "SCENE:\n- Kristin is outside the house." in user
    for hidden in (
        "drawer",
        "pens",
        "stapler",
        "spare batteries",
        "Michelle's phone",
        "workstation",
        "workstation chair",
        "back door has been forced",
        "thin gap",
    ):
        assert hidden.casefold() not in user.casefold()


def test_seated_outside_feed_has_exact_where_bullet(monkeypatch: pytest.MonkeyPatch) -> None:
    user = _turn_prompt(monkeypatch, _state_at("truck_driver_seat"))["user"]
    assert "SCENE:\n- Kristin is in the driver's seat of Kristin's truck, outside the house." in user
    assert "Kristin. Place: driver's seat." in user


def test_command_referred_distant_thing_remains_in_things(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at("outside_house")
    _stub_transport(monkeypatch)
    provider = build_capture_provider(state)
    provider._selected_names = list(provider.item_facts)
    provider._referred_names = ["drawer"]
    user = provider._section_user_prompt(provider.assemble_turn_prompt("Open the drawer.")["context"])
    assert "- drawer." in user


def test_name_matching_prompt_keeps_the_full_scene_list(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _state_at("outside_house")
    _stub_transport(monkeypatch)
    provider = build_capture_provider(state)
    matching = provider._match_payload("Look around.", [])
    assert matching["system"].startswith("You match names in a story game")
    for name in ("drawer", "pens", "stapler", "Michelle's phone", "workstation", "back door"):
        assert f"- {name}." in matching["user"]


def test_loader_rejects_blank_location_description(tmp_path: Path) -> None:
    root = tmp_path / "story"
    shutil.copytree(ROOT / "data/stories/continuity-initiative", root)
    world_path = root / "world.yaml"
    text = world_path.read_text()
    old_description = (
        "  description: \"Michelle's house stands behind a low gate. Kristin's truck is parked at the curb, and "
        'sirens carry from the next street."\n'
    )
    assert text.count(old_description) == 1
    world_path.write_text(text.replace(old_description, "  description: '  '\n"))
    with pytest.raises(StoryPackageError, match="description must be a non-blank string"):
        load_story_package(root)


def test_reach_scoped_committed_statements_follow_the_protagonist(monkeypatch: pytest.MonkeyPatch) -> None:
    inside = _state_at("mcgehee_home")
    outside = _state_at("outside_house")
    for state in (inside, outside):
        state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
        state.facts.assert_fact(Fact(predicate="drawer_gap_pointed_out", subject="story", value="true"))
        apply_world_effects(PACKAGE, state.facts)
    inside_user = _turn_prompt(monkeypatch, inside)["user"]
    outside_user = _turn_prompt(monkeypatch, outside)["user"]
    assert "Kristin opens the drawer and is pointed toward the thin gap" in inside_user
    assert "Kristin examines the carved initials and is pointed toward the thin gap" in inside_user
    assert "thin gap" not in outside_user


def _synthetic_package() -> StoryPackage:
    scene = Scene(
        metadata=SceneMetadata(
            scene_id="1A",
            location_id="room",
            freytag_phase="exposition",
            objective="find the key",
            item_ids=("car", "driver_seat", "held_key", "lamp", "remote_statue"),
            entry_text="A room waits.",
            item_placements={
                "car": ItemPlacement(parent="yard"),
                "driver_seat": ItemPlacement(parent="car"),
                "held_key": ItemPlacement(parent="hero"),
                "lamp": ItemPlacement(parent="room"),
                "remote_statue": ItemPlacement(parent="room"),
            },
            character_placements={"hero": CharacterPlacement(parent="room")},
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
        id="near_statue",
        statement="The statue bears a blue mark.",
        entity_ids=("remote_statue",),
        reach_entity_ids=("remote_statue",),
        aliases=("blue statue",),
        audience=Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        establishes=(RouteOperation(op="assert", fact_id="statue_known", value=True),),
        source=RevealSource(kind="scene_entry"),
    )
    world = WorldSource(
        story_id="second_story",
        protagonist_id="hero",
        locations=(
            Location(id="room", name="the room"),
            Location(id="yard", name="the yard", description="A small yard surrounds the room."),
        ),
        npcs=(Npc(id="hero", name="Ari"),),
        items=(
            Item(id="car", name="a blue car", kind="vehicle"),
            Item(
                id="driver_seat",
                name="driver seat",
                kind="seat",
                seat_for="car",
                enter_text="Ari sits down.",
                leave_text="Ari stands up.",
            ),
            Item(id="held_key", name="brass key"),
            Item(id="lamp", name="lamp"),
            Item(id="remote_statue", name="stone statue"),
        ),
        kinds=(KindDeclaration(id="seat", is_=("furniture", "supporter"), enterable=True),),
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
        story_id="second_story",
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
            story_id="second_story", canonical_scene_chain=("1A",), sole_ending_scene_id="1A", storylets=()
        ),
        knowledge=catalog,
        knowledge_indexes=indexes,
        deliveries=(),
    )


def _synthetic_provider(state: RuntimeState) -> ItemFactsProvider:
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider._selected_names = list(provider.item_facts)
    return provider


def test_synthetic_story_proves_place_scope_without_story_names() -> None:
    package = _synthetic_package()
    inside = RuntimeState.bootstrap(package)
    inside.facts.assert_fact(Fact(predicate="statue_known", subject="story", value="true"))
    inside_provider = _synthetic_provider(inside)
    inside_user = inside_provider._section_user_prompt(inside_provider.assemble_turn_prompt("Look around.")["context"])
    assert "The room is ready." in inside_user
    assert "The statue bears a blue mark." in inside_user
    assert "SCENE:" in inside_user and "Ari is" not in inside_user.split("SCENE:", 1)[1].split("\n\n", 1)[0]

    outside = RuntimeState.bootstrap(package)
    outside.facts.assert_fact(Fact(predicate="statue_known", subject="story", value="true"))
    assert world_for(package, outside.facts).move("hero", "yard").ok
    outside_provider = _synthetic_provider(outside)
    outside_provider._referred_names = ["stone statue"]
    outside_user = outside_provider._section_user_prompt(
        outside_provider.assemble_turn_prompt("Look at the stone statue.")["context"]
    )
    assert "A small yard surrounds the room." in outside_user
    assert "The room is ready." not in outside_user
    assert "The statue bears a blue mark." not in outside_user
    assert "- stone statue." in outside_user
    assert "- lamp." not in outside_user

    seated = RuntimeState.bootstrap(package)
    assert world_for(package, seated.facts).move("hero", "driver_seat").ok
    seated_provider = _synthetic_provider(seated)
    seated_user = seated_provider._section_user_prompt(seated_provider.assemble_turn_prompt("Look around.")["context"])
    assert "SCENE:\n- Ari is in the driver seat of a blue car, the yard." in seated_user
