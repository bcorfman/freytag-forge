"""Each authored leak vocabulary entry uses the same earning rule in both callers."""

from pathlib import Path

import pytest

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeGuards, KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import guarded_narration_terms, load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


@pytest.mark.parametrize("term", sorted(guarded_narration_terms(PACKAGE.knowledge_indexes)))
@pytest.mark.parametrize("earned", (False, True), ids=("scene-start", "earned"))
def test_helper_and_validator_agree_for_each_package_guarded_term(term: str, earned: bool) -> None:
    # Isolate this term's guard from overlapping phrases and entity scope rules.
    # Keep the real owners, audience declarations, effects and starting facts.
    indexes = PACKAGE.knowledge_indexes
    owners = indexes.leak_term_to_knowledge[term]
    package = PACKAGE.model_copy(
        update={
            "knowledge_indexes": indexes.model_copy(
                update={
                    "leak_term_to_knowledge": {term: owners},
                    "entity_alias_to_entities": {},
                    "protected_terms": (),
                    "disclosure_guards": {},
                }
            )
        }
    )
    state = RuntimeState.bootstrap(package)
    if earned:
        for owner in owners:
            for effect in indexes.by_id[owner].establishes:
                value = str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value)
                if effect.op == "assert":
                    state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value=value))
                else:
                    state.facts.retract_fact(Fact(predicate=effect.fact_id, subject="story", value=value))
    guards = KnowledgeGuards(state)
    proposal = ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=term),))
    if guards.unearned(owners):
        with pytest.raises(ProposalValidationError, match="unavailable knowledge"):
            NarrationSafetyValidator().validate(state, state, proposal, KnowledgeProjector(), "Examine the room.")
    else:
        NarrationSafetyValidator().validate(state, state, proposal, KnowledgeProjector(), "Examine the room.")
