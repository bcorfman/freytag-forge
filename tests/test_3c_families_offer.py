from __future__ import annotations

from pathlib import Path

from bench.core import load_variation, package_and_state
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector

VARIATION_PATH = Path("bench/variations/stage7-3c-families-offer.json")
SHIPPED_PACKAGE = Path("data/stories/continuity-initiative")
PRE_ADOPTION_PACKAGE = Path("tests/fixtures/continuity_initiative_pre_3c_adoption")
COMMAND = "Answer the families with news of the captives."
D2 = "k_sl_3c_d_r2"
D1 = "k_sl_3c_d_r1"
C_FACTS = ("k_sl_3c_c_r1", "k_sl_3c_c_r2")
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")


def _matches_must_convey(delivery, text: str) -> bool:
    lowered = text.casefold()
    return all(any(phrase.casefold() in lowered for phrase in group) for group in delivery.must_convey)


def _families_package_and_state(variation_path: str):
    variation = load_variation(Path("bench/variations") / variation_path)
    package, state = package_and_state(variation, "3C")
    state._assert_scene_entry_fact("3C")  # noqa: SLF001 - establish the committed scene entry.
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return package, state


def _provider(package, knowledge_id: str):
    knowledge = package.knowledge_indexes.by_id[knowledge_id]
    text = knowledge.delivery_text or knowledge.statement
    return lambda _command: {
        "segments": [{"kind": "narration", "text": text}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _finish_c(order: tuple[str, ...] = C_FACTS, variation_path: str = VARIATION_PATH.name):
    package, state = _families_package_and_state(variation_path)
    commands = {
        "k_sl_3c_a_r1": "Send the evidence package.",
        "k_sl_3c_b_r1": "Take the Portable data case from Rebecca.",
        "k_sl_3c_c_r1": "Restore the drainage pumps.",
        "k_sl_3c_c_r2": "Open the surface gates.",
    }
    ids = ("k_sl_3c_a_r1", "k_sl_3c_b_r1", *order)
    engine = RuntimeEngine(state, _provider(package, ids[0]))
    for knowledge_id in ids:
        engine.provider = _provider(package, knowledge_id)
        engine.turn(commands[knowledge_id])
        engine._activate_pacing()  # noqa: SLF001 - commit the next staged cue.
    return package, engine


def _match(package, engine, command: str):
    projection = engine.projector.project(engine.state, "player", command)
    return uniquely_matched_authored_handoff(command, projection.reveal_universe)


def _selector_state(case: str, variation_path: str):
    order = C_FACTS if case != "C not complete" else ()
    package, engine = _finish_c(order, variation_path)
    if case == "D1 spent":
        engine.provider = _provider(package, D1)
        engine.turn("Read the detention site reports.")
        engine._activate_pacing()  # noqa: SLF001 - spend D1 before selecting.
    elif case == "D2 already spent":
        engine.provider = _provider(package, D2)
        engine.turn("Answer the families.")
        engine._activate_pacing()  # noqa: SLF001 - spend D2 before selecting.
    return _match(package, engine, COMMAND)


def _selector_table(variation_path: str) -> dict[str, str | None]:
    return {
        case: (matched.candidate.id if matched is not None else None)
        for case in ("D1 unspent", "D1 spent", "D2 already spent", "C not complete")
        for matched in (_selector_state(case, variation_path),)
    }


def test_variation_loader_and_source_diff_are_exact() -> None:
    variation = load_variation(VARIATION_PATH)
    effective = Path(variation["_package_path"])
    shipped_files = sorted(path.relative_to(SHIPPED_PACKAGE) for path in SHIPPED_PACKAGE.rglob("*") if path.is_file())
    effective_files = sorted(path.relative_to(effective) for path in effective.rglob("*") if path.is_file())
    assert effective_files == shipped_files

    for relative in shipped_files:
        shipped = (SHIPPED_PACKAGE / relative).read_bytes()
        changed = (effective / relative).read_bytes()
        if relative.as_posix() != "handoffs.yaml":
            assert changed == shipped, relative
        else:
            old = (
                b"  cue_text: Families of the missing call the broadcast chamber for word. "
                b"Kristin can answer the families with news of the captives."
            )
            new = b"  cue_text: Families of the missing call the broadcast chamber for word."
            assert changed == shipped.replace(old, new, 1)
            assert (SHIPPED_PACKAGE / relative).read_bytes().count(old) == 1
            assert changed.count(new) == 1


def test_offer_preserves_conveyance_and_protected_word_safety() -> None:
    variation, _ = _families_package_and_state(VARIATION_PATH.name)
    delivery = next(item for item in variation.deliveries if item.fact_id == "community_rescue_efforts_begun")
    assert delivery.cue_text == "Families of the missing call the broadcast chamber for word."
    assert _matches_must_convey(delivery, delivery.cue_text)
    forbidden = ("janus", "phase one", "phase two", "coded message")
    assert not any(word in delivery.cue_text.casefold() for word in forbidden)


def test_variation_command_never_selects_d1_or_another_reveal() -> None:
    package, engine = _finish_c()
    matched = _match(package, engine, COMMAND)
    assert matched is not None and matched.candidate.id == D2
    assert _match(package, engine, "Answer the neighbours with news of the captives.") is None
    projection = engine.projector.project(engine.state, "player", COMMAND)
    assert {candidate.id for candidate in projection.reveal_universe} <= {D1, D2}
    assert matched.candidate.id != D1


def _composed_reply(variation_path: str) -> tuple[str, frozenset[str], frozenset[str]]:
    package, state = _families_package_and_state(variation_path)
    state.staged_cue_fact_id = "community_rescue_efforts_begun"
    state.staged_cue_stage = 1
    provider = CloudflareTurnProvider.__new__(CloudflareTurnProvider)
    provider.state = state
    provider.projector = KnowledgeProjector()
    proposal = parse_turn_proposal({"segments": [{"kind": "narration", "text": "The broadcast chamber waits."}]})
    composed = provider._compose_staged_cue(proposal)  # noqa: SLF001 - exercise deterministic cue composition.
    eligibility = frozenset(
        candidate.id for candidate in provider.projector.project(state, "player", COMMAND).reveal_universe
    )
    committed = frozenset(fact.predicate for fact in state.facts.asserted)
    return composed.narration, eligibility, committed


def test_composed_reply_diff_is_only_the_appended_sentence() -> None:
    shipped_text, shipped_eligible, shipped_committed = _composed_reply("stage7-3c-item-facts.json")
    variation_text, variation_eligible, variation_committed = _composed_reply(VARIATION_PATH.name)
    old = "Families of the missing call the broadcast chamber for word."
    appended = " Kristin can answer the families with news of the captives."
    assert variation_text == shipped_text.replace(old + appended, old, 1)
    assert shipped_text.endswith(old + appended)
    assert "organize independent rescue efforts" not in variation_text.casefold()
    assert "many of the missing are still alive" not in variation_text.casefold()
    assert shipped_eligible == variation_eligible
    assert shipped_committed == variation_committed
