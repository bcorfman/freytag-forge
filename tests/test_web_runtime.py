from __future__ import annotations

import pytest

from storygame.engine.fact_commit import ValidatedFactCommitter
from storygame.web_runtime import (
    TurnExecution,
    _bootstrap_opening_from_narrator_opening_agent,
    _llm_bootstrap_opening_lines,
    _normalized_narrator_opening_paragraphs,
    bootstrap_failure_debug_payload,
    build_state_snapshot_payload,
    build_turn_response_payload,
)
from tests.fast_fixtures import make_cached_story_state


def test_shared_response_payloads_use_injected_runtime_state_without_an_adapter() -> None:
    state = make_cached_story_state(seed=901, genre="mystery")
    state.player.inventory = ("case_file",)
    ValidatedFactCommitter().commit(
        state,
        [{"op": "assert", "fact": ("active_goal", "Inspect the case file.")}],
        source="test.web_runtime",
    )

    snapshot = build_state_snapshot_payload(state, "run_id", "run-901")
    response = build_turn_response_payload(
        state,
        "look",
        "look",
        "investigation",
        True,
        ["The room waits."],
        "run_id",
        "run-901",
    )

    assert snapshot["run_id"] == "run-901"
    assert snapshot["inventory"] == list(state.player.inventory)
    assert snapshot["objective"] == state.active_goal
    assert response["lines"] == [">LOOK", "The room waits."]
    assert response["state"] == snapshot


def test_shared_turn_execution_contract_is_adapter_independent() -> None:
    state = make_cached_story_state(seed=902)
    execution = TurnExecution(state, ["A bounded result."], "look", "setup_scene", True)

    assert execution.next_state is state
    assert execution.lines == ["A bounded result."]
    assert execution.action_raw == "look"
    assert execution.beat == "setup_scene"
    assert execution.continued is True


def test_opening_normalization_is_shared_by_local_and_hosted_adapters() -> None:
    paragraphs = _normalized_narrator_opening_paragraphs(
        "Ask Daria Stone about the suspect's involvement.\n\n"
        "The room settles into silence.\n\n"
        "A final complete paragraph.",
        "Daria Stone",
    )

    assert paragraphs == [
        "consult Daria Stone about the suspect's involvement.",
        "The room settles into silence.",
        "A final complete paragraph.",
    ]


def test_opening_normalization_rejects_empty_contract() -> None:
    with pytest.raises(RuntimeError, match="Opening contract validation failed"):
        _normalized_narrator_opening_paragraphs("", "Daria Stone")


def test_opening_normalization_discards_an_incomplete_fourth_paragraph() -> None:
    paragraphs = _normalized_narrator_opening_paragraphs(
        "First complete.\n\nSecond complete!\n\nThird complete?\n\nFourth unfinished",
        "Daria Stone",
    )

    assert paragraphs == ["First complete.", "Second complete!", "Third complete?"]


def test_opening_normalization_removes_doctest_wrappers_and_echoed_json() -> None:
    paragraphs = _normalized_narrator_opening_paragraphs(
        '# doctests """ Rain needles the mansion steps.\n\n'
        "Daria Stone holds the case file close.\n\n"
        'Your first task is to decide where to begin. """ '
        '{"opening_draft":"This echoed request must not reach the player."}',
        "Daria Stone",
    )

    assert paragraphs == [
        "Rain needles the mansion steps.",
        "Daria Stone holds the case file close.",
        "Your first task is to decide where to begin.",
    ]
    displayed = "\n".join(paragraphs)
    assert "doctest" not in displayed.lower()
    assert "opening_draft" not in displayed
    assert "{" not in displayed


def test_bootstrap_debug_payload_is_fact_and_package_scoped() -> None:
    state = make_cached_story_state(seed=903)
    state.world_package["llm_story_bundle"] = {
        "assistant_name": "Daria Stone",
        "actionable_objective": "Open the case file.",
        "opening_paragraphs": ["One.", "", "Two."],
    }

    payload = bootstrap_failure_debug_payload(state, "start", "session_id", "session-903")

    assert payload["session_id"] == "session-903"
    assert payload["assistant_name"] == "Daria Stone"
    assert payload["bundle_actionable_objective"] == "Open the case file."
    assert payload["bundle_opening_paragraphs"] == ["One.", "Two."]


class _OpeningDirector:
    def compose_opening_fast(self, state):  # noqa: ANN001
        state.world_package["llm_story_bundle"] = {"opening_paragraphs": ["Fast opening."]}
        return ["Fast opening."]

    def compose_opening(self, state):  # noqa: ANN001
        raise AssertionError("fast opening should be selected")


class _EmptyNarrator:
    def generate(self, context):  # noqa: ANN001
        return ""


class _FailingDirector:
    def compose_opening_fast(self, state):  # noqa: ANN001
        raise RuntimeError("director unavailable")

    def compose_opening(self, state):  # noqa: ANN001
        raise RuntimeError("director unavailable")


class _FailingNarrator:
    def generate(self, context):  # noqa: ANN001
        raise RuntimeError("narrator unavailable")


class _OpeningAgent:
    def run(self, state, architect, cast, plan):  # noqa: ANN001
        assert cast["contacts"]
        assert plan["assistant_name"]
        return ["An agent-authored opening."]


class _EmptyOpeningAgent:
    def run(self, state, architect, cast, plan):  # noqa: ANN001, ARG002
        return []


class _FailingOpeningAgent:
    def run(self, state, architect, cast, plan):  # noqa: ANN001, ARG002
        raise RuntimeError("opening agent unavailable")


class _ShortNarrator:
    def generate(self, context):  # noqa: ANN001
        return "Cloudflare-authored opening prose."


class _PassThroughEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return lines


def test_bootstrap_runtime_seams_support_fast_openings_and_fail_closed_fallback() -> None:
    state = make_cached_story_state(seed=904)
    assert _llm_bootstrap_opening_lines(
        state,
        _OpeningDirector(),
        _EmptyNarrator(),
        _PassThroughEditor(),
        use_fast_story_director_opening=True,
    ) == ["Fast opening."]

    with pytest.raises(RuntimeError, match="LLM-authored opening"):
        _llm_bootstrap_opening_lines(
            make_cached_story_state(seed=905),
            _OpeningDirector(),
            _EmptyNarrator(),
            _PassThroughEditor(),
            allow_story_director_bootstrap=False,
        )

    with pytest.raises(RuntimeError, match="story_director=director unavailable"):
        _llm_bootstrap_opening_lines(
            make_cached_story_state(seed=906),
            _FailingDirector(),
            _FailingNarrator(),
            _PassThroughEditor(),
            use_fast_story_director_opening=True,
        )


def test_narrator_opening_agent_receives_fact_backed_contacts() -> None:
    state = make_cached_story_state(seed=907)

    assert _bootstrap_opening_from_narrator_opening_agent(
        state,
        _OpeningAgent(),
        _PassThroughEditor(),
    ) == ["An agent-authored opening."]


def test_hosted_bootstrap_uses_generic_worker_prose_only_after_an_empty_opening_agent() -> None:
    assert _llm_bootstrap_opening_lines(
        make_cached_story_state(seed=908),
        _OpeningDirector(),
        _ShortNarrator(),
        _PassThroughEditor(),
        allow_story_director_bootstrap=False,
        narrator_opening_agent=_EmptyOpeningAgent(),
    ) == ["Cloudflare-authored opening prose."]


def test_hosted_bootstrap_reports_both_worker_opening_failures() -> None:
    with pytest.raises(RuntimeError, match="opening_agent=opening agent unavailable; narrator=empty"):
        _llm_bootstrap_opening_lines(
            make_cached_story_state(seed=909),
            _OpeningDirector(),
            _FailingNarrator(),
            _PassThroughEditor(),
            allow_story_director_bootstrap=False,
            narrator_opening_agent=_FailingOpeningAgent(),
        )
