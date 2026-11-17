from __future__ import annotations

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
from storygame.story_package import StoryPackageError as _StoryPackageError
from storygame.story_package import load_story_package
from storygame.story_package.models import ItemPlacement, SceneFrame
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import DELETE, compiled_story_copy
from tests.story_source.helpers import patch_source as _patch_source

StoryPackageError = (_StoryPackageError, SourceError)


def patch_source(root: Path, file: str, address: str, value: object = DELETE) -> None:
    _patch_source(root / "source", file, address, value)


PACKAGE = Path("data/stories/continuity-initiative")


def test_scene_frame_situation_may_be_omitted() -> None:
    package = load_story_package(PACKAGE)
    frame = next(item for item in package.knowledge.scene_frames if item.scene_id == "3C")

    assert frame.situation == ""
    assert frame.pressure == "Expose the network and escape"
    assert SceneFrame(scene_id="3C", pressure="Expose the network and escape").situation == ""


def test_scene_1c_frame_situation_names_the_processing_line() -> None:
    package = load_story_package(PACKAGE)
    frame = next(item for item in package.knowledge.scene_frames if item.scene_id == "1C")

    assert frame.situation == (
        "The freight terminal has loading docks above a service level. The observation shaft overlooks the processing "
        "line. The service entrance is at the freight terminal."
    )


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

    world = world_for(package, state.facts)
    assert world.parent("kristin") == "facility_perimeter"
    assert world.parent("brandon") == "facility_perimeter"
    assert world.parent("shift_supervisor") == "facility_perimeter"


def test_scene_2c_may_name_the_maintenance_network() -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "2C")

    assert "maintenance_network" in NarrationSafetyValidator._scene_entity_ids(package, scene)
    assert world_for(package, state.facts).parent("maintenance_network") == "purge_chamber"


def test_group_member_package_declares_group_and_places_member(tmp_path: Path) -> None:
    destination = copied_package(tmp_path)
    catalog_path = destination / "source" / "catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    catalog["groups"]["captives"].pop("scoped_aliases", None)  # type: ignore[index]
    catalog["groups"]["prisoners"] = {"name": "Prisoners", "aliases": ["prisoners"]}  # type: ignore[index]
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")
    patch_source(destination, "scenes/2C.yaml", "placements.prisoners", {"parent": "purge_chamber"})
    patch_source(destination, "scenes/2C.yaml", "placements.michelle", {"parent": "prisoners"})

    package = load_story_package(destination)
    state = RuntimeState.bootstrap(package)
    assert apply_scene_placements(package, state.facts, "2C") == ()
    world = world_for(package, state.facts)
    assert world.members("prisoners") == ("michelle",)
    assert world.parent("rebecca") == "purge_chamber"
    assert world.parent("copied_janus_files") == "kristin"


def test_group_scoped_alias_loader_rejects_declared_name(tmp_path: Path) -> None:
    destination = copied_package(tmp_path)
    catalog_path = destination / "source" / "catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    catalog["groups"]["corridor_guards"]["scoped_aliases"] = ["Kristin"]  # type: ignore[index]
    catalog_path.write_text(yaml.safe_dump(catalog, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="scoped alias 'Kristin'.*declared entity name or alias"):
        load_story_package(destination)


def copied_package(tmp_path: Path) -> Path:
    return compiled_story_copy(tmp_path)


def _source_document(root: Path, relative_path: str) -> tuple[Path, dict[str, object]]:
    path = root / "source" / relative_path
    return path, yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_source(path: Path, document: dict[str, object]) -> None:
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def _reveal(scene: dict[str, object], claim_id: str) -> dict[str, object]:
    return next(
        variant
        for reveal in scene["reveals"]  # type: ignore[index]
        for variant in reveal.get("variants", {}).values()
        if variant.get("claim_id") == claim_id
    )


def _match_claim(match: dict[str, object], claim_id: str) -> dict[str, object]:
    return match["claims"][claim_id]  # type: ignore[index]


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
    assert len(package.storylets) == 68  # SL-1A-K adds one authored storylet.
    assert all(storylet.source_links and storylet.sections["Protected boundary"] for storylet in package.storylets)
    assert package.knowledge.schema_version == "2.0"
    assert package.scenes[0].metadata.item_placements == {
        "memory_card": ItemPlacement(parent="michelle_drawer", under=True),
        "michelle_phone": ItemPlacement(parent="kitchen", text="on the kitchen floor"),
        "kristin_laptop": ItemPlacement(parent="truck_passenger_seat", text="on the passenger seat of Kristin's truck"),
        "truck_driver_seat": ItemPlacement(parent="kristin_truck"),
        "truck_passenger_seat": ItemPlacement(parent="kristin_truck"),
        "kristin_truck": ItemPlacement(parent="outside_house"),
        "michelle_workstation": ItemPlacement(parent="kitchen", text="across the kitchen from the back door"),
        "michelle_drawer": ItemPlacement(parent="michelle_workstation", part_of=True, text="in Michelle's workstation"),
        "workstation_chair": ItemPlacement(parent="kitchen", text="at Michelle's workstation"),
        "back_door": ItemPlacement(parent="kitchen"),
        "house_gate": ItemPlacement(parent="outside_house", text="at the front of the house"),
        "michelle_tea_mug": ItemPlacement(parent="michelle_workstation", text="on Michelle's workstation"),
        "michelle_reading_glasses": ItemPlacement(parent="michelle_workstation", text="folded on her manuscript pages"),
        "manuscript_pages": ItemPlacement(parent="michelle_workstation", text="marked in red pen"),
        "kitchen_calendar": ItemPlacement(
            parent="kitchen", text="a paper calendar hanging on the wall by the refrigerator"
        ),
        "lake_photograph": ItemPlacement(
            parent="kitchen",
            text="held to the refrigerator by a pear-shaped magnet, showing Kristin and Michelle at a lake",
        ),
        "back_door_splinters": ItemPlacement(parent="kitchen", text="around the back door frame"),
        "back_door_deadbolt": ItemPlacement(parent="kitchen", text="on the back door"),
        "truck_radio": ItemPlacement(parent="kristin_truck"),
    }
    assert package.scenes[0].metadata.setting_facts == (
        "Sirens carry from the next street.",
        "A dog barks behind the empty house next door.",
        "The rest of the house is quiet. Michelle is not in it.",
    )
    pacing_facts = {effect.fact_id for event in package.pacing.events for effect in event.effects}
    mapped_facts = set(package.knowledge_indexes.facts_to_knowledge)
    pacing_only_facts = {
        "evidence_gap_processing_numbers",
        "evidence_gap_development_record",
        "evidence_gap_marked_site_list",
        "national_detention_network_known",
        "architects_strategy_known",
        "card_challenged",
        "kristin_marked_by_patrol",
        # Retained world declarations from the retired Act 2 preparation/search beats.
        "archive_security_sweep",
        "brandon_prepared_before_event",
        "facility_perimeter_reached",
        "false_identities_ready",
        "identity_scrutiny_visible",
        "inspector_cover_under_review",
        "kristin_deliberately_left_behind",
        "prisoner_records_corrupted",
        "processing_numbers_used_in_confrontation",
        "purge_transfers_underway",
        "service_route_used_in_confrontation",
        "los_angeles_facility_lost",
    }
    assert mapped_facts <= set(package.world.facts)
    assert set(package.world.facts) - pacing_facts - pacing_only_facts <= mapped_facts
    assert set(package.knowledge_indexes.scene_to_candidates) == {"1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"}
    unmapped_realizations = {
        "storylet:SL-2A-D:SL-2A-D-R1",
        "storylet:SL-2B-D:SL-2B-D-R1",
        "storylet:SL-2C-E:SL-2C-E-R1",
        "storylet:SL-3C-F:SL-3C-F-R1",
    }
    for route in package.storylet_routes.storylets:
        for realization in route.realizations:
            source_key = f"storylet:{route.id}:{realization.id}"
            knowledge_ids = package.knowledge_indexes.source_to_knowledge.get(source_key)
            if source_key in unmapped_realizations:
                continue
            if knowledge_ids is None:
                assert source_key in unmapped_realizations
                continue
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
            lambda realization: realization.pop("from_outline"),
            "SL-1B-B-R1.*SL-1B-B.*source_beats",
            id="loader_rejects_missing_source_beats_on_multi_beat_realization",
        ),
        pytest.param(
            lambda realization: realization.__setitem__("from_outline", ["1A.1"]),
            "StopIteration",
            id="loader_rejects_source_beat_outside_realization_storylet",
        ),
    ],
)
def test_loader_rejects_invalid_realization_source_beats(tmp_path: Path, mutate: object, message: str) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1B.yaml")
    realization = _reveal(scene, "k_sl_1b_b_r1")
    mutate(realization)  # type: ignore[operator]
    _write_source(source, scene)

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_item_placement_for_an_item_not_in_the_scene(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    patch_source(package, "scenes/1A.yaml", "placements.stolen_radio", {"parent": "kitchen", "text": "on the table"})

    with pytest.raises(StoryPackageError, match="scene 1A.*stolen_radio"):
        load_story_package(package)


def test_scene_without_item_placements_loads_with_an_empty_mapping(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1B.yaml")
    scene["placements"] = {}
    _write_source(source, scene)
    assert scene["placements"] == {}

    package = load_story_package(root)

    assert package.scenes[1].metadata.item_placements == {}


def test_guarded_item_placement_loads_with_text_and_guard_fact(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    scene_path, scene = _source_document(root, "scenes/1A.yaml")
    scene["items"].append("test_item")  # type: ignore[union-attr]
    scene["placements"]["test_item"] = {  # type: ignore[index]
        "placement": "beneath the test desk",
        "while_fact_false": "michelle_abduction_suspicion",
    }
    _write_source(scene_path, scene)
    catalog_path, catalog = _source_document(root, "catalog.yaml")
    catalog["items"]["test_item"] = {"name": "Test item"}  # type: ignore[index]
    _write_source(catalog_path, catalog)

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
    patch_source(root, "scenes/1A.yaml", "setting", ["The test shutters are closed.", "The test lamp is on."])

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
            "1A.*michelle_phone.*undeclared_fact",
            id="loader_rejects_item_placement_guard_for_an_unknown_fact",
        ),
        pytest.param(
            "  michelle_phone: {parent: kitchen, text: on the kitchen floor}\n",
            "  michelle_phone:\n    placement: on the kitchen floor\n    while_fact_true: undeclared_fact\n",
            "1A.*michelle_phone.*undeclared_fact",
            id="loader_rejects_true_item_placement_guard_for_an_unknown_fact",
        ),
    ],
)
def test_loader_rejects_invalid_scene_fact_values(tmp_path: Path, old: str, new: str, message: str) -> None:
    root = copied_package(tmp_path)
    if "entry_text:" in old:
        patch_source(root, "scenes/1A.yaml", "setting", ["  "])
    else:
        patch_source(
            root,
            "scenes/1A.yaml",
            "placements.michelle_phone",
            {"parent": "kitchen", "text": "on the kitchen floor", "while_fact_false": "undeclared_fact"}
            if "while_fact_false" in new
            else {"parent": "kitchen", "text": "on the kitchen floor", "while_fact_true": "undeclared_fact"},
        )

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_uses_empty_setting_facts_when_unset(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    patch_source(root, "scenes/1A.yaml", "setting", [])

    assert load_story_package(root).scenes[0].metadata.setting_facts == ()


def test_loader_rejects_transition_trigger_that_can_never_fail(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    scene_path, scene = _source_document(root, "scenes/1A.yaml")
    scene["exit"]["when_all"].append("never_asserted_fact")  # type: ignore[index]
    _write_source(scene_path, scene)
    scene["facts"]["never_asserted_fact"] = {"purpose": "test-only fact"}  # type: ignore[index]
    _write_source(scene_path, scene)

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
    source, scene = _source_document(package, "scenes/1A.yaml")
    next(beat for beat in scene["outline"] if beat["id"] == "1A.1")["details"] = ["too few"]  # type: ignore[index]
    _write_source(source, scene)

    with pytest.raises(StoryPackageError, match="1A.1.details.*between 3 and 7"):
        load_story_package(package)


def test_every_shipped_storylet_source_link_resolves_to_a_scene_beat() -> None:
    package = load_story_package(PACKAGE)
    beats = {anchor for scene in package.scenes for anchor in scene.beats}
    links = [link for storylet in package.storylets for link in storylet.source_links]

    assert len(set(links)) == 34
    assert all(link in beats for link in set(links))


def test_loader_rejects_a_storylet_linking_to_a_nonexistent_beat_anchor(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    patch_source(package, "scenes/1A.yaml", "reveals[sl_1a_a].from_outline[1]", "1A.2-missing-beat")

    with pytest.raises(StoryPackageError, match="sl_1a_a.*does not resolve"):
        load_story_package(package)


def test_a_scene_without_a_first_beat_fails_to_load(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    source, scene = _source_document(package, "scenes/1A.yaml")
    scene["outline"] = [beat for beat in scene["outline"] if beat["id"] != "1A.1"]  # type: ignore[index]
    _write_source(source, scene)

    with pytest.raises(StoryPackageError, match="outline reference '1A.1' does not resolve"):
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
        "k_sl_1a_g_r1",
        "k_sl_1a_g_r2",
        "k_sl_1a_h_r1",
        "k_sl_1a_i_r1",
        "k_sl_1a_j_r1",
        "k_sl_1a_j_r2",
        "k_sl_1a_j_r3",
        "k_sl_1a_b_r0",
        "k_sl_1a_b_r0w",
        "k_sl_1a_f_r1",
        "k_sl_1a_f_r2",
        "k_sl_1a_f_r3",
        "k_sl_1a_b_r1",
        "k_sl_1a_b_r2",
        "k_sl_1a_c_r1",
        "k_sl_1a_c_r2",
        "k_sl_1a_k_r1",
        "k_sl_1a_d_r1",
        "k_sl_1b_a_r1",
        "k_sl_1b_a_r2",
        "k_sl_1b_b_r1",
        "k_sl_1b_b_r2",
        "k_sl_1b_d_r1",
        "k_sl_1b_e_r1",
        "k_sl_1b_f_r1",
        "k_sl_1b_g_r1",
        "k_sl_1b_h_r1",
        "k_sl_1b_c_r1",
        "k_sl_1b_c_r2",
        "k_sl_1c_a_r1",
        "k_sl_1c_b_r1",
        "k_sl_1c_b_r2",
        "k_sl_1c_c_copy_numbers",
        "k_sl_1c_c_secure_route",
        "k_sl_1c_d_r1",
        "k_sl_1c_e_r1",
        "k_sl_1c_f_r1",
        "k_sl_1c_g_r1",
        "k_sl_2a_c_r5",
        "k_sl_2a_c_r6",
        "k_sl_2a_b_r1",
        "k_sl_2a_e_r1",
        "k_sl_2a_f_r1",
        "k_sl_2a_g_r1",
        "k_sl_2a_h_r1",
        "k_sl_2b_b_r4",
        "k_sl_2b_b_r5",
        "k_sl_2b_a_r1",
        "k_sl_2b_c_r3",
        "k_sl_2b_e_r1",
        "k_sl_2b_f_r1",
        "k_sl_2b_g_r1",
        "k_sl_3a_a_r1",
        "k_sl_3a_a_r2",
        "k_sl_3a_b_r1",
        "k_sl_3a_b_r2",
        "k_sl_3a_e_r1",
        "k_sl_3a_c_r1",
        "k_sl_3a_c_r2",
        "k_sl_3a_d_r1",
        "k_sl_3a_d_r2",
        "k_sl_3a_f_r1",
        "k_sl_3a_g_r1",
        "k_sl_3a_h_r1",
        "k_sl_3a_i_r1",
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
        "k_sl_2c_d_r3",
        "k_sl_2c_d_r4",
        "k_sl_2c_c_r1",
        "k_sl_2c_f_r1",
        "k_sl_2c_g_r1",
        "k_sl_2c_h_r1",
    }
    actual = {item.id for item in package.knowledge.knowledge if item.delivery_text}

    assert actual == expected, "Migrating or un-migrating a candidate is a reviewed change and must update this set."


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda data: data["reveal"].update(commits={"unknown_fact": True}), "fact .*unknown_fact.*not declared"),
        (lambda data: data["reveal"].update(realization_id="missing"), "realization_id"),
        (
            lambda data: data["scene"]["reveals"][0]["guidance"].update(available_while={"missing_fact": True}),
            "not declared",
        ),
        (lambda data: data["claim"].update(aliases=[]), "at least 1 item"),
        (lambda data: data["scene"].update(schema=2), "schema"),
    ],
)
def test_loader_rejects_invalid_knowledge_catalog(tmp_path: Path, mutate: object, message: str) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    match_path, match = _source_document(root, "scenes/1A.match.yaml")
    payload = {"scene": scene, "reveal": _reveal(scene, "k_sl_1a_a_r1"), "claim": _match_claim(match, "k_sl_1a_a_r1")}
    mutate(payload)  # type: ignore[operator]
    _write_source(source, scene)
    _write_source(match_path, match)
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


_AUTHORED_DELIVERY = (
    "Michelle finds the memory card from under the drawer carved with her initials, KMS, and plays the damaged "
    "recording. The warning concerns emergency broadcasts."
)


def _knowledge_item(scene: dict[str, object], knowledge_id: str) -> dict[str, object]:
    return next(
        variant
        for reveal in scene["reveals"]  # type: ignore[index]
        for variant in reveal.get("variants", {}).values()
        if variant.get("claim_id") == knowledge_id
    )


def test_complete_authored_handoff_loads_and_stays_out_of_runtime_serialization(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    item = _knowledge_item(scene, "k_sl_1a_b_r2")
    item["text"] = _AUTHORED_DELIVERY
    _write_source(source, scene)

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
        (lambda data: data["claim"].update(action_evidence=[]), "non-empty action_evidence"),
        (
            lambda data: data["claim"].update(action_evidence=[[]]),
            "non-empty action_evidence",
        ),
        (lambda data: data["variant"].update(text="   "), "blank"),
        (
            lambda data: data["variant"].update(text="Michelle finds the memory card and plays the damaged recording."),
            "must_convey",
        ),
        (
            lambda data: data["variant"].update(text=f"{_AUTHORED_DELIVERY} (candidate_id: k_sl_1a_b_r2)"),
            "implementation-only token",
        ),
    ],
)
def test_loader_rejects_invalid_authored_handoff(tmp_path: Path, mutate: object, message: str) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    match_path, match = _source_document(root, "scenes/1A.match.yaml")
    payload = {
        "variant": _knowledge_item(scene, "k_sl_1a_b_r2"),
        "claim": _match_claim(match, "k_sl_1a_b_r2"),
    }
    mutate(payload)  # type: ignore[operator]
    _write_source(source, scene)
    _write_source(match_path, match)

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_evidence_without_delivery_text_still_loads(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    _knowledge_item(scene, "k_sl_1a_b_r1").pop("text")  # type: ignore[union-attr]
    _write_source(source, scene)

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
    kitchen_candidates = (
        KnowledgeProjector()
        .project(
            state,
            "player",
            "Recover Michelle's memory card and read the saved files.",
        )
        .candidates
    )
    kitchen_evidence = tuple(
        ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence)
        for candidate in kitchen_candidates
    )

    assert uniquely_matched_candidate("Recover Michelle's memory card.", kitchen_evidence) is None
    # 1A laptop reach: the files cannot be read while Kristin is still in the kitchen.
    assert (
        uniquely_matched_candidate("Recover Michelle's memory card and read the saved files.", kitchen_evidence) is None
    )

    assert world_for(package, state.facts).move("kristin", "truck_driver_seat").ok
    laptop_candidates = (
        KnowledgeProjector()
        .project(
            state,
            "player",
            "Recover Michelle's memory card and read the saved files.",
        )
        .candidates
    )
    laptop_evidence = tuple(
        ActionEvidenceCandidate(id=candidate.id, required_groups=candidate.action_evidence)
        for candidate in laptop_candidates
    )

    # 1A laptop reach: the same action resolves once Kristin is with her laptop.
    assert (
        uniquely_matched_candidate("Recover Michelle's memory card and read the saved files.", laptop_evidence).id
        == "k_sl_1a_b_r1"
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
    if expected_id is not None:
        assert world_for(package, state.facts).move("kristin", "truck_driver_seat").ok
    candidates = KnowledgeProjector().project(state, "player", player_input).candidates

    handoff = uniquely_matched_authored_handoff(player_input, candidates)
    if expected_id is None:
        assert handoff is None
    else:
        assert handoff is not None
        assert handoff.candidate.id == expected_id


def test_loader_rejects_ambiguous_knowledge_effect_and_unreachable_prerequisite(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    duplicate = dict(scene["reveals"][0])  # type: ignore[index]
    duplicate["id"] = "sl_duplicate"
    scene["reveals"].append(duplicate)  # type: ignore[union-attr]
    _write_source(source, scene)
    with pytest.raises(SourceError, match=r"L2\.duplicate_id.*storylet id 'SL-1A-A'"):
        load_story_package(root)

    root = copied_package(tmp_path / "unreachable")
    # The source tree has no writable legacy ``requires`` field; an explicit prerequisite is a shape error.
    patch_source(
        root,
        "scenes/1A.yaml",
        "reveals[sl_1a_a].guidance.prerequisite",
        {"broadcast_started": True},
    )
    with pytest.raises(SourceError, match=r"L1\.unknown_key.*unknown key 'prerequisite'"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("entity_ids", ["missing_entity"], "entity reference .*does not resolve"),
        ("available_in_scenes", ["9Z"], "fact .*9Z.*not declared"),
        (
            "audience",
            {"kind": "characters", "character_ids": ["missing_character"], "player_visible": False},
            "unknown audience character",
        ),
    ],
)
def test_loader_rejects_knowledge_reference_boundaries(tmp_path: Path, field: str, value: object, message: str) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    match_path, match = _source_document(root, "scenes/1A.match.yaml")
    if field == "entity_ids":
        _reveal(scene, "k_sl_1a_a_r1")["entities"] = value
    elif field == "available_in_scenes":
        scene["reveals"][0]["guidance"]["available_while"] = {"9Z": True}  # type: ignore[index]
    else:
        _reveal(scene, "k_sl_1a_a_r1")["audience"] = value
    _write_source(source, scene)
    _write_source(match_path, match)
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_knowledge_effect_mismatch_and_self_prerequisite(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    match_path, match = _source_document(root, "scenes/1A.match.yaml")
    _reveal(scene, "k_sl_1a_a_r1")["commits_subset"] = {"michelle_warning_known": True}
    _write_source(source, scene)
    _write_source(match_path, match)
    with pytest.raises(StoryPackageError, match="establishes a fact outside its source commits"):
        load_story_package(root)

    root = copied_package(tmp_path / "self")
    source, scene = _source_document(root, "scenes/1A.yaml")
    _reveal(scene, "k_sl_1a_a_r1")["when"] = {"michelle_abduction_suspicion": True}
    _write_source(source, scene)
    with pytest.raises(StoryPackageError, match="own prerequisite"):
        load_story_package(root)


def test_loader_rejects_invalid_canonical_event_and_scene_entry_sources(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    patch_source(
        root,
        "scenes/1B.yaml",
        "bridge[bridge_1b_departure].claim.source",
        {"canonical_event_id": "missing_event"},
    )
    with pytest.raises(SourceError, match=r"L1\.unknown_key.*unknown key 'source'"):
        load_story_package(root)

    root = copied_package(tmp_path / "entry")
    patch_source(
        root,
        "scenes/1A.yaml",
        "entry_claims[k_scene_1a_entry].source",
        {"canonical_event_id": "missing_event"},
    )
    with pytest.raises(SourceError, match=r"L1\.unknown_key.*unknown key 'source'"):
        load_story_package(root)


def test_loader_rejects_same_scene_knowledge_prerequisite_cycle(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    _reveal(scene, "k_sl_1a_c_r2")["when"] = {"michelle_warning_known": True}
    _reveal(scene, "k_sl_1a_b_r2")["when"] = {"house_marked_for_return": True}
    _write_source(source, scene)

    with pytest.raises(StoryPackageError, match="prerequisite/reveal cycle"):
        load_story_package(root)


def test_loader_indexes_reachable_knowledge_prerequisites(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1B.yaml")
    _reveal(scene, "k_sl_1b_a_r1")["when"] = {"brandon_face_known": True}
    _write_source(source, scene)
    package = load_story_package(root)
    assert "k_sl_1b_a_r1" in package.knowledge_indexes.prerequisite_dependents["brandon_face_known"]


def test_loader_rejects_selectable_transition_trigger_without_must_convey(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, match = _source_document(root, "scenes/1A.match.yaml")
    _match_claim(match, "k_sl_1a_d_r1").pop("must_convey")
    _write_source(source, match)

    with pytest.raises(StoryPackageError, match="must_convey"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("field", "message"),
    [("facts", "fact .*home_search_window_narrowing.*not declared"), ("scene_frames", "no scene claim")],
)
def test_loader_rejects_incomplete_knowledge_catalog(tmp_path: Path, field: str, message: str) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    if field == "facts":
        scene["facts"].popitem()  # type: ignore[union-attr]
    else:
        scene["entry_claims"].clear()  # type: ignore[union-attr]
    _write_source(source, scene)
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        ("scenes/1A.yaml", "scene", "9Z", "no match entry"),
        ("scenes/1A.yaml", "location", "unknown_home", "entity reference .*does not resolve"),
        ("scenes/1A.yaml", "turns.min", 16, "turn allocations must be ordered"),
        ("scenes/1A.yaml", "outline", [], "outline"),
        ("scenes/1A.yaml", "exit.to", "9Z", "scene reference .*does not resolve"),
    ],
)
def test_loader_rejects_malformed_sources(tmp_path: Path, path: str, old: str, new: object, message: str) -> None:
    root = copied_package(tmp_path / "fallback")
    source, document = _source_document(root, path)
    if old == "turns.min":
        document["turns"]["min"] = new  # type: ignore[index]
    elif old == "exit.to":
        document["exit"]["to"] = new  # type: ignore[index]
    else:
        document[old] = new
    _write_source(source, document)
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_storylet_window_outside_parent_scene(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["reveals"][0]["guidance"]["window"]["latest_turn"] = 16  # type: ignore[index]
    _write_source(source, scene)
    with pytest.raises(StoryPackageError, match="escapes its scene pacing window"):
        load_story_package(root)


def test_loader_rejects_a_pacing_event_scheduled_past_its_scene_minimum(tmp_path: Path) -> None:
    """An event later than the floor can be walked past, so the package must not load.

    min_turns is the earliest a scene can be left. An event scheduled after it is
    one the player may never see, and a beat that never fires is exactly the class
    of defect a hosted playthrough should not be the first thing to notice.
    """

    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["beats"][0]["at_turn"] = scene["turns"]["min"] + 1  # type: ignore[index]
    _write_source(source, scene)

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
            "priority",
            "ambiguous priority",
            id="loader_rejects_ambiguous_transition_priority",
        ),
    ],
)
def test_loader_rejects_invalid_transition_graph(tmp_path: Path, transition: str, message: str) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    if transition == "priority":
        patch_source(root, "scenes/1A.yaml", "bridge[bridge_1a_actionable_lead].priority", 10)
        with pytest.raises(SourceError, match=r"L1\.unknown_key.*unknown key 'priority'"):
            load_story_package(root)
    else:
        scene["exit"]["to"] = "1A"  # type: ignore[index]
        scene["exit"]["when_all"] = ["broadcast_started"]  # type: ignore[index]
        _write_source(source, scene)
        with pytest.raises(StoryPackageError, match=message):
            load_story_package(root)


def test_loader_rejects_unknown_trigger_predicate_and_fallback(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["exit"]["when_all"] = ["unknown_fact"]  # type: ignore[index]
    _write_source(source, scene)
    with pytest.raises(StoryPackageError, match="fact .*unknown_fact.*not declared"):
        load_story_package(root)

    root = copied_package(tmp_path / "fallback")
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["placements"]["memory_card"]["parent"] = "missing_item"  # type: ignore[index]
    _write_source(source, scene)
    with pytest.raises(StoryPackageError, match="scene scope|does not resolve"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("path", "old", "new", "message"),
    [
        ("scenes/1A.yaml", "scene", "9Z", "no match entry"),
        ("scenes/1A.yaml", "participants", ["missing_character"], "entity reference .*does not resolve"),
        ("scenes/1A.yaml", "items", ["missing_item"], "entity reference .*does not resolve"),
        ("scenes/1A.yaml", "location", "missing_location", "entity reference .*does not resolve"),
        ("scenes/1A.yaml", "exit.to", "9Z", "scene reference .*does not resolve"),
    ],
)
def test_loader_rejects_remaining_boundary_errors(
    tmp_path: Path, path: str, old: str, new: object, message: str
) -> None:
    root = copied_package(tmp_path)
    source, document = _source_document(root, path)
    if old == "exit.to":
        document["exit"]["to"] = new  # type: ignore[index]
    else:
        document[old] = new
    _write_source(source, document)
    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def _delivery(root: Path, fact_id: str) -> tuple[Path, dict[str, object], dict[str, object]]:
    for scene_id in ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"):
        source, scene = _source_document(root, f"scenes/{scene_id}.yaml")
        fact = scene["facts"].get(fact_id)  # type: ignore[union-attr]
        if fact is not None and "delivery" in fact:
            return source, scene, fact["delivery"]
    raise KeyError(fact_id)


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
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["facts"]["continuity_initiative_known"].pop("delivery")  # type: ignore[index]
    _write_source(source, scene)

    with pytest.raises(StoryPackageError, match="continuity_initiative_known.*no FactDelivery"):
        load_story_package(root)


def test_loader_rejects_duplicate_fact_delivery(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["facts"]["michelle_warning_known"]["delivery"] = dict(  # type: ignore[index]
        scene["facts"]["continuity_initiative_known"]["delivery"]  # type: ignore[index]
    )
    scene["facts"]["michelle_warning_known"]["delivery"]["fact_id"] = "continuity_initiative_known"  # type: ignore[index]
    _write_source(source, scene)

    with pytest.raises(SourceError, match=r"L1\.unknown_key.*unknown key 'fact_id'"):
        load_story_package(root)


@pytest.mark.parametrize(
    ("fact_id", "field", "value", "message"),
    [
        pytest.param(
            "brandon_identified",
            "source_entity_id",
            "rebecca",
            "brandon_identified.*unknown key.*source_entity_id",
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
    source, scene, delivery = _delivery(root, fact_id)
    delivery[field] = value
    _write_source(source, scene)

    with pytest.raises(StoryPackageError, match=message):
        load_story_package(root)


def test_loader_rejects_delivery_for_world_only_fact(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["facts"]["patrol_on_scene"]["delivery"] = {  # type: ignore[index]
        "source_kind": "observation",
        "fallback_text": ("The patrol remains by the front door while the house stays under scrutiny."),
        "fact_id": "patrol_on_scene",
    }
    _write_source(source, scene)

    with pytest.raises(SourceError, match=r"L1\.unknown_key.*unknown key 'fact_id'"):
        load_story_package(root)

    root = copied_package(tmp_path / "unseen")
    source, scene = _source_document(root, "scenes/1A.yaml")
    scene["facts"]["patrol_on_scene"]["delivery"] = {  # type: ignore[index]
        "source_kind": "observation",
        "fallback_text": "The patrol remains by the front door.",
    }
    _write_source(source, scene)

    with pytest.raises(SourceError, match=r"L2\.delivery_unseen.*delivery for fact 'patrol_on_scene'"):
        load_story_package(root)


def test_loader_rejects_bridge_text_keys_that_do_not_match_transition_ids(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, scene = _source_document(root, "scenes/1A.yaml")
    patch_source(root, "scenes/1A.yaml", "bridge_text", {"t_1a_1b": "departure"})

    with pytest.raises(SourceError, match=r"L1\.unknown_key.*unknown key 'bridge_text'"):
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
