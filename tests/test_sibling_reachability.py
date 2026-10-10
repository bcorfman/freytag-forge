from __future__ import annotations

from types import SimpleNamespace

from scripts.ringer.affordance.sibling_reachability import report
from storygame.story_package.models import Audience, KnowledgeDefinition, RevealSource, RouteOperation


def _item(item_id: str, storylet_id: str, fact_id: str) -> KnowledgeDefinition:
    return KnowledgeDefinition(
        id=item_id,
        statement=f"The story establishes {fact_id}.",
        aliases=(item_id,),
        audience=Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
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
