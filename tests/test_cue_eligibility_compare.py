from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    Audience,
    FactDelivery,
    FactPredicate,
    KnowledgeDefinition,
    RevealSource,
    RouteOperation,
)

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _item(
    item_id: str,
    storylet_id: str,
    fact_id: str,
    *,
    requires: tuple[FactPredicate, ...] = (),
    audience: Audience | None = None,
) -> KnowledgeDefinition:
    return KnowledgeDefinition(
        id=item_id,
        statement=f"The story establishes {fact_id}.",
        aliases=(item_id,),
        audience=audience or Audience(kind="public", player_visible=True),
        available_in_scenes=("1A",),
        requires=requires,
        establishes=(RouteOperation(op="assert", fact_id=fact_id, value=True),),
        source=RevealSource(kind="storylet_realization", storylet_id=storylet_id, realization_id=item_id),
    )


def _delivery(fact_id: str) -> FactDelivery:
    return FactDelivery(
        fact_id=fact_id,
        scene_id="1A",
        source_kind="observation",
        must_convey=((fact_id,), (fact_id,)),
        fallback_text=f"The story carries {fact_id}.",
        cue_text=f"Look for {fact_id}.",
    )


def _synthetic_package() -> SimpleNamespace:
    setup = _item("k_setup", "SL-1A-A", "setup_fact")
    # Seeding SL-1A-A's activation condition makes the target fact established
    # without firing the target source storylet.  This exercises the earned arm.
    setup = setup.model_copy(update={"establishes": (RouteOperation(op="assert", fact_id="setup_fact", value=True),)})
    spent = _item("k_spent", "SL-1A-B", "spent_fact")
    eligible = _item("k_eligible", "SL-1A-C", "eligible_fact")
    earned = _item("k_earned", "SL-1A-D", "earned_fact")
    missing = _item(
        "k_missing",
        "SL-1A-E",
        "missing_fact",
        requires=(FactPredicate(fact_id="never_true", equals=True),),
    )
    storylets = tuple(
        SimpleNamespace(id=storylet_id, scene_id="1A", activation_conditions=activation)
        for storylet_id, activation in (
            ("SL-1A-A", (FactPredicate(fact_id="earned_fact", equals=True),)),
            ("SL-1A-B", ()),
            ("SL-1A-C", ()),
            ("SL-1A-D", ()),
            ("SL-1A-E", ()),
        )
    )
    items = (setup, spent, eligible, earned, missing)
    return SimpleNamespace(
        scenes=(SimpleNamespace(metadata=SimpleNamespace(scene_id="1A")),),
        deliveries=tuple(
            _delivery(fact_id) for fact_id in ("spent_fact", "eligible_fact", "earned_fact", "missing_fact")
        ),
        knowledge=SimpleNamespace(knowledge=items),
        storylet_routes=SimpleNamespace(storylets=storylets),
    )


def test_synthetic_package_classifies_spent_eligible_earned_and_missing() -> None:
    from scripts.ringer.affordance.cue_eligibility_compare import report

    output = report(_synthetic_package())

    assert (
        "1A | SL-1A-B fired through k_spent | spent_fact | True | False | "
        "k_spent:already_established | CUE_SHOWN_BUT_SPENT"
    ) in output
    assert "1A | S0 | eligible_fact | True | True | k_eligible:eligible | AGREE" in output
    assert (
        "1A | SL-1A-A fired through k_setup | earned_fact | True | False | "
        "k_earned:already_established | CUE_SHOWN_BUT_EARNED"
    ) in output
    assert "1A | S0 | missing_fact | False | False | k_missing:prerequisite_missing | AGREE" in output


def test_real_package_reports_the_known_1a_spent_case() -> None:
    from scripts.ringer.affordance.cue_eligibility_compare import report

    output = report(PACKAGE)

    assert (
        "1A | SL-1A-B fired through k_sl_1a_b_r1 | continuity_initiative_known | True | False | "
        "k_sl_1a_b_r0:already_established,k_sl_1a_b_r1:already_established,k_sl_1a_d_r1:already_established | "
        "CUE_SHOWN_BUT_SPENT"
    ) in output
    assert "Known case observed: yes" in output


def test_importing_script_does_not_change_real_cue_results() -> None:
    scene_id = "1A"
    state = RuntimeState(package=PACKAGE, current_scene_id=scene_id, phase="exposition")
    state._assert_scene_entry_fact(scene_id)
    holder = SimpleNamespace(state=state)
    fact_ids = tuple(
        delivery.fact_id for delivery in PACKAGE.deliveries if delivery.scene_id == scene_id and delivery.cue_text
    )
    sys.modules.pop("scripts.ringer.affordance.cue_eligibility_compare", None)
    before = tuple(RuntimeEngine._cue_reveal_available(holder, fact_id) for fact_id in fact_ids)
    importlib.import_module("scripts.ringer.affordance.cue_eligibility_compare")
    after = tuple(RuntimeEngine._cue_reveal_available(holder, fact_id) for fact_id in fact_ids)

    assert after == before
