"""AST checks for the story/world architecture boundaries.

Rule 2 intentionally uses a name heuristic for expressions that denote a
``World``.  Aliasing a World to another name evades this heuristic.
Scene and item identifiers are not included in rule 3 because they produce
false positives in the current runtime; the checked sets are NPC IDs, the
protagonist ID, and storylet IDs.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from storygame.story_package.loader import load_story_package

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_DOC = "docs/contributor-guide/runtime-and-authoring-boundaries.md"


def _tree(source: str) -> ast.AST:
    return ast.parse(textwrap.dedent(source))


def _line(node: ast.AST) -> int:
    return getattr(node, "lineno", 0)


def _final_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _imports_storygame(source: str) -> list[int]:
    """Return lines containing direct or nested imports of storygame."""
    violations: list[int] = []
    for node in ast.walk(_tree(source)):
        if isinstance(node, ast.Import):
            if any(alias.name == "storygame" or alias.name.startswith("storygame.") for alias in node.names):
                violations.append(_line(node))
        elif (
            isinstance(node, ast.ImportFrom)
            and node.module
            and (node.module == "storygame" or node.module.startswith("storygame."))
        ):
            violations.append(_line(node))
    return violations


def _denotes_world(node: ast.AST) -> bool:
    name = _final_name(node)
    if name is not None and (name == "world" or name.endswith("_world")):
        return True
    if isinstance(node, ast.Call):
        return _final_name(node.func) in {"world", "_world", "world_for"}
    return False


def _world_internal_reads(source: str) -> list[int]:
    """Return lines reading forbidden World internals using the documented heuristic."""
    forbidden = {"schema", "backend", "make_fact", "resolver"}
    violations: list[int] = []
    for node in ast.walk(_tree(source)):
        if not isinstance(node, ast.Attribute):
            continue
        is_private = node.attr.startswith("_") and not node.attr.startswith("__")
        if (node.attr in forbidden or is_private) and _denotes_world(node.value):
            violations.append(_line(node))
    return violations


def _story_identifiers() -> set[str]:
    identifiers: set[str] = set()
    story_roots = sorted(path.parent.parent for path in (ROOT / "data" / "stories").rglob("source/story.yaml"))
    for story_root in story_roots:
        package = load_story_package(story_root)
        identifiers.add(package.protagonist_id)
        identifiers.update(character.id for character in package.world.npcs)
        identifiers.update(storylet.id for storylet in package.storylets)
        identifiers.update(route.id for route in package.storylet_routes.storylets)
    return identifiers


def _runtime_story_collisions(source: str, identifiers: set[str]) -> list[int]:
    """Return lines whose literal is an exact story-specific identifier."""
    return [
        _line(node)
        for node in ast.walk(_tree(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in identifiers
    ]


def _source_files(*directories: str) -> list[Path]:
    return sorted(path for directory in directories for path in (ROOT / directory).rglob("*.py"))


def _failure(rule: str, violations: list[str], repair: str) -> str:
    details = "\n".join(f"{violation}" for violation in violations)
    return f"Rule {rule} violations:\n{details}\nHow to repair: {repair}\nSee {BOUNDARY_DOC}."


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("def f():\n    import storygame.runtime\n", [2]),
        ("from worldkeeper import World\n", []),
        ("import storygames\n", []),
    ],
)
def test_import_detector(source: str, expected: list[int]) -> None:
    assert _imports_storygame(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("world.backend\nself._world().schema\nworld_for(p, f).resolver\n", [1, 2, 3]),
        ("self._x.backend\npackage.world.items\nmodule.backend\n", []),
        ("self.world._private\n", [1]),
    ],
)
def test_world_internal_detector(source: str, expected: list[int]) -> None:
    assert _world_internal_reads(source) == expected


def test_worldkeeper_does_not_import_storygame() -> None:
    violations = [
        f"{path.relative_to(ROOT)}:{line}: imports storygame"
        for path in _source_files("packages/worldkeeper")
        for line in _imports_storygame(path.read_text(encoding="utf-8"))
    ]
    assert not violations, _failure(
        "1",
        violations,
        "move storygame-dependent adaptation into storygame/runtime/world_model.py or another storygame module",
    )


def test_storygame_factory_and_bench_do_not_read_world_internals() -> None:
    adapter = ROOT / "storygame" / "runtime" / "world_model.py"
    violations = [
        f"{path.relative_to(ROOT)}:{line}: reads a World implementation internal"
        for directory in ("storygame", "factory", "bench")
        for path in _source_files(directory)
        if path != adapter
        for line in _world_internal_reads(path.read_text(encoding="utf-8"))
    ]
    assert not violations, _failure(
        "2",
        violations,
        "World-state traversal belongs in a World method; add its tests in packages/worldkeeper/tests/.",
    )


def test_runtime_stays_story_agnostic() -> None:
    identifiers = _story_identifiers()
    violations = [
        f"{path.relative_to(ROOT)}:{line}: contains a story-specific identifier literal"
        for path in _source_files("storygame/runtime")
        for line in _runtime_story_collisions(path.read_text(encoding="utf-8"), identifiers)
    ]
    assert not violations, _failure(
        "3",
        violations,
        "move story-specific identifiers into validated package data and keep runtime code story-agnostic",
    )
