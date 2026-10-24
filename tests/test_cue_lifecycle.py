from __future__ import annotations

from types import SimpleNamespace

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import NarrationSegment, TurnProposal
from storygame.runtime.cue_lifecycle import staged_cue_is_eligible
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from tests.test_discovery_continuity import (
    PACKAGE,
    _reveal_provider,
    _state_1a,
    _true_facts,
)


def test_same_turn_discovery_does_not_show_the_staged_cue() -> None:
    state = _state_1a(card_recovered=False)
    engine = RuntimeEngine(state, _reveal_provider("k_sl_1a_b_r0"))

    result = engine.turn("Search beneath the drawer.")

    cue = next(item.cue_text for item in PACKAGE.deliveries if item.fact_id == "continuity_initiative_known")
    assert "memory_card_recovered" in _true_facts(state)
    assert all(segment.text != cue for segment in result.segments)
    assert state.staged_cue_fact_id is None
    assert state.staged_cue_stage == 1


def test_cloudflare_drops_a_cue_when_the_current_state_already_has_the_target() -> None:
    state = _state_1a(card_recovered=True)
    state.facts.assert_fact(Fact(predicate="continuity_initiative_known", subject="story", value="true"))
    state.staged_cue_fact_id = "continuity_initiative_known"
    provider = CloudflareTurnProvider(worker_url="https://worker.invalid", token="test", state=state)
    proposal = TurnProposal(segments=(NarrationSegment(kind="narration", text="ordinary"),))

    result = provider._compose_staged_cue(proposal)

    assert result.segments == proposal.segments
    assert state.staged_cue_fact_id is None
    assert state.staged_cue_stage == 1


def test_synthetic_cue_eligibility_uses_identity_predicates_and_scene() -> None:
    state = SimpleNamespace(
        current_scene_id="observatory",
        staged_cue_fact_id="lead_known",
        staged_cue_stage=1,
        delivered_cue_ids=(),
        cue_stages=(),
        facts=SimpleNamespace(asserted=()),
    )
    delivery = SimpleNamespace(fact_id="lead_known", scene_id="observatory")

    assert staged_cue_is_eligible(state, delivery)
    assert not staged_cue_is_eligible(
        state,
        delivery,
        final_scene_id="archive",
    )
    state.facts.asserted = (SimpleNamespace(predicate="lead_known", value="true"),)
    assert not staged_cue_is_eligible(state, delivery)
