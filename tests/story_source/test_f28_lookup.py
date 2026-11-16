from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tests.story_source.helpers import copy_fixture, load_tree, require_story_source

_LOOKUP_BRIDGE = {
    "id": "bridge_1a_lookup",
    "commits": {"memory_card_recovered": True},
    "fallback_text": "Kristin starts the truck and heads for the park, avoiding checkpoints and emergency patrols.",
}


def _add_bridge(root: Path) -> None:
    path = root / "scenes/1A.yaml"
    document = load_tree(root)["scenes/1A.yaml"]
    ordered: dict[str, object] = {}
    for key, value in document.items():
        if key == "exit":
            ordered["bridge"] = [_LOOKUP_BRIDGE]
        ordered[key] = value
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(ordered, stream, sort_keys=False, width=10_000, allow_unicode=True)


def test_lookup_fixture_adds_only_one_bridge_record(tmp_path: Path) -> None:
    baseline = copy_fixture("mini_ok", tmp_path / "baseline")
    root = copy_fixture("mini_ok", tmp_path / "changed")
    _add_bridge(root)

    baseline_tree = load_tree(baseline)
    changed_tree = load_tree(root)
    assert set(changed_tree) == set(baseline_tree)
    for path in baseline_tree:
        if path == "scenes/1A.yaml":
            changed = dict(changed_tree[path])
            original = dict(baseline_tree[path])
            assert changed.pop("bridge") == [_LOOKUP_BRIDGE]
            assert changed == original
        else:
            assert changed_tree[path] == baseline_tree[path]
    assert list(changed_tree["scenes/1A.yaml"])[-2:] == ["bridge", "exit"]


def test_every_contract_lookup_kind_resolves_and_unknown_addresses_fail(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    _add_bridge(root)
    clean_root = copy_fixture("mini_ok", tmp_path / "clean")

    assert story_source.check_source_tree(root) == []
    assert story_source.check_source_tree(clean_root) == []
    package = story_source.compile_source_tree(root)
    text_addresses = (
        "scene:1A.title",
        "fact:memory_card_recovered.purpose",
        "delivery:continuity_initiative_known.fallback_text",
        "claim:k_sl_1a_b_r0.says",
        "beat:patrol_leaves_1a.say[-1].text",
        "exit:t_1a_1b.bridge",
        "bridge:bridge_1a_lookup.fallback_text",
        "outline:1A.1.title",
        "ending:story.marker",
        "entity:memory_card.name",
        "reveal:find_card.title",
        "variant:find_card/quiet.intent",
        "part:find_card/find_lead",
    )
    for address in text_addresses:
        assert story_source.story_text(address, package=package)
    assert story_source.story_value("outcome:i_2c_rebecca_corridor/committed_to_transmit.advantages", package=package)

    template = story_source.story_text("claim:k_sl_1a_b_r0.text", package=package, source=True)
    assert "{find_lead}" in template
    assert "{find_lead}" not in story_source.story_text("claim:k_sl_1a_b_r0.text", package=package)
    assert story_source.story_text("part:find_card/find_lead", package=package) in story_source.story_text(
        "claim:k_sl_1a_b_r0.text", package=package
    )
    with pytest.raises(KeyError, match="claim:no_such_claim.says"):
        story_source.story_text("claim:no_such_claim.says", package=package)
