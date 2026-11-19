"""Layer and compiler tests for the optional scene order mapping."""

from __future__ import annotations

from storygame.story_source import check_source_tree
from tests.story_source.helpers import DELETE, compiled_story_copy, load_compiled_copy, patch_source


def _scene_ids(package, attribute: str, scene_id: str, scene_for) -> list[str]:
    records = getattr(package, attribute)
    if attribute == "pacing":
        records = records.events
    if attribute == "knowledge":
        records = records.knowledge
    return [item.id if hasattr(item, "id") else item.fact_id for item in records if scene_for(item) == scene_id]


def test_order_key_reorders_each_supported_kind_and_keeps_routes_natural(tmp_path) -> None:
    root = compiled_story_copy(tmp_path)
    source = root / "source"
    for scene_id in ("1A", "1B", "1C"):
        patch_source(source, f"scenes/{scene_id}.yaml", "order", DELETE)
    baseline = load_compiled_copy(root)
    storylet_ids = _scene_ids(baseline, "storylets", "1A", lambda item: item.scene_id)
    delivery_ids = _scene_ids(baseline, "deliveries", "1B", lambda item: item.scene_id)
    claim_ids = _scene_ids(
        baseline, "knowledge", "1C", lambda item: item.available_in_scenes[0] if item.available_in_scenes else None
    )
    event_ids = _scene_ids(baseline, "pacing", "1A", lambda item: item.scene_id)

    patch_source(
        source,
        "scenes/1A.yaml",
        "order",
        {"storylets": [storylet_ids[-1]], "pacing_events": [event_ids[-1]]},
    )
    patch_source(source, "scenes/1B.yaml", "order", {"deliveries": [delivery_ids[-1]]})
    patch_source(source, "scenes/1C.yaml", "order", {"knowledge": [claim_ids[-1]]})

    ordered = load_compiled_copy(root)
    assert [item.id for item in ordered.storylets if item.scene_id == "1A"] == [storylet_ids[-1], *storylet_ids[:-1]]
    assert [item.id for item in ordered.storylet_routes.storylets if item.scene_id == "1A"] == [
        item.id for item in baseline.storylet_routes.storylets if item.scene_id == "1A"
    ]
    assert [item.fact_id for item in ordered.deliveries if item.scene_id == "1B"] == [
        delivery_ids[-1],
        *delivery_ids[:-1],
    ]
    assert [item.id for item in ordered.knowledge.knowledge if item.available_in_scenes == ("1C",)] == [
        claim_ids[-1],
        *claim_ids[:-1],
    ]
    assert [item.id for item in ordered.pacing.events if item.scene_id == "1A"] == [event_ids[-1], *event_ids[:-1]]


def test_absent_order_key_changes_nothing(tmp_path) -> None:
    root = compiled_story_copy(tmp_path)
    package = load_compiled_copy(root)

    assert [item.id for item in package.storylets if item.scene_id == "3A"] == [
        item.id for item in package.storylet_routes.storylets if item.scene_id == "3A"
    ]


def test_order_unknown_and_duplicate_ids_are_rejected(tmp_path) -> None:
    root = compiled_story_copy(tmp_path)
    source = root / "source"
    patch_source(source, "scenes/1A.yaml", "order", {"storylets": ["missing_storylet", "missing_storylet"]})

    diagnostics = check_source_tree(source)

    assert [diagnostic.name for diagnostic in diagnostics].count("L2.order_id") >= 2


def test_order_wrong_shape_is_rejected(tmp_path) -> None:
    root = compiled_story_copy(tmp_path)
    source = root / "source"
    patch_source(source, "scenes/1A.yaml", "order", {"storylets": "SL-1A-E"})

    diagnostics = check_source_tree(source)

    assert any(diagnostic.name == "L1.type" for diagnostic in diagnostics)
