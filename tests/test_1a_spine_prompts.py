from scripts.generate_spine_expected_reveals import knowledge_items, matching_reveals, scene_prompts


def test_1a_research_fragments_earn_d_r1_without_the_file_reading_tie() -> None:
    prompts = scene_prompts()["1A"]
    knowledge = knowledge_items()
    assert matching_reveals(knowledge, "1A", prompts[3]) == {"k_sl_1a_b_r1", "k_sl_1a_d_r1"}
    assert matching_reveals(knowledge, "1A", prompts[2]) == {"k_sl_1a_d_r1"}


def test_research_fragments_then_files_can_both_be_earned() -> None:
    from pathlib import Path

    from storygame.runtime.facts import Fact
    from storygame.runtime.reveal_eligibility import explain_reveal
    from storygame.runtime.state import RuntimeState
    from storygame.story_package.loader import load_story_package

    package = load_story_package(Path("data/stories/continuity-initiative"))
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    state.active_event_ids.update({"SL-1A-D", "SL-1A-B"})
    for item_id in ("k_sl_1a_d_r1", "k_sl_1a_b_r1"):
        item = package.knowledge_indexes.by_id[item_id]
        eligibility = explain_reveal(state, "player", item)
        assert eligibility.eligible, eligibility
        state.fired_event_ids.add(item.source.storylet_id)
        for effect in item.establishes:
            assert effect.op == "assert"
            state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value="true"))
