from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.ringer.affordance.sibling_reachability import report
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    Audience,
    FactPredicate,
    KnowledgeDefinition,
    RevealSource,
    RouteOperation,
)


def _item(
    item_id: str,
    storylet_id: str,
    fact_id: str,
    requires: tuple[FactPredicate, ...] = (),
) -> KnowledgeDefinition:
    return KnowledgeDefinition(
        id=item_id,
        statement=f"The story establishes {fact_id}.",
        aliases=(item_id,),
        audience=Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        requires=requires,
        establishes=(RouteOperation(op="assert", fact_id=fact_id, value=True),),
        source=RevealSource(kind="storylet_realization", storylet_id=storylet_id, realization_id=item_id),
    )


def _package() -> SimpleNamespace:
    storylets = tuple(
        SimpleNamespace(id=storylet_id, scene_id="1A", activation_conditions=())
        for storylet_id in ("SL-1A-A", "SL-1A-B", "SL-1A-C", "SL-1A-D")
    )
    items = (
        _item("k_different_a", "SL-1A-A", "unique_a"),
        _item("k_different_b", "SL-1A-A", "unique_b"),
        _item("k_same_a", "SL-1A-B", "shared_fact"),
        _item("k_same_b", "SL-1A-B", "shared_fact"),
        _item("k_split_a", "SL-1A-C", "split_a"),
        _item("k_split_b", "SL-1A-D", "split_b"),
    )
    return SimpleNamespace(
        knowledge=SimpleNamespace(knowledge=items),
        storylet_routes=SimpleNamespace(storylets=storylets),
    )


def _package_with_activation_bridge() -> SimpleNamespace:
    storylets = (
        SimpleNamespace(
            id="SL-1A-X",
            scene_id="1A",
            activation_conditions=(FactPredicate(fact_id="g", equals=True),),
        ),
        SimpleNamespace(
            id="SL-1A-Y",
            scene_id="1A",
            activation_conditions=(FactPredicate(fact_id="g", equals=True),),
        ),
    )
    items = (
        _item("k_x_r1", "SL-1A-X", "f1"),
        _item(
            "k_x_r2",
            "SL-1A-X",
            "f2",
            requires=(FactPredicate(fact_id="r2_ready", equals=True),),
        ),
        _item(
            "k_y_r1",
            "SL-1A-Y",
            "f1",
            requires=(FactPredicate(fact_id="r2_ready", equals=True),),
        ),
    )
    return SimpleNamespace(
        knowledge=SimpleNamespace(knowledge=items),
        storylet_routes=SimpleNamespace(storylets=storylets),
    )


def test_report_flags_unique_sibling_facts_and_accepts_genuine_alternatives() -> None:
    output = report(_package())

    assert "SL-1A-A | k_different_a | k_different_b | storylet_spent | no | unique_b" in output
    assert "SL-1A-A | k_different_b | k_different_a | storylet_spent | no | unique_a" in output
    assert "SL-1A-B | k_same_a | k_same_b | already_established | yes | -" in output
    assert "SL-1A-B | k_same_b | k_same_a | already_established | yes | -" in output


def test_report_has_no_sibling_row_for_actions_split_into_storylets() -> None:
    output = report(_package())

    assert "SL-1A-C" not in output
    assert "SL-1A-D" not in output


def test_report_seeds_activation_conditions_before_firing_reveal() -> None:
    output = report(_package_with_activation_bridge())

    assert "SL-1A-X | k_x_r2 | k_x_r1 | storylet_spent | yes | -" in output


def test_real_package_reports_medical_entry_sibling_fact_as_obtainable() -> None:
    package = load_story_package(Path(__file__).parents[1] / "data/stories/continuity-initiative")
    output = report(package)

    assert "SL-3A-B | k_sl_3a_b_r2 | k_sl_3a_b_r1 | storylet_spent | yes | -" in output
