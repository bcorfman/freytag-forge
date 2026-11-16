from __future__ import annotations

from pathlib import Path

from tests.story_source.helpers import copy_fixture, load_tree, require_story_source

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


def _write_examples(tmp_path: Path) -> Path:
    """Write the examples file outside the source tree, at the contract's layout (section 10.1)."""

    examples = tmp_path / "tests" / "fixtures" / "story_examples" / "continuity-initiative" / "1A.yaml"
    examples.parent.mkdir(parents=True)
    examples.write_text(_EXAMPLES, encoding="utf-8")
    return examples


def test_examples_are_separate_and_only_add_the_1a_examples_file(tmp_path: Path) -> None:
    baseline = copy_fixture("mini_ok", tmp_path / "baseline")
    root = copy_fixture("mini_ok", tmp_path / "changed")
    examples = _write_examples(tmp_path)

    baseline_tree = load_tree(baseline)
    changed_tree = load_tree(root)
    assert changed_tree == baseline_tree
    assert load_tree(examples.parent)["1A.yaml"] == {
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
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)

    assert story_source.check_source_tree(root) == []


def test_checker_names_the_failing_group_and_smallest_word(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path / "source")
    examples = _write_examples(tmp_path)

    failures = story_source.check_examples(root, examples)

    assert len(failures) == 1
    failure = failures[0]
    assert failure.claim_id == "k_sl_1a_b_r0"
    assert failure.kind == "accept"
    assert failure.line == "search beneath the KMS drawer for Michelle's memory card"
    assert failure.group == 1  # the `[taped]` group of must_convey
    assert failure.missing == "taped"
