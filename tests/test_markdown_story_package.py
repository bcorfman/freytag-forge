from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import unconveyed_terms
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for
from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.models import ItemPlacement, SceneFrame

PACKAGE = Path("data/stories/continuity-initiative")


def test_scene_frame_situation_may_be_omitted() -> None:
    package = load_story_package(PACKAGE)
    frame = next(item for item in package.knowledge.scene_frames if item.scene_id == "3C")

    assert frame.situation == ""
    assert frame.pressure == "Expose the network and escape"
    assert SceneFrame(scene_id="3C", pressure="Expose the network and escape").situation == ""


def test_scene_2b_applies_archive_and_companion_placements() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "2B"

    assert apply_scene_placements(package, state.facts, "2B") == ()

    world = world_for(package, state.facts)
    assert world.parent("kristin") == "janus_archive"
    assert world.parent("brandon") == "janus_archive"
    assert world.parent("archive_terminals") == "janus_archive"
    assert world.parent("medical_terminal") == "janus_archive"
    assert "brandon" in world.companions("kristin")


def test_scene_2c_applies_command_levels_and_companion_placements() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "2C"

    assert apply_scene_placements(package, state.facts, "2C") == ()

    world = world_for(package, state.facts)
    assert world.parent("kristin") == "purge_chamber"
    assert world.parent("brandon") == "purge_chamber"
    assert "brandon" in world.companions("kristin")


def test_scene_3a_applies_detention_group_and_codes_placements() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3A"

    assert apply_scene_placements(package, state.facts, "3A") == ()

    world = world_for(package, state.facts)
    for entity_id in ("kristin", "brandon", "michelle", "captives", "stolen_radio", "gate_status_panel"):
        assert world.parent(entity_id) == "detention_level"
    assert world.parent("senior_official") == "captives"
    assert world.members("captives") == ("senior_official",)
    assert world.parent("override_codes") == "senior_official"
    assert world.is_hidden("override_codes")
    assert "brandon" in world.companions("kristin")

    state.facts.assert_fact(Fact(predicate="military_override_codes_available", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    world = world_for(package, state.facts)
    assert world.parent("override_codes") == "kristin"
    assert not world.is_hidden("override_codes")


def test_scene_3b_places_group_in_security_corridors_and_moves_brandon_to_relay() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3B"

    assert apply_scene_placements(package, state.facts, "3B") == ()

    world = world_for(package, state.facts)
    assert world.parent("kristin") == "security_corridors"
    assert world.parent("brandon") == "security_corridors"
    assert world.parent("michelle") == "security_corridors"
    assert world.parent("rebecca") == "executive_office"
    assert set(world.companions("kristin")) == {"brandon", "michelle"}

    state.facts.assert_fact(Fact(predicate="relay_open", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    world = world_for(package, state.facts)
    assert world.parent("brandon") == "broadcast_relay"
    assert world.parent("kristin") == "security_corridors"
    assert world.parent("michelle") == "security_corridors"


def test_scene_3c_places_broadcast_chamber_and_moves_archive_to_kristin() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3A"
    assert apply_scene_placements(package, state.facts, "3A") == ()
    state.current_scene_id = "3B"
    assert apply_scene_placements(package, state.facts, "3B") == ()
    state.facts.assert_fact(Fact(predicate="relay_open", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    state.current_scene_id = "3C"

    assert apply_scene_placements(package, state.facts, "3C") == ()
    world = world_for(package, state.facts)
    assert world.parent("kristin") == "broadcast_chamber"
    assert world.parent("michelle") == "broadcast_chamber"
    assert world.parent("rebecca") == "executive_office"
    assert world.parent("brandon") == "broadcast_relay"
    assert world.parent("portable_archive") == "rebecca"
    assert set(world.companions("kristin")) == {"michelle"}

    state.facts.assert_fact(Fact(predicate="portable_archive_secured", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    assert world_for(package, state.facts).parent("portable_archive") == "kristin"


def test_scene_3c_places_captives_in_maintenance_network() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3A"
    assert apply_scene_placements(package, state.facts, "3A") == ()
    state.current_scene_id = "3B"
    assert apply_scene_placements(package, state.facts, "3B") == ()
    state.facts.assert_fact(Fact(predicate="relay_open", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    state.current_scene_id = "3C"

    assert apply_scene_placements(package, state.facts, "3C") == ()
    world = world_for(package, state.facts)
    assert world.parent("captives") == "maintenance_network"
    assert world.parent("senior_official") == "captives"


def test_scene_3c_places_pump_controls_and_declares_surface_location() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3A"
    assert apply_scene_placements(package, state.facts, "3A") == ()
    state.current_scene_id = "3B"
    assert apply_scene_placements(package, state.facts, "3B") == ()
    state.facts.assert_fact(Fact(predicate="relay_open", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    state.current_scene_id = "3C"

    assert apply_scene_placements(package, state.facts, "3C") == ()
    world = world_for(package, state.facts)
    assert world.parent("drainage_pump_controls") == "maintenance_network"
    facility_escape = next(location for location in package.world.locations if location.id == "facility_escape")
    assert facility_escape.name == "Los Angeles surface"
    assert facility_escape.parent == "regional_facility"


def test_scene_3b_office_entry_moves_kristin_and_michelle_in_and_leaves_brandon() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3B"

    assert apply_scene_placements(package, state.facts, "3B") == ()

    state.facts.assert_fact(Fact(predicate="rebecca_office_reached", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    world = world_for(package, state.facts)
    assert world.parent("kristin") == "executive_office"
    assert world.parent("michelle") == "executive_office"
    assert world.parent("brandon") == "security_corridors"
    assert world.parent("rebecca") == "executive_office"


def test_scene_2a_arrival_moves_kristin_and_brandon_to_the_perimeter() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "2A"

    assert apply_scene_placements(package, state.facts, "2A") == ()

    state.facts.assert_fact(Fact(predicate="false_identities_ready", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    world = world_for(package, state.facts)
    assert world.parent("kristin") == "brandon_hideout"
    assert world.parent("brandon") == "brandon_hideout"

    state.facts.assert_fact(Fact(predicate="facility_perimeter_reached", subject="story", value="true"))
    assert apply_world_effects(package, state.facts) == ()
    world = world_for(package, state.facts)
    assert world.parent("kristin") == "facility_perimeter"
    assert world.parent("brandon") == "facility_perimeter"


def test_scene_2c_may_name_the_maintenance_network() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "2C")

    assert "maintenance_network" in NarrationSafetyValidator._scene_entity_ids(package, scene)
    assert world_for(package, state.facts).parent("maintenance_network") == "purge_chamber"


def test_group_member_package_declares_group_and_places_member(tmp_path: Path) -> None:
    destination = copied_package(tmp_path)
    world_path = destination / "world.yaml"
    world_data = yaml.safe_load(world_path.read_text())
    world_data["groups"][0].pop("scoped_aliases", None)
    world_data["groups"].append({"id": "prisoners", "name": "Prisoners", "aliases": ["prisoners"]})
    world_path.write_text(yaml.safe_dump(world_data, sort_keys=False))
    plot_path = destination / "plot.md"
    plot = plot_path.read_text()
    plot = plot.replace(
        "participant_ids: [kristin, brandon, michelle, rebecca]\ncompanions: [brandon]\nitem_ids: []",
        "participant_ids: [kristin, brandon, michelle, rebecca]\n"
        "character_placements:\n  prisoners: {parent: purge_chamber}\n  michelle: {parent: prisoners}\n"
        "companions: [brandon]\nitem_ids: []",
        1,
    )
    plot_path.write_text(plot)

    package = load_story_package(destination)
    state = RuntimeState.bootstrap(package)
    assert apply_scene_placements(package, state.facts, "2C") == ()
    world = world_for(package, state.facts)
    assert world.members("prisoners") == ("michelle",)


def test_group_scoped_alias_loader_rejects_declared_name(tmp_path: Path) -> None:
    destination = copied_package(tmp_path)
    world_path = destination / "world.yaml"
    world_data = yaml.safe_load(world_path.read_text())
    world_data["groups"][0]["scoped_aliases"] = ["Kristin"]
    world_path.write_text(yaml.safe_dump(world_data, sort_keys=False))

    with pytest.raises(StoryPackageError, match="scoped alias 'Kristin'.*declared entity name or alias"):
        load_story_package(destination)


def copied_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE, destination)
    return destination


def test_continuity_package_loads_all_scene_headings_and_storylets() -> None:
    package = load_story_package(PACKAGE)
    assert [scene.metadata.scene_id for scene in package.scenes] == [
        "1A",
        "1B",
        "1C",
        "2A",
        "2B",
        "2C",
        "3A",
        "3B",
        "3C",
    ]
    assert len(package.storylets) == 39
    assert all(storylet.source_links and storylet.sections["Protected boundary"] for storylet in package.storylets)
    assert package.knowledge.schema_version == "2.0"
    assert package.scenes[0].metadata.item_placements == {
        "memory_card": ItemPlacement(parent="michelle_drawer", under=True),
        "michelle_phone": ItemPlacement(parent="kitchen", text="on the kitchen floor"),
        "kristin_laptop": ItemPlacement(parent="kristin_truck", text="in Kristin's truck outside the house"),
        "truck_driver_seat": ItemPlacement(parent="kristin_truck"),
        "truck_passenger_seat": ItemPlacement(parent="kristin_truck"),
        "kristin_truck": ItemPlacement(parent="outside_house"),
        "michelle_workstation": ItemPlacement(parent="kitchen"),
        "michelle_drawer": ItemPlacement(parent="michelle_workstation", part_of=True, text="in Michelle's workstation"),
        "workstation_chair": ItemPlacement(parent="kitchen", text="at Michelle's workstation"),
        "back_door": ItemPlacement(parent="kitchen"),
    }
    assert package.scenes[0].metadata.setting_facts == ()
    pacing_facts = {effect.fact_id for event in package.pacing.events for effect in event.effects}
    mapped_facts = set(package.knowledge_indexes.facts_to_knowledge)
    assert mapped_facts <= set(package.world.facts)
    assert set(package.world.facts) - pacing_facts <= mapped_facts
    assert set(package.knowledge_indexes.scene_to_candidates) == {"1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"}
    for route in package.storylet_routes.storylets:
        for realization in route.realizations:
            source_key = f"storylet:{route.id}:{realization.id}"
            knowledge_ids = package.knowledge_indexes.source_to_knowledge[source_key]
            effects = {
                effect
                for knowledge_id in knowledge_ids
                for effect in package.knowledge_indexes.by_id[knowledge_id].establishes
            }
            assert effects == set(realization.operations)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        pytest.param(
            lambda realization: realization.pop("source_beats"),
            "SL-1B-B-R1.*SL-1B-B.*source_beats",
            id="loader_rejects_missing_source_beats_on_multi_beat_realization",
        ),
        pytest.param(
            lambda realization: realization.__setitem__("source_beats", ["scene-1a1--michelles-gone"]),
            "SL-1B-B-R1.*outside its storylet",
            id="loader_rejects_source_beat_outside_realization_storylet",
        ),
    ],
)
def test_loader_rejects_invalid_realization_source_beats(tmp_path: Path, mutate: object, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / "storylet-routes.yaml"
    routes = yaml.safe_load(source.read_text(encoding="utf-8"))
    realization = next(
        realization
        for route in routes["storylets"]
        if route["id"] == "SL-1B-B"
        for realization in route["realization_options"]
        if realization["id"] == "SL-1B-B-R1"
    )
    mutate(realization)  # type: ignore[operator]
    source.write_text(yaml.safe_dump(routes, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_item_placement_for_an_item_not_in_the_scene(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    plot = package / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    contents = contents.replace(
        "  michelle_phone: {parent: kitchen, text: on the kitchen floor}\n",
        "  transit_card: {parent: kitchen, text: on the table}\n",
        1,
    )
    plot.write_text(contents, encoding="utf-8")

    with pytest.raises(StoryPackageError, match="scene 1A.*transit_card"):
        load_story_package(package)


def test_scene_without_item_placements_loads_with_an_empty_mapping(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    item_ids = (
        "item_ids: [memory_card, transit_card, number_sequence, michelle_photograph, "
        "park_bench, service_gate, storm_drain, kristin_truck]\n"
    )
    placement_block = (
        "item_placements:\n"
        "  park_bench: {parent: los_angeles_park}\n"
        "  service_gate: {parent: los_angeles_park}\n"
        "  storm_drain: {parent: los_angeles_park}\n"
        "  transit_card: {parent: park_bench, under: true}\n"
        "  number_sequence: {parent: park_bench, under: true}\n"
        "  michelle_photograph: {parent: park_bench, under: true}\n"
        "  kristin_truck: {parent: los_angeles_park}\n"
    )
    assert contents.count(item_ids) == 1
    assert contents.count(placement_block) == 1
    contents = contents.replace(item_ids, "item_ids: [memory_card, transit_card]\n", 1)
    plot.write_text(contents.replace(placement_block, "", 1), encoding="utf-8")

    copied_contents = plot.read_text(encoding="utf-8")
    assert placement_block not in copied_contents

    package = load_story_package(root)

    assert package.scenes[1].metadata.item_placements == {}


def test_guarded_item_placement_loads_with_text_and_guard_fact(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    contents = contents.replace(
        "item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer, "
        "workstation_chair, truck_driver_seat, truck_passenger_seat, kristin_truck, "
        "michelle_workstation, back_door]\n",
        "item_ids: [memory_card, michelle_phone, kristin_laptop, michelle_drawer, "
        "workstation_chair, truck_driver_seat, truck_passenger_seat, kristin_truck, "
        "michelle_workstation, back_door, test_item]\n",
        1,
    )
    contents = contents.replace(
        "  michelle_phone: {parent: kitchen, text: on the kitchen floor}\n",
        "  michelle_phone: {parent: kitchen, text: on the kitchen floor}\n"
        "  test_item:\n"
        "    placement: beneath the test desk\n"
        "    while_fact_false: michelle_abduction_suspicion\n",
        1,
    )
    plot.write_text(contents, encoding="utf-8")
    world_path = root / "world.yaml"
    world = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    world["items"].append({"id": "test_item", "name": "Test item"})
    world_path.write_text(yaml.safe_dump(world, sort_keys=False), encoding="utf-8")

    placement = load_story_package(root).scenes[0].metadata.item_placements["test_item"]

    assert placement.placement == "beneath the test desk"
    assert placement.while_fact_false == "michelle_abduction_suspicion"


def test_item_placement_accepts_true_guard_and_rejects_two_guards() -> None:
    placement = ItemPlacement(placement="under the drawer", while_fact_true="memory_card_recovered")

    assert placement.while_fact_true == "memory_card_recovered"
    with pytest.raises(ValidationError, match="at most one"):
        ItemPlacement(
            placement="under the drawer",
            while_fact_false="memory_card_recovered",
            while_fact_true="memory_card_recovered",
        )


def test_loader_parses_setting_facts_from_synthetic_scene_frontmatter(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8").replace(
        "entry_text:",
        'setting_facts: ["The test shutters are closed.", "The test lamp is on."]\nentry_text:',
        1,
    )
    plot.write_text(contents, encoding="utf-8")

    scene = load_story_package(root).scenes[0]

    assert scene.metadata.setting_facts == ("The test shutters are closed.", "The test lamp is on.")


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        pytest.param(
            "entry_text:",
            'setting_facts: ["  "]\nentry_text:',
            "setting_facts",
            id="loader_rejects_empty_setting_fact",
        ),
        pytest.param(
            "  michelle_phone: {parent: kitchen, text: on the kitchen floor}\n",
            "  michelle_phone:\n    placement: on the kitchen floor\n    while_fact_false: undeclared_fact\n",
            "scene 1A.*michelle_phone.*undeclared_fact",
            id="loader_rejects_item_placement_guard_for_an_unknown_fact",
        ),
        pytest.param(
            "  michelle_phone: {parent: kitchen, text: on the kitchen floor}\n",
            "  michelle_phone:\n    placement: on the kitchen floor\n    while_fact_true: undeclared_fact\n",
            "scene 1A.*michelle_phone.*undeclared_fact",
            id="loader_rejects_true_item_placement_guard_for_an_unknown_fact",
        ),
    ],
)
def test_loader_rejects_invalid_scene_fact_values(tmp_path: Path, old: str, new: str, message: str) -> None:
    root = copied_package(tmp_path)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8").replace(
        old,
        new,
        1,
    )
    plot.write_text(contents, encoding="utf-8")

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_uses_empty_setting_facts_when_unset(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8").replace(
        'setting_facts: ["The drawer is shut.", "The drawer holds pens, binder clips, a stapler, and '
        'spare batteries.", '
        '"Kristin\'s laptop is closed.", '
        '"Michelle\'s phone is not damaged."]\n',
        "",
        1,
    )
    plot.write_text(contents, encoding="utf-8")

    assert load_story_package(root).scenes[0].metadata.setting_facts == ()


def test_loader_rejects_transition_trigger_that_can_never_fail(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    world_source = root / "world.yaml"
    world = yaml.safe_load(world_source.read_text())
    world["facts"].append("never_asserted_fact")
    world_source.write_text(yaml.safe_dump(world, sort_keys=False))
    knowledge_source = root / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_source.read_text())
    knowledge["facts"].append({"id": "never_asserted_fact", "purpose": "test-only fact"})
    knowledge_source.write_text(yaml.safe_dump(knowledge, sort_keys=False))
    pacing_source = root / "pacing.yaml"
    pacing = yaml.safe_load(pacing_source.read_text())
    pacing["transitions"][0]["triggers"].append({"fact_id": "never_asserted_fact", "equals": False})
    pacing_source.write_text(yaml.safe_dump(pacing, sort_keys=False))

    with pytest.raises(StoryPackageError, match="t_1a_1b.*never_asserted_fact.*can never fail"):
        load_story_package(root)


def test_scene_beats_are_parsed_and_addressable_by_authored_anchor() -> None:
    package = load_story_package(PACKAGE)
    scene = package.scenes[0]

    assert list(scene.beats) == [
        "scene-1a1--michelle-is-gone",
        "scene-1a2--michelles-last-investigation",
        "scene-1a3--the-interrupted-message",
        "scene-1a4--the-first-threat",
    ]
    assert [beat.id for beat in scene.beats.values()] == ["1A.1", "1A.2", "1A.3", "1A.4"]
    assert [beat.anchor for beat in scene.beats.values()] == list(scene.beats)
    assert scene.opening_beat == scene.beats["scene-1a1--michelle-is-gone"]
    assert all(beat.title and beat.prose and 3 <= len(beat.details) <= 7 for beat in scene.beats.values())
    assert "**Details:**" not in scene.opening_beat.prose


def test_loader_rejects_a_beat_without_details(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    plot = package / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    details = "**Details:** missing tablet and work bag; forced back door; KMS initials carved in drawer\n"
    plot.write_text(contents.replace(details, "", 1), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="scene 1A beat 1A.1 lacks a Details line"):
        load_story_package(package)


def test_every_shipped_storylet_source_link_resolves_to_a_scene_beat() -> None:
    package = load_story_package(PACKAGE)
    beats = {anchor for scene in package.scenes for anchor in scene.beats}
    links = [link for storylet in package.storylets for link in storylet.source_links]

    assert len(set(links)) == 36
    assert all(link in beats for link in set(links))


def test_loader_rejects_a_storylet_linking_to_a_nonexistent_beat_anchor(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    storylets = package / "storylets.md"
    contents = storylets.read_text(encoding="utf-8")
    storylets.write_text(contents.replace("scene-1a2--michelles-last-investigation", "scene-1a2--missing-beat", 1))

    with pytest.raises(StoryPackageError, match="SL-1A-A.*scene-1a2--missing-beat"):
        load_story_package(package)


def test_a_scene_without_a_first_beat_fails_to_load(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    plot = package / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    heading = next(line for line in contents.splitlines(keepends=True) if line.startswith("### Scene 1A.1 "))
    plot.write_text(contents.replace(heading, "", 1), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="scene 1A lacks an opening beat"):
        load_story_package(package)


def test_scene_1a_entry_catalog_is_safe_before_any_route_is_selected() -> None:
    package = load_story_package(PACKAGE)

    entry = package.knowledge_indexes.by_id[package.knowledge_indexes.source_to_knowledge["entry:1A"][0]]

    assert entry.establishes[0].fact_id == "scene_1a_entry_known"
    assert entry.audience.player_visible
    entry_text = " ".join((entry.statement, *entry.aliases)).casefold()
    assert not {"warning", "janus", "facility", "patrol tape"} & set(entry_text.split())


def test_authored_handoff_candidates_are_exactly_the_reviewed_set() -> None:
    package = load_story_package(PACKAGE)
    expected = {
        "k_sl_1a_a_r1",
        "k_sl_1a_b_r0",
        "k_sl_1a_b_r1",
        "k_sl_1a_b_r2",
        "k_sl_1a_c_r1",
        "k_sl_1a_c_r2",
        "k_sl_1a_d_r1",
        "k_sl_1b_a_r1",
        "k_sl_1b_a_r2",
        "k_sl_1b_b_r1",
        "k_sl_1b_b_r2",
        "k_sl_1b_c_r1",
        "k_sl_1b_c_r2",
        "k_sl_1c_a_r1",
        "k_sl_1c_a_r2",
        "k_sl_1c_b_r1",
        "k_sl_1c_b_r2",
        "k_sl_1c_c_r1",
        "k_sl_1c_c_r2",
        "k_sl_2a_a_r1",
        "k_sl_2a_a_r2",
        "k_sl_2a_b_r1",
        "k_sl_2a_b_r2",
        "k_sl_2a_e_r1",
        "k_sl_2a_c_r1",
        "k_sl_2a_c_r2",
        "k_sl_2b_a_r1",
        "k_sl_2b_a_r2",
        "k_sl_2b_b_r1",
        "k_sl_2b_b_r2",
        "k_sl_2b_b_r3",
        "k_sl_2b_c_r1",
        "k_sl_2b_c_r2",
        "k_sl_3a_a_r1",
        "k_sl_3a_a_r2",
        "k_sl_3a_b_r1",
        "k_sl_3a_b_r2",
        "k_sl_3a_e_r1",
        "k_sl_3a_c_r1",
        "k_sl_3a_c_r2",
        "k_sl_3a_d_r1",
        "k_sl_3a_d_r2",
        "k_sl_3b_a_r1",
        "k_sl_3b_a_r2",
        "k_sl_3b_e_r1",
        "k_sl_3b_b_r1",
        "k_sl_3b_b_r2",
        "k_sl_3b_c_r1",
        "k_sl_3b_c_r2",
        "k_sl_3b_d_r1",
        "k_sl_3b_d_r2",
        "k_sl_3c_a_r1",
        "k_sl_3c_a_r2",
        "k_sl_3c_b_r1",
        "k_sl_3c_b_r2",
        "k_sl_3c_c_r1",
        "k_sl_3c_c_r2",
        "k_sl_3c_d_r1",
        "k_sl_3c_d_r2",
        "k_sl_3c_e_r1",
        "k_sl_3c_e_r2",
        "k_sl_2c_a_r1",
        "k_sl_2c_a_r2",
        "k_sl_2c_b_r1",
        "k_sl_2c_b_r2",
        "k_sl_2c_c_r1",
        "k_sl_2c_c_r2",
        "k_sl_2c_d_r1",
        "k_sl_2c_d_r2",
    }
    actual = {item.id for item in package.knowledge.knowledge if item.delivery_text}

    assert actual == expected, "Migrating or un-migrating a candidate is a reviewed change and must update this set."


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data["knowledge"][0]["establishes"][0].update(fact_id="unknown_fact"), "unknown fact"),
        (lambda data: data["knowledge"][0]["source"].update(realization_id="missing"), "unknown realization"),
        (lambda data: data["knowledge"][0].update(available_in_scenes=["1B"]), "source unavailable"),
        (lambda data: data["knowledge"][0].update(aliases=[]), "at least 1 item"),
        (lambda data: data.update(schema_version="1.1"), "schema_version"),
    ],
)
def test_loader_rejects_invalid_knowledge_catalog(tmp_path: Path, mutate: object, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    mutate(catalog)  # type: ignore[operator]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


_AUTHORED_DELIVERY = (
    "Michelle finds the memory card from under the drawer carved with her initials, KMS, and plays the damaged "
    "recording. The warning concerns emergency broadcasts."
)


def _knowledge_item(catalog: dict[str, object], knowledge_id: str) -> dict[str, object]:
    return next(item for item in catalog["knowledge"] if item["id"] == knowledge_id)  # type: ignore[index]


def test_complete_authored_handoff_loads_and_stays_out_of_runtime_serialization(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    item = _knowledge_item(catalog, "k_sl_1a_b_r2")
    item["delivery_text"] = _AUTHORED_DELIVERY
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))

    package = load_story_package(root)
    knowledge = next(item for item in package.knowledge.knowledge if item.id == "k_sl_1a_b_r2")
    candidate = KnowledgeProjector._candidate(knowledge)

    assert knowledge.delivery_text == _AUTHORED_DELIVERY
    assert candidate.delivery_text == _AUTHORED_DELIVERY
    assert "action_evidence" not in candidate.model_dump()
    assert "delivery_text" not in candidate.model_dump()
    assert _AUTHORED_DELIVERY not in candidate.model_dump_json()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda item: item.update(delivery_text=_AUTHORED_DELIVERY, action_evidence=[]), "non-empty action_evidence"),
        (
            lambda item: item.update(delivery_text=_AUTHORED_DELIVERY, action_evidence=[[]]),
            "non-empty action_evidence",
        ),
        (lambda item: item.update(delivery_text="   "), "blank delivery_text"),
        (
            lambda item: item.update(delivery_text="Michelle finds the memory card and plays the damaged recording."),
            "must_convey",
        ),
        (
            lambda item: item.update(delivery_text=f"{_AUTHORED_DELIVERY} (candidate_id: k_sl_1a_b_r2)"),
            "implementation-only token",
        ),
    ],
)
def test_loader_rejects_invalid_authored_handoff(tmp_path: Path, mutate: object, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    mutate(_knowledge_item(catalog, "k_sl_1a_b_r2"))  # type: ignore[operator]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_legacy_evidence_without_delivery_text_still_loads(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    _knowledge_item(catalog, "k_sl_1a_b_r1").pop("delivery_text")  # type: ignore[union-attr]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))

    package = load_story_package(root)
    legacy = next(item for item in package.knowledge.knowledge if item.id == "k_sl_1a_b_r1")

    assert legacy.action_evidence
    assert legacy.delivery_text is None


def test_scene_1a_recording_warning_handoff_matches_one_exact_action() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    projection = KnowledgeProjector().project(
        state,
        "player",
        "Play the damaged recording on Michelle's memory card.",
    )

    handoff = uniquely_matched_authored_handoff(
        "Play the damaged recording on Michelle's memory card.",
        projection.candidates,
    )

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_1a_b_r2"
    assert handoff.delivery_text == package.knowledge_indexes.by_id["k_sl_1a_b_r2"].delivery_text


def test_1a_deadline_fallback_names_the_drawer() -> None:
    delivery = next(
        item for item in load_story_package(PACKAGE).deliveries if item.fact_id == "continuity_initiative_known"
    )

    assert delivery.scene_id == "1A"
    assert "KMS" not in delivery.fallback_text
    assert "drawer" in delivery.fallback_text.casefold()


def test_scene_1a_files_evidence_requires_reading_saved_files() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    candidates = (
        KnowledgeProjector()
        .project(
            state,
            "player",
            "Recover Michelle's memory card and read the saved files.",
        )
        .candidates
    )
    evidence = tuple(
        ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence) for candidate in candidates
    )

    assert uniquely_matched_candidate("Recover Michelle's memory card.", evidence) is None
    assert uniquely_matched_candidate("Recover Michelle's memory card and read the saved files.", evidence).id == (
        "k_sl_1a_b_r1"
    )


@pytest.mark.parametrize(
    ("player_input", "expected_id"),
    [
        ("Recover Michelle's memory card.", None),
        ("Recover Michelle's damaged recording.", None),
        ("Recover Michelle's memory card and read the saved files.", "k_sl_1a_b_r1"),
        ("Do not recover Michelle's damaged recording or listen to it.", None),
    ],
)
def test_scene_1a_recording_warning_handoff_rejects_unsafe_partial_actions(
    player_input: str, expected_id: str | None
) -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    candidates = KnowledgeProjector().project(state, "player", player_input).candidates

    handoff = uniquely_matched_authored_handoff(player_input, candidates)
    if expected_id is None:
        assert handoff is None
    else:
        assert handoff is not None
        assert handoff.candidate.id == expected_id


def test_loader_rejects_ambiguous_knowledge_effect_and_unreachable_prerequisite(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    duplicate = dict(catalog["knowledge"][0])
    duplicate["id"] = "k_duplicate"
    catalog["knowledge"].append(duplicate)
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match="ownership is ambiguous"):
        load_story_package(root)

    root = copied_package(tmp_path / "unreachable")
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    catalog["knowledge"][0]["requires"] = [{"fact_id": "broadcast_started", "equals": True}]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match="unreachable prerequisite"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("entity_ids", ["missing_entity"], "unknown entities"),
        ("available_in_scenes", ["9Z"], "unknown scene"),
        (
            "audience",
            {"kind": "characters", "character_ids": ["missing_character"], "player_visible": False},
            "unknown audience character",
        ),
    ],
)
def test_loader_rejects_knowledge_reference_boundaries(tmp_path: Path, field: str, value: object, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    catalog["knowledge"][0][field] = value
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_knowledge_effect_mismatch_and_self_prerequisite(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    catalog["knowledge"][0]["establishes"][0]["fact_id"] = "michelle_warning_known"
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match="effects differ"):
        load_story_package(root)

    root = copied_package(tmp_path / "self")
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    catalog["knowledge"][0]["requires"] = [{"fact_id": "michelle_abduction_suspicion", "equals": True}]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match="own prerequisite"):
        load_story_package(root)


def test_loader_rejects_invalid_canonical_event_and_scene_entry_sources(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    event_knowledge = next(item for item in catalog["knowledge"] if item["id"] == "k_bridge_1b_departure")
    event_knowledge["source"]["canonical_event_id"] = "missing_event"
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match="canonical event source"):
        load_story_package(root)

    root = copied_package(tmp_path / "entry")
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    entry = next(item for item in catalog["knowledge"] if item["id"] == "k_scene_1a_entry")
    entry["establishes"][0]["fact_id"] = "michelle_warning_known"
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match="entry effects differ"):
        load_story_package(root)


def test_loader_rejects_same_scene_knowledge_prerequisite_cycle(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    suspicion = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_1a_c_r2")
    warning = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_1a_b_r2")
    suspicion["requires"] = [{"fact_id": "michelle_warning_known", "equals": True}]
    warning["requires"] = [{"fact_id": "house_marked_for_return", "equals": True}]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))

    with pytest.raises(StoryPackageError, match="prerequisite/reveal cycle"):
        load_story_package(root)


def test_loader_indexes_reachable_knowledge_prerequisites(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    candidate = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_1b_a_r1")
    candidate["requires"] = [{"fact_id": "brandon_face_known", "equals": True}]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    package = load_story_package(root)
    assert "k_sl_1b_a_r1" in package.knowledge_indexes.prerequisite_dependents["brandon_face_known"]


def test_loader_rejects_selectable_transition_trigger_without_must_convey(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    candidate = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_1a_d_r1")
    candidate.pop("must_convey")
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))

    with pytest.raises(StoryPackageError, match="must_convey"):
        load_story_package(root)


@pytest.mark.parametrize(("field", "message"), [("facts", "facts must define"), ("scene_frames", "safe scene frame")])
def test_loader_rejects_incomplete_knowledge_catalog(tmp_path: Path, field: str, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text())
    catalog[field].pop()
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        ("plot.md", "scene_id: 1A", "scene_id: 9Z", "heading and frontmatter"),
        ("plot.md", "---\nscene_id: 1A", "scene_id: 1A", "lacks YAML frontmatter"),
        ("world.yaml", "mcgehee_home", "unknown_home", "unknown location parent"),
        (
            "pacing.yaml",
            "min_turns: 8\n  nudge_after_turns: 10",
            "min_turns: 11\n  nudge_after_turns: 10",
            "turn allocations must be ordered",
        ),
        ("storylets.md", "**Pacing window**", "**Window**", "lacks sections"),
        ("storylets.md", "plot.md#scene-1a1", "plot.md#missing", "unknown plot heading"),
    ],
)
def test_loader_rejects_malformed_sources(tmp_path: Path, path: str, old: str, new: str, message: str) -> None:
    root = copied_package(tmp_path / "fallback")
    source = root / path
    source.write_text(source.read_text().replace(old, new, 1))
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_storylet_window_outside_parent_scene(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "storylets.md"
    source.write_text(source.read_text().replace("latest: `turn 3`", "latest: `turn 14`", 1))
    with pytest.raises(StoryPackageError, match="escapes its scene pacing window"):
        load_story_package(root)


def test_loader_rejects_a_pacing_event_scheduled_past_its_scene_minimum(tmp_path: Path) -> None:
    """An event later than the floor can be walked past, so the package must not load.

    min_turns is the earliest a scene can be left. An event scheduled after it is
    one the player may never see, and a beat that never fires is exactly the class
    of defect a hosted playthrough should not be the first thing to notice.
    """

    root = copied_package(tmp_path)
    source = root / "pacing.yaml"
    pacing = yaml.safe_load(source.read_text())
    window = next(item for item in pacing["scenes"] if item["scene_id"] == "1A")
    event = next(item for item in pacing["events"] if item["id"] == "pressure_1a")
    event["at_turn"] = window["min_turns"] + 1
    source.write_text(yaml.safe_dump(pacing, sort_keys=False))

    with pytest.raises(StoryPackageError, match="exceeds its min_turns floor"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("transition", "message"),
    [
        pytest.param(
            "- {id: t_cycle, source_scene_id: 3C, target_scene_id: 1A, priority: 1, "
            "triggers: [{fact_id: broadcast_started, equals: true}]}\n",
            "dependency cycle",
            id="loader_rejects_transition_dependency_cycle",
        ),
        pytest.param(
            "- {id: t_tie, source_scene_id: 1A, target_scene_id: 1C, priority: 10, "
            "triggers: [{fact_id: michelle_lead_actionable, equals: true}, "
            "{fact_id: patrol_return_pressure, equals: true}, "
            "{fact_id: memory_card_recovered, equals: true}]}\n",
            "ambiguous priority",
            id="loader_rejects_ambiguous_transition_priority",
        ),
    ],
)
def test_loader_rejects_invalid_transition_graph(tmp_path: Path, transition: str, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / "pacing.yaml"
    source.write_text(source.read_text() + "\n" + transition)
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_unknown_trigger_predicate_and_fallback(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    pacing = root / "pacing.yaml"
    pacing.write_text(
        pacing.read_text().replace(
            "  - fact_id: michelle_lead_actionable\n    equals: true\n  - fact_id: patrol_return_pressure",
            "  - fact_id: unknown_fact\n    equals: true\n  - fact_id: patrol_return_pressure",
            1,
        )
    )
    with pytest.raises(StoryPackageError, match="unknown trigger predicate"):
        load_story_package(root)

    root = copied_package(tmp_path / "fallback")
    world = root / "world.yaml"
    world.write_text(world.read_text().replace("  - michelle_phone", "  - missing_item", 1))
    with pytest.raises(StoryPackageError, match="unknown fallback"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        ("plot.md", "## Scene", "### Scene", "unknown scene"),
        ("storylets.md", "**Allowed scene:** `1A`", "**Allowed scene:** `1B`", "invalid allowed scene"),
        ("storylets.md", "earliest: `turn 0`", "earliest: `later`", "invalid turn offset"),
        (
            "pacing.yaml",
            "  - memory_card",
            "  - unknown",
            "unknown dependency",
        ),
        ("pacing.yaml", "id: t_1b_1c", "id: t_1a_1b", "duplicate transition ID"),
    ],
)
def test_loader_rejects_remaining_boundary_errors(tmp_path: Path, path: str, old: str, new: str, message: str) -> None:
    root = copied_package(tmp_path)
    source = root / path
    source.write_text(source.read_text().replace(old, new, 1))
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def _handoffs(root: Path) -> tuple[Path, dict[str, object]]:
    source = root / "handoffs.yaml"
    return source, yaml.safe_load(source.read_text(encoding="utf-8"))


def test_bridge_required_player_safe_facts_have_one_self_conveying_delivery() -> None:
    package = load_story_package(PACKAGE)
    required = {
        fact_id
        for event in package.storylet_routes.bridge_events
        for fact_id in (*event.activation.all_facts_true, *event.activation.any_of)
    }
    player_safe = {
        effect.fact_id
        for knowledge in package.knowledge.knowledge
        if knowledge.audience.player_visible
        for effect in knowledge.establishes
    }
    world_only = required - player_safe
    deliveries = {delivery.fact_id: delivery for delivery in package.deliveries}
    bridge_deliveries = {fact_id: deliveries[fact_id] for fact_id in required if fact_id in deliveries}

    assert set(bridge_deliveries) == required & player_safe
    assert required <= set(bridge_deliveries) | world_only
    assert len(package.deliveries) == len(deliveries)
    assert all(not unconveyed_terms(delivery.must_convey, delivery.fallback_text) for delivery in deliveries.values())


def test_loader_rejects_missing_bridge_delivery(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, handoffs = _handoffs(root)
    handoffs["deliveries"].pop(0)  # type: ignore[index]
    source.write_text(yaml.safe_dump(handoffs, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="continuity_initiative_known.*no FactDelivery"):
        load_story_package(root)


def test_loader_rejects_duplicate_fact_delivery(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, handoffs = _handoffs(root)
    handoffs["deliveries"].append(dict(handoffs["deliveries"][0]))  # type: ignore[index]
    source.write_text(yaml.safe_dump(handoffs, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="continuity_initiative_known.*more than one"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("fact_id", "field", "value", "message"),
    [
        pytest.param(
            "brandon_identified",
            "source_entity_id",
            "rebecca",
            "brandon_identified.*source entity.*rebecca.*absent",
            id="loader_rejects_delivery_source_outside_scene_participants",
        ),
        pytest.param(
            "facility_proof",
            "fallback_text",
            "The terminal is quiet and empty.",
            "facility_proof.*fallback_text.*fresh tire tracks",
            id="loader_rejects_delivery_fallback_that_misses_a_required_phrase",
        ),
        pytest.param(
            "facility_proof",
            "cue_text",
            "   ",
            "cue_text",
            id="loader_rejects_empty_delivery_cue_text",
        ),
    ],
)
def test_loader_rejects_invalid_delivery_fields(
    tmp_path: Path, fact_id: str, field: str, value: str, message: str
) -> None:
    root = copied_package(tmp_path)
    source, handoffs = _handoffs(root)
    delivery = next(item for item in handoffs["deliveries"] if item["fact_id"] == fact_id)  # type: ignore[index]
    delivery[field] = value
    source.write_text(yaml.safe_dump(handoffs, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_delivery_for_world_only_fact(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, handoffs = _handoffs(root)
    handoffs["deliveries"].append(  # type: ignore[index]
        {
            "fact_id": "rebecca_observing_infiltrators",
            "scene_id": "2A",
            "source_kind": "observation",
            "must_convey": [["security alert"], ["Rebecca is watching"]],
            "fallback_text": "The security alert makes clear that Rebecca is watching.",
        }
    )
    source.write_text(yaml.safe_dump(handoffs, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="rebecca_observing_infiltrators.*no player-visible"):
        load_story_package(root)


def test_loader_rejects_bridge_text_keys_that_do_not_match_transition_ids(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "plot.md"
    contents = source.read_text(encoding="utf-8")
    contents = contents.replace("transition_ids: [t_1a_1b]", "transition_ids: []", 1)
    source.write_text(contents, encoding="utf-8")

    with pytest.raises(StoryPackageError, match="scene 1A bridge_text keys must match transition_ids exactly"):
        load_story_package(root)


def _world():
    from storygame.story_package.loader import load_story_package

    return load_story_package(PACKAGE).world


def test_a_package_without_authored_character_biographies_still_loads() -> None:
    """CHARACTERS is authored material, so a package may simply not have it."""

    from storygame.story_package.loader import _parse_characters

    assert _parse_characters("# Story\n\n## Premise\n\nSomething happens.\n", _world()) == ()


def test_a_biography_for_someone_who_is_not_an_npc_is_skipped_not_rejected() -> None:
    """Prose may introduce a character before the runtime needs identity for them."""

    from storygame.story_package.loader import _parse_characters

    plot_text = (
        "## Principal Characters\n\n"
        "### Kristin Schweitzer\n\nA 33-year-old former assessment lead.\n\n"
        "### A Stranger On The Bus\n\nSomeone with no runtime identity at all.\n\n"
        "# Expanded Scene Outline\n"
    )
    characters = _parse_characters(plot_text, _world())

    assert [item.id for item in characters] == ["kristin"]
