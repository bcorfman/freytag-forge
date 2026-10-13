"""Regression coverage for authoritative multi-word leak terms."""

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import guarded_narration_terms, load_story_package
from tests.test_leak_terms import PACKAGE, _package_for


def test_leak_term_alone_rejects_narration_before_the_item_is_earned() -> None:
    package = _package_for(leak_terms=("silver ember phrase",))

    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(
            RuntimeState.bootstrap(package),
            lambda _: {"segments": [{"kind": "narration", "text": "Kristin finds the silver ember phrase."}]},
        ).turn("Search the desk.")

    assert caught.value.code == "narration_known_term_leak"


def test_single_word_leak_term_is_not_enforced() -> None:
    # Single-word leak terms are intentionally not enforced by design.
    package = _package_for(leak_terms=("password",))

    result = RuntimeEngine(
        RuntimeState.bootstrap(package),
        lambda _: {"segments": [{"kind": "narration", "text": "Kristin notices the password."}]},
    ).turn("Search the desk.")

    assert result.segments[0].text == "Kristin notices the password."


def test_card_phrase_is_rejected_before_the_search_and_allowed_on_the_earning_turn() -> None:
    text = "Kristin finds Michelle's memory card taped beneath the drawer."

    def scripted(player_input: str) -> dict[str, object]:
        earning = player_input == "Search under the drawer in her workstation."
        return {
            "segments": [{"kind": "narration", "text": text, "grounding_ids": ["k_sl_1a_b_r0"] if earning else []}],
            "selected_knowledge_ids": ["k_sl_1a_b_r0"] if earning else [],
        }

    early_state = RuntimeState.bootstrap(PACKAGE)
    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(early_state, scripted).turn("Look around the kitchen.")
    assert caught.value.code == "narration_known_term_leak"

    earning_state = RuntimeState.bootstrap(PACKAGE)
    result = RuntimeEngine(earning_state, scripted).turn("Search under the drawer in her workstation.")
    assert result.selected_knowledge_ids == ("k_sl_1a_b_r0",)


def test_every_multiword_leak_term_in_the_story_is_enforced() -> None:
    for story_root in sorted(path for path in Path("data/stories").iterdir() if path.is_dir()):
        package = load_story_package(story_root)
        guarded = guarded_narration_terms(package.knowledge_indexes)
        for item in package.knowledge.knowledge:
            for term in item.leak_terms or ():
                if len(term.split()) > 1:
                    assert term.casefold() in guarded
