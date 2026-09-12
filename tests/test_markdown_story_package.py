from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.validation import unconveyed_terms
from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.models import ItemPlacement

PACKAGE = Path("data/stories/continuity-initiative")


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
    assert len(package.storylets) == 30
    assert all(storylet.source_links and storylet.sections["Protected boundary"] for storylet in package.storylets)
    assert package.knowledge.schema_version == "2.0"
    assert package.scenes[0].metadata.item_placements == {
        "michelle_phone": "on the kitchen floor",
        "kristin_laptop": "in Kristin's truck outside the house",
        "memory_card": ItemPlacement(
            placement="taped under a drawer in Michelle's workstation",
            while_fact_false="memory_card_in_kristins_custody",
        ),
    }
    assert set(package.knowledge_indexes.facts_to_knowledge) == set(package.world.facts)
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


def test_loader_rejects_item_placement_for_an_item_not_in_the_scene(tmp_path: Path) -> None:
    package = copied_package(tmp_path)
    plot = package / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    contents = contents.replace("  michelle_phone: on the kitchen floor\n", "  transit_card: on the table\n", 1)
    plot.write_text(contents, encoding="utf-8")

    with pytest.raises(StoryPackageError, match="scene 1A.*transit_card"):
        load_story_package(package)


def test_scene_without_item_placements_loads_with_an_empty_mapping() -> None:
    package = load_story_package(PACKAGE)

    assert package.scenes[1].metadata.item_placements == {}


def test_guarded_item_placement_loads_with_text_and_guard_fact(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8")
    contents = contents.replace(
        "  memory_card:\n"
        "    placement: taped under a drawer in Michelle's workstation\n"
        "    while_fact_false: memory_card_in_kristins_custody\n",
        "  memory_card:\n"
        "    placement: taped beneath the workstation drawer\n"
        "    while_fact_false: michelle_abduction_suspicion\n",
        1,
    )
    plot.write_text(contents, encoding="utf-8")

    placement = load_story_package(root).scenes[0].metadata.item_placements["memory_card"]

    assert placement.placement == "taped beneath the workstation drawer"
    assert placement.while_fact_false == "michelle_abduction_suspicion"


def test_bare_string_item_placement_remains_a_string() -> None:
    placement = load_story_package(PACKAGE).scenes[0].metadata.item_placements["michelle_phone"]

    assert placement == "on the kitchen floor"


def test_loader_rejects_item_placement_guard_for_an_unknown_fact(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    plot = root / "plot.md"
    contents = plot.read_text(encoding="utf-8").replace(
        "  michelle_phone: on the kitchen floor\n",
        "  michelle_phone:\n    placement: on the kitchen floor\n    while_fact_false: undeclared_fact\n",
        1,
    )
    plot.write_text(contents, encoding="utf-8")

    with pytest.raises(StoryPackageError, match="scene 1A.*michelle_phone.*undeclared_fact"):
        load_story_package(root)


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
    details = (
        "**Details:** Michelle's phone on the kitchen floor; missing tablet and work bag; overturned workstation "
        "chair; "
        "forced back door; KMS initials in drawer\n"
    )
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
    "Michelle finds the memory card and plays the damaged recording. The warning concerns emergency broadcasts."
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


def test_legacy_evidence_without_delivery_text_still_loads() -> None:
    package = load_story_package(PACKAGE)

    assert any(item.action_evidence for item in package.knowledge.knowledge)
    assert all(item.delivery_text is None for item in package.knowledge.knowledge)


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
    candidate["requires"] = [{"fact_id": "michelle_abduction_suspicion", "equals": True}]
    source.write_text(yaml.safe_dump(catalog, sort_keys=False))
    package = load_story_package(root)
    assert "k_sl_1b_a_r1" in package.knowledge_indexes.prerequisite_dependents["michelle_abduction_suspicion"]


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
        ("world.yaml", "mcgehee_home", "unknown_home", "unknown entities"),
        (
            "pacing.yaml",
            "min_turns: 2\n  nudge_after_turns: 4",
            "min_turns: 3\n  nudge_after_turns: 2",
            "turn allocations",
        ),
        ("storylets.md", "**Pacing impact**", "**Impact**", "lacks sections"),
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
    source.write_text(source.read_text().replace("latest: `turn 3`", "latest: `turn 6`", 1))
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


def test_loader_rejects_transition_dependency_cycle(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "pacing.yaml"
    source.write_text(
        source.read_text()
        + "\n"
        + (
            "- {id: t_cycle, source_scene_id: 3C, target_scene_id: 1A, priority: 1, "
            "triggers: [{fact_id: broadcast_started, equals: true}]}\n"
        )
    )
    with pytest.raises(StoryPackageError, match="dependency cycle"):
        load_story_package(root)


def test_loader_rejects_unknown_trigger_predicate_and_fallback(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    pacing = root / "pacing.yaml"
    pacing.write_text(pacing.read_text().replace("fact_id: michelle_lead_actionable", "fact_id: unknown_fact", 1))
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


def test_loader_rejects_ambiguous_transition_priority(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "pacing.yaml"
    source.write_text(
        source.read_text()
        + "\n"
        + (
            "- {id: t_tie, source_scene_id: 1A, target_scene_id: 1C, priority: 10, "
            "triggers: [{fact_id: michelle_lead_actionable, equals: true}, "
            "{fact_id: patrol_return_pressure, equals: true}, "
            "{fact_id: memory_card_in_kristins_custody, equals: true}]}\n"
        )
    )
    with pytest.raises(StoryPackageError, match="ambiguous priority"):
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

    assert set(deliveries) == required & player_safe
    assert required <= set(deliveries) | world_only
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


def test_loader_rejects_delivery_source_outside_scene_participants(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, handoffs = _handoffs(root)
    delivery = next(item for item in handoffs["deliveries"] if item["fact_id"] == "brandon_identified")  # type: ignore[index]
    delivery["source_entity_id"] = "rebecca"
    source.write_text(yaml.safe_dump(handoffs, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="brandon_identified.*source entity.*rebecca.*absent"):
        load_story_package(root)


def test_loader_rejects_delivery_fallback_that_misses_a_required_phrase(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source, handoffs = _handoffs(root)
    delivery = next(item for item in handoffs["deliveries"] if item["fact_id"] == "facility_proof")  # type: ignore[index]
    delivery["fallback_text"] = "The terminal is quiet and empty."
    source.write_text(yaml.safe_dump(handoffs, sort_keys=False), encoding="utf-8")

    with pytest.raises(StoryPackageError, match="facility_proof.*fallback_text.*fresh tire tracks"):
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
