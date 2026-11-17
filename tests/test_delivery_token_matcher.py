from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from storygame.story_package import load_story_package
from storygame.story_package.loader import _delivery_token_matcher
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, patch_source

PACKAGE = Path("data/stories/continuity-initiative")


def test_delivery_fact_id_is_rejected_as_an_implementation_only_token(tmp_path: Path) -> None:
    package_root = compiled_story_copy(tmp_path)
    fact_id = "continuity_initiative_known"
    source_path = package_root / "source" / "scenes" / "1A.yaml"
    data = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    reveal = next(
        reveal
        for reveal in data["reveals"]
        if any(variant.get("claim_id") == "k_sl_1a_a_r1" for variant in reveal["variants"].values())
    )
    variants = reveal["variants"]
    variant = next(variant for variant in variants.values() if variant.get("claim_id") == "k_sl_1a_a_r1")
    variant["text"] += f" {fact_id}."
    patch_source(package_root / "source", "scenes/1A.yaml", f"reveals[{reveal['id']}].variants", variants)

    with pytest.raises(SourceError, match=rf"implementation-only token '{fact_id}'"):
        load_compiled_copy(package_root)


def test_unmodified_package_loads() -> None:
    assert load_story_package(PACKAGE)


def test_delivery_token_matcher_respects_token_boundaries() -> None:
    package = load_story_package(PACKAGE)
    fact_id = "continuity_initiative_known"
    matcher = _delivery_token_matcher(package)

    assert matcher.search(f"x{fact_id}".casefold()) is None
    assert matcher.search(f"{fact_id}-y".casefold()) is None
    assert matcher.search(f"See {fact_id}.".casefold())
