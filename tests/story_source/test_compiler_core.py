"""Focused compiler-core coverage beyond the fixture-specific gate tests."""

# NOTE: Loader cycle wording is unstable, so the public name is asserted instead.
# NOTE: F01 is a reduced slice; generated scene-entry facts and omitted legacy producers are compiler inputs.
# NOTE: Fact IDs declared by source are asserted as a subset because entry facts are required compiler derivations.

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source


def _canonical(package: object) -> str:
    """Return the contract's canonical package JSON."""

    return json.dumps(package.model_dump(mode="json", by_alias=True), sort_keys=True, separators=(",", ":"))


def test_compiler_runs_inherited_loader_checks(tmp_path: Path) -> None:
    """A source mutation that passes layers one and two reaches the loader."""

    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(
        root,
        "scenes/2C.yaml",
        "reveals[michelle_changes_the_choice].variants.transmit.outcome.advantages",
        ["evidence_not_transmitted"],
    )
    assert story_source.check_source_tree(root) == []
    with pytest.raises(story_source.SourceError) as error:
        story_source.compile_source_tree(root)
    assert any(diagnostic.name == "LOADER" for diagnostic in error.value.diagnostics)


def test_compiler_is_deterministic_and_preserves_source_record_ids(tmp_path: Path) -> None:
    """Repeated compilation keeps canonical JSON and all authored record IDs."""

    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    first = story_source.compile_source_tree(root)
    second = story_source.compile_source_tree(root)
    assert _canonical(first) == _canonical(second)

    tree = load_tree(root)
    source_scenes = {tree[f"scenes/{scene}.yaml"]["scene"] for scene in tree["story.yaml"]["scenes"]}
    assert {scene.scene_id for scene in first.scenes} == source_scenes
    source_claims = {
        claim_id for path, value in tree.items() if path.endswith(".match.yaml") for claim_id in value["claims"]
    }
    assert {claim.id for claim in first.knowledge.knowledge} == source_claims
    source_deliveries = {
        fact_id
        for path, value in tree.items()
        if path.endswith(".yaml") and not path.endswith(".match.yaml")
        for fact_id, record in (value.get("facts", {}) or {}).items()
        if "delivery" in record
    }
    assert {delivery.fact_id for delivery in first.deliveries} == source_deliveries
    source_incidents = {
        record["id"]
        for path, value in tree.items()
        if path.endswith(".yaml") and not path.endswith(".match.yaml")
        for record in value.get("incidents", ())
    }
    assert {incident.id for incident in first.incidents} == source_incidents
    source_facts = {
        fact_id
        for path, value in tree.items()
        if path.endswith(".yaml") and not path.endswith(".match.yaml")
        for fact_id in (value.get("facts", {}) or {})
    }
    assert source_facts <= set(first.world.facts)
