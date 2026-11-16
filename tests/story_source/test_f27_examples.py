from __future__ import annotations

from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree

_EXAMPLES = """schema: 1
scene: 1A
claims:
  k_sl_1a_b_r0:
    accept:
      - search beneath the KMS drawer for Michelle's taped memory card
      - search beneath the KMS drawer for Michelle's memory card
    reject:
      - search for the memory card
shared: {}
"""


def test_examples_are_separate_and_only_add_the_1a_examples_file(tmp_path: Path) -> None:
    baseline = copy_fixture("mini_ok", tmp_path / "baseline")
    root = copy_fixture("mini_ok", tmp_path / "changed")
    examples = root / "examples" / "1A.yaml"
    examples.parent.mkdir()
    examples.write_text(_EXAMPLES, encoding="utf-8")

    baseline_tree = load_tree(baseline)
    changed_tree = load_tree(root)
    assert set(changed_tree) == set(baseline_tree) | {"examples/1A.yaml"}
    assert all(changed_tree[path] == baseline_tree[path] for path in baseline_tree)
    assert changed_tree["examples/1A.yaml"] == {
        "schema": 1,
        "scene": "1A",
        "claims": {
            "k_sl_1a_b_r0": {
                "accept": [
                    "search beneath the KMS drawer for Michelle's taped memory card",
                    "search beneath the KMS drawer for Michelle's memory card",
                ],
                "reject": ["search for the memory card"],
            }
        },
        "shared": {},
    }


def test_examples_source_tree_is_clean_when_compiler_exists(tmp_path: Path) -> None:
    story_source = pytest.importorskip("storygame.story_source")
    root = copy_fixture("mini_ok", tmp_path)

    assert story_source.check_source_tree(root) == []
