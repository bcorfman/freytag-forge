from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import StoryPackageError, load_story_package

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
        ("pacing.yaml", "latest_seconds: 120", "latest_seconds: 30", "pacing timestamps"),
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
    source.write_text(source.read_text().replace("latest: `00:05:00`", "latest: `00:05:01`", 1))
    with pytest.raises(StoryPackageError, match="escapes its scene pacing window"):
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
        ("storylets.md", "earliest: `00:00:00`", "earliest: `00:99:00`", "invalid timestamp"),
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
            "{fact_id: patrol_return_pressure, equals: true}]}\n"
        )
    )
    with pytest.raises(StoryPackageError, match="ambiguous priority"):
        load_story_package(root)
