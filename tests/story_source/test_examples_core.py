from __future__ import annotations

from pathlib import Path

from tests.story_source.helpers import copy_fixture, require_story_source


def test_checker_reports_a_reject_that_matches(tmp_path: Path) -> None:
    """A reject line that satisfies the claim is reported as a reject failure."""

    root = copy_fixture("mini_ok", tmp_path / "source")
    examples = tmp_path / "1A.yaml"
    examples.write_text(
        """schema: 1
scene: 1A
claims:
  k_sl_1a_b_r0:
    accept: []
    reject:
      - search beneath the KMS drawer for Michelle's taped memory card
shared: {}
""",
        encoding="utf-8",
    )

    failures = require_story_source().check_examples(root, examples)

    assert len(failures) == 1
    assert failures[0].kind == "reject"
    assert failures[0].claim_id == "k_sl_1a_b_r0"
