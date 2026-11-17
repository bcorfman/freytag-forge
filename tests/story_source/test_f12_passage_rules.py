# NOTE: Keep must_convey on text_when claims because selectable scene-transition claims require it.
from __future__ import annotations

import copy
from pathlib import Path

import yaml

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source

_SAY_ENTRIES = [
    {"when": {"card_challenged": True}, "text": "The first matching patrol line."},
    {"when": {"patrol_on_scene": True}, "text": "The second matching patrol line."},
    {"text": "The default patrol line."},
]
_TEXT_WHEN_ENTRIES = [
    {
        "when": ["ticket_header_matched"],
        "text": "{sending} {route_close} The ticket header matches.",
    },
    {
        "when": ["evidence_ready_to_transmit"],
        "text": "{sending} {route_close} The evidence is ready to transmit.",
    },
]
_ENDING_ADDITIONS = [
    {"when": ["evacuation_complete"], "text": "The first aftermath addition."},
    {"when": ["purge_recovery_ready"], "text": "The second aftermath addition."},
]


def _patch_passage_rules(root: Path) -> None:
    patch_source(root, "scenes/1A.yaml", "beats[patrol_leaves_1a].say", _SAY_ENTRIES)
    patch_source(
        root,
        "scenes/2C.yaml",
        "reveals[michelle_changes_the_choice].variants.transmit.text_when",
        _TEXT_WHEN_ENTRIES,
    )
    scene = load_tree(root)["scenes/2C.yaml"]
    assert isinstance(scene, dict)
    ending = dict(scene["ending"])
    ending["additions"] = _ENDING_ADDITIONS
    ending = {key: ending[key] for key in ("when", "text", "additions", "marker")}
    scene["ending"] = ending
    (root / "scenes/2C.yaml").write_text(
        yaml.safe_dump(scene, sort_keys=False, width=10_000, allow_unicode=True),
        encoding="utf-8",
    )


def test_passage_rules_fixture_changes_only_the_three_passage_fields(tmp_path: Path) -> None:
    baseline = load_tree(copy_fixture("mini_ok", tmp_path / "baseline"))
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _patch_passage_rules(root)

    expected = copy.deepcopy(baseline)
    expected["scenes/1A.yaml"]["beats"][5]["say"] = _SAY_ENTRIES  # type: ignore[index]
    expected["scenes/2C.yaml"]["reveals"][1]["variants"]["transmit"]["text_when"] = _TEXT_WHEN_ENTRIES  # type: ignore[index]
    expected["scenes/2C.yaml"]["ending"]["additions"] = _ENDING_ADDITIONS  # type: ignore[index]
    assert load_tree(root) == expected
    assert list(load_tree(root)["scenes/2C.yaml"]["ending"]) == ["when", "text", "additions", "marker"]  # type: ignore[index]


def test_passage_rules_compile_to_ordered_and_ambiguous_values(tmp_path: Path) -> None:
    story_source = require_story_source()
    from storygame.runtime.delivery_text import AMBIGUOUS, resolve_delivery_text

    clean = copy_fixture("mini_ok", tmp_path / "clean")
    assert story_source.check_source_tree(clean) == []
    root = copy_fixture("mini_ok", tmp_path / "mutated")
    _patch_passage_rules(root)
    package = story_source.compile_source_tree(root)

    event = next(event for event in package.pacing.events if event.id == "patrol_leaves_1a")
    assert [realization.text for realization in event.realizations] == [entry["text"] for entry in _SAY_ENTRIES]
    matching = [
        realization
        for realization in event.realizations
        if {predicate.fact_id for predicate in realization.when} <= {"card_challenged", "patrol_on_scene"}
    ]
    assert matching[0].text == "The first matching patrol line."
    claim = next(item for item in package.knowledge.knowledge if item.id == "k_sl_2c_d_r3")
    assert claim.must_convey
    assert resolve_delivery_text(claim, {"ticket_header_matched", "evidence_ready_to_transmit"}) is AMBIGUOUS
    assert [variant.text for variant in package.pacing.ending.variants] == [
        entry["text"] for entry in _ENDING_ADDITIONS
    ]
