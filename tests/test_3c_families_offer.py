from __future__ import annotations

import tempfile
from pathlib import Path

from bench.core import load_variation, package_and_state
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy, load_tree, patch_source

VARIATION_PATH = Path("bench/variations/stage7-3c-families-offer.json")
PRE_ADOPTION_PACKAGE = Path("tests/fixtures/continuity_initiative_pre_3c_adoption")
COMMAND = "Answer the families with news of the captives."
D2 = "k_sl_3c_d_r2"
D1 = "k_sl_3c_d_r1"
C_FACTS = ("k_sl_3c_c_r1", "k_sl_3c_c_r2")
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")
_COMPILED_COPIES: list[tempfile.TemporaryDirectory[str]] = []


def _families_source_package(*, offer: bool):
    temporary = tempfile.TemporaryDirectory(prefix="families-offer-")
    _COMPILED_COPIES.append(temporary)
    root = compiled_story_copy(Path(temporary.name))
    if offer:
        patch_source(
            root,
            "source/scenes/3C.yaml",
            "facts.community_rescue_efforts_begun.delivery.cue_text",
            "Families of the missing call the broadcast chamber for word.",
        )
    return root


def _matches_must_convey(delivery, text: str) -> bool:
    lowered = text.casefold()
    return all(any(phrase.casefold() in lowered for phrase in group) for group in delivery.must_convey)


def _families_package_and_state(variation_path: str):
    if variation_path == VARIATION_PATH.name:
        root = _families_source_package(offer=True)
        variation = {"_package_path": str(root)}
        package, state = package_and_state(variation, "3C")
    else:
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
        "k_sl_3c_c_r2": "Give up the lower levels.",
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


def test_variation_loader_and_source_diff_are_exact(tmp_path: Path) -> None:
    shipped_root = compiled_story_copy(tmp_path / "shipped")
    changed_root = compiled_story_copy(tmp_path / "changed")
    patch_source(
        changed_root,
        "source/scenes/3C.yaml",
        "facts.community_rescue_efforts_begun.delivery.cue_text",
        "Families of the missing call the broadcast chamber for word.",
    )
    shipped = load_compiled_copy(shipped_root)
    changed = load_compiled_copy(changed_root)

    shipped_tree = load_tree(shipped_root / "source")
    changed_tree = load_tree(changed_root / "source")
    assert set(changed_tree) == set(shipped_tree)
    for relative, shipped_document in shipped_tree.items():
        if relative != "scenes/3C.yaml":
            assert changed_tree[relative] == shipped_document, relative
    assert changed_tree["scenes/3C.yaml"]["facts"]["community_rescue_efforts_begun"]["delivery"]["cue_text"] == (
        "Families of the missing call the broadcast chamber for word."
    )
    shipped_delivery = next(item for item in shipped.deliveries if item.fact_id == "community_rescue_efforts_begun")
    changed_delivery = next(item for item in changed.deliveries if item.fact_id == "community_rescue_efforts_begun")
    assert shipped_delivery.cue_text.endswith("Kristin can answer the families with news of the captives.")
    assert changed_delivery.cue_text == "Families of the missing call the broadcast chamber for word."


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
    assert engine.state.story_complete is True
    assert matched is None


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
