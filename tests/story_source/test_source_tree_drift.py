"""Keep the committed default-story source tree synchronized with its converter output."""

from pathlib import Path

from storygame.story_package.loader import load_story_package
from storygame.story_source import check_source_tree, compile_source_tree
from storygame.story_source.convert import write_source_tree

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
SOURCE_ROOT = PACKAGE_ROOT / "source"


def _relative_files(root: Path) -> set[Path]:
    return {path.relative_to(root) for path in root.rglob("*") if path.is_file()}


def test_committed_source_tree_matches_a_fresh_conversion(tmp_path: Path) -> None:
    legacy = load_story_package(PACKAGE_ROOT)
    write_source_tree(legacy, tmp_path)

    committed_files = _relative_files(SOURCE_ROOT)
    generated_files = _relative_files(tmp_path)
    missing = sorted(committed_files - generated_files)
    extra = sorted(generated_files - committed_files)
    differing = sorted(
        path
        for path in committed_files & generated_files
        if (SOURCE_ROOT / path).read_bytes() != (tmp_path / path).read_bytes()
    )
    message = (
        "Committed source tree drift detected.\n"
        f"Missing: {missing[:20]}\n"
        f"Extra: {extra[:20]}\n"
        f"Differing: {differing[:20]}\n"
        "Regenerate by running write_source_tree on the legacy package into "
        "data/stories/continuity-initiative/source."
    )
    assert not missing and not extra and not differing, message


def test_committed_source_tree_is_valid_and_compiles() -> None:
    diagnostics = check_source_tree(SOURCE_ROOT)
    assert not diagnostics, f"Source tree diagnostics: {diagnostics}"

    legacy = load_story_package(PACKAGE_ROOT)
    compiled = compile_source_tree(SOURCE_ROOT)
    legacy_scene_ids = [scene.metadata.scene_id for scene in legacy.scenes]
    compiled_scene_ids = [scene.metadata.scene_id for scene in compiled.scenes]
    assert compiled_scene_ids == legacy_scene_ids
