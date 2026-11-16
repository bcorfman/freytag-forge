from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import storygame.story_source as story_source
from storygame.story_source.reader import SourceTree


def _write_check(path: Path, module: str, body: str) -> None:
    (path / module).write_text(body, encoding="utf-8")


def test_discovery_and_execution_are_sorted_and_layered(tmp_path: Path, monkeypatch: object) -> None:
    package_path = tmp_path / "story_source_modules"
    package_path.mkdir()
    _write_check(
        package_path,
        "l1_alpha.py",
        dedent(
            """
            from storygame.story_source.checks import layer1_check
            from storygame.story_source.diagnostics import Diagnostic

            @layer1_check
            def first(tree):
                if tree.root.name != "registry-root":
                    return []
                return [Diagnostic("L1.first", "", "", "", "alpha-first")]

            @layer1_check
            def second(tree):
                if tree.root.name != "registry-root":
                    return []
                return [Diagnostic("L1.second", "", "", "", "alpha-second")]
            """
        ),
    )
    _write_check(
        package_path,
        "l1_zeta.py",
        dedent(
            """
            from storygame.story_source.checks import layer1_check
            from storygame.story_source.diagnostics import Diagnostic

            @layer1_check
            def check(tree):
                if tree.root.name != "registry-root":
                    return []
                return [Diagnostic("L1.third", "", "", "", "zeta")]
            """
        ),
    )
    _write_check(
        package_path,
        "l2_beta.py",
        dedent(
            """
            from storygame.story_source.checks import layer2_check
            from storygame.story_source.diagnostics import Diagnostic

            @layer2_check
            def check(tree):
                if tree.root.name == "registry-root":
                    return [Diagnostic("L2.ran", "", "", "", "layer two ran")]
                return []
            """
        ),
    )

    package = story_source.__path__
    monkeypatch.setattr(story_source, "__path__", [str(package_path), *package])
    story_source.checks.discover()
    tree = SourceTree(tmp_path / "registry-root", {})

    layer_one = story_source.checks.run_layer1(tree)
    layer_two = story_source.checks.run_layer2(tree)

    assert [diagnostic.message for diagnostic in layer_one] == ["alpha-first", "alpha-second", "zeta"]
    assert [diagnostic.message for diagnostic in layer_two] == ["layer two ran"]


def test_layer_two_is_skipped_after_syntax_diagnostic(tmp_path: Path, monkeypatch: object) -> None:
    package_path = tmp_path / "story_source_modules"
    package_path.mkdir()
    _write_check(
        package_path,
        "l2_syntax_skip.py",
        dedent(
            """
            from storygame.story_source.checks import layer2_check
            from storygame.story_source.diagnostics import Diagnostic

            @layer2_check
            def check(tree):
                return [Diagnostic("L2.must_skip", "", "", "", "must not run")]
            """
        ),
    )
    package = story_source.__path__
    monkeypatch.setattr(story_source, "__path__", [str(package_path), *package])
    root = tmp_path / "syntax-root"
    root.mkdir()
    (root / "broken.yaml").write_text("schema: [\n", encoding="utf-8")

    diagnostics = story_source.check_source_tree(root)

    assert [diagnostic.name for diagnostic in diagnostics] == ["L1.syntax"]
