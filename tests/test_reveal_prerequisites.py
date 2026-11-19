from __future__ import annotations

import re
from pathlib import Path

import pytest

from storygame.story_package import load_story_package
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

PACKAGE = Path("data/stories/continuity-initiative")


def test_continuity_package_loads() -> None:
    package = load_story_package(PACKAGE)

    assert package.story_id == "continuity_initiative"


def test_loader_rejects_required_reveal_with_unproducible_scene_prerequisite(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(
        root / "source",
        "scenes/2C.yaml",
        "reveals[sl_2c_d].variants.r3.when.evidence_gap_development_record",
        True,
    )

    with pytest.raises(
        SourceError,
        match=re.escape(
            "scene 2C reveal 'k_sl_2c_d_r3' requires 'evidence_gap_development_record', which scene entry does not "
            "guarantee and the scene cannot produce"
        ),
    ):
        load_compiled_copy(root)
