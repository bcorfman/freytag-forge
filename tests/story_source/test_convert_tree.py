"""End-to-end checks for assembling the default story source tree."""

from pathlib import Path

from storygame.story_package.loader import load_story_package
from storygame.story_source import check_source_tree, compile_source_tree
from storygame.story_source.convert import write_source_tree

PACKAGE_ROOT = Path("data/stories/continuity-initiative")


def _assert_same_ids(label: str, expected: set[str], actual: set[str]) -> None:
    """Assert an ID set with useful differences in the failure message."""

    assert actual == expected, f"{label}: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"


def test_default_story_tree_validates_compiles_and_preserves_ids(tmp_path: Path) -> None:
    """The assembled default tree is valid and retains every legacy record ID."""

    legacy = load_story_package(PACKAGE_ROOT)
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    write_source_tree(legacy, first_root)
    write_source_tree(legacy, second_root)

    assert check_source_tree(first_root) == []
    compiled = compile_source_tree(first_root)

    _assert_same_ids(
        "scenes",
        {scene.metadata.scene_id for scene in legacy.scenes},
        {scene.metadata.scene_id for scene in compiled.scenes},
    )
    _assert_same_ids(
        "claims",
        {claim.id for claim in legacy.knowledge.knowledge},
        {claim.id for claim in compiled.knowledge.knowledge},
    )
    _assert_same_ids(
        "storylets",
        {storylet.id for storylet in legacy.storylets},
        {storylet.id for storylet in compiled.storylets},
    )
    _assert_same_ids(
        "realizations",
        {realization.id for route in legacy.storylet_routes.storylets for realization in route.realizations},
        {realization.id for route in compiled.storylet_routes.storylets for realization in route.realizations},
    )
    _assert_same_ids(
        "delivery facts", {item.fact_id for item in legacy.deliveries}, {item.fact_id for item in compiled.deliveries}
    )
    _assert_same_ids(
        "pacing events", {item.id for item in legacy.pacing.events}, {item.id for item in compiled.pacing.events}
    )
    _assert_same_ids("incidents", {item.id for item in legacy.incidents}, {item.id for item in compiled.incidents})
    _assert_same_ids("facts", set(legacy.fact_ids), set(compiled.fact_ids))

    first_files = sorted(path.relative_to(first_root) for path in first_root.rglob("*.yaml"))
    second_files = sorted(path.relative_to(second_root) for path in second_root.rglob("*.yaml"))
    assert first_files == second_files
    for relative_path in first_files:
        assert (first_root / relative_path).read_bytes() == (second_root / relative_path).read_bytes()
