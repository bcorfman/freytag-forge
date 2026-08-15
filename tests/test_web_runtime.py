from __future__ import annotations

import pytest

from storygame.engine.fact_commit import ValidatedFactCommitter
from storygame.llm.adapters import CloudflareNarrationError
from storygame.web_runtime import (
    TurnExecution,
    _bootstrap_opening_from_narrator,
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


def test_opening_normalization_rejects_an_incomplete_fourth_paragraph() -> None:
    with pytest.raises(RuntimeError, match="truncated final paragraph"):
        _normalized_narrator_opening_paragraphs(
            "First complete.\n\nSecond complete!\n\nThird complete?\n\nFourth unfinished",
            "Daria Stone",
        )


def test_opening_normalization_rejects_a_truncated_final_paragraph_without_editing_prose() -> None:
    with pytest.raises(RuntimeError, match="truncated final paragraph"):
        _normalized_narrator_opening_paragraphs(
            "The opening is grounded.\n\nDaria keeps watch.\n\nThe work continues. You glance toward the drive, a reminder that you still have a lot to do before you can start making",
            "Daria Stone",
        )


class _RetryingOpeningNarrator:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate(self, context):  # noqa: ANN001
        self.calls.append(context.completion_instruction)
        if len(self.calls) == 1:
            return "First paragraph.\n\nSecond paragraph.\n\nThe final paragraph is cut off"
        return "First paragraph.\n\nSecond paragraph.\n\nThe final paragraph is complete."


def test_opening_generation_retries_truncation_with_completion_instruction() -> None:
    narrator = _RetryingOpeningNarrator()
    state = make_cached_story_state(seed=904, genre="mystery")

    opening = _bootstrap_opening_from_narrator(state, narrator, _PassThroughEditor())

    assert opening[-1] == "The final paragraph is complete."
    assert narrator.calls == [
        "",
        "Your previous opening was cut off. Return the complete opening again, with 3 to 4 complete paragraphs and a final sentence ending in punctuation. Do not summarize or omit the ending.",
    ]


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


def test_opening_normalization_rejects_echoed_prompt_and_room_context() -> None:
    leaked_worker_response = """>LOOK
Rule: do not invent facts. Rule: any state change must be explicit, limited to engine context, and fact-representable. Rule: opening scene must establish who the player is, where they are, and the immediate objective. Rule: opening scene must stay materially consistent with the room description, exits, visible items, visible NPCs, and inventory. Rule: action: look

Outside The Mansion
Broad stone steps rise to a carved oak door framed by weathered columns.
A dark sedan waits nearby where you left it.
The main entrance from here leads north toward the mansion interior, while the drive behind you remains open.
Daria Stone is nearby, watching your next move."""

    with pytest.raises(RuntimeError, match="prompt/context echo"):
        _normalized_narrator_opening_paragraphs(
            leaked_worker_response,
            "Daria Stone",
        )


def test_opening_normalization_rejects_code_comment_artifacts_in_player_prose() -> None:
    with pytest.raises(RuntimeError, match="code-comment artifact"):
        _normalized_narrator_opening_paragraphs(
            "You're standing outside the mansion with Daria Stone. # noqa.\n\n"
            "The case file waits in your hand. # noqa.",
            "Daria Stone",
        )


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
        assert architect["protagonist_name"] == "Detective Elias Wren"
        assert "private detective" in architect["protagonist_background"].lower()
        assert "murder" in architect["protagonist_background"].lower()
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


class _InvalidOpeningNarrator:
    def generate(self, context):  # noqa: ANN001
        return "The mansion waits. # noqa."


class _IncoherentOpeningNarrator:
    def generate(self, context):  # noqa: ANN001
        return (
            "Your assistant, Daria Stone, stands at your side.\n\n"
            "Daria Stone is the suspect in the murder.\n\n"
            "The rain turns the steps slick beneath your shoes.\n\n"
            "The house gives nothing away."
        )


class _NoBundleDirector:
    def compose_opening_fast(self, state):  # noqa: ANN001
        return []

    def compose_opening(self, state):  # noqa: ANN001
        return []


class _PassThroughEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return lines


class _CommentInjectingEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return ["Opening artifact. # noqa"]


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


def test_bootstrap_preserves_structured_cloudflare_failures() -> None:
    class _CloudflareFailureNarrator:
        def generate(self, _context):
            raise CloudflareNarrationError(
                "AI_WORKER_REVISION_MISMATCH",
                "revision mismatch",
                http_status=502,
                trace_id="trace-123",
            )

    with pytest.raises(CloudflareNarrationError, match="AI_WORKER_REVISION_MISMATCH"):
        _bootstrap_opening_from_narrator(
            make_cached_story_state(seed=912),
            _CloudflareFailureNarrator(),
            _PassThroughEditor(),
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


def test_explicit_legacy_opening_agent_remains_outside_the_hosted_demo_path() -> None:
    assert _llm_bootstrap_opening_lines(
        make_cached_story_state(seed=910),
        _OpeningDirector(),
        _EmptyNarrator(),
        _PassThroughEditor(),
        allow_story_director_bootstrap=False,
        narrator_opening_agent=_OpeningAgent(),
    ) == ["An agent-authored opening."]


def test_bootstrap_reports_invalid_narrator_output_after_a_director_failure() -> None:
    with pytest.raises(RuntimeError, match="story_director=director unavailable"):
        _llm_bootstrap_opening_lines(
            make_cached_story_state(seed=911),
            _FailingDirector(),
            _InvalidOpeningNarrator(),
            _PassThroughEditor(),
        )


def test_local_bootstrap_rejects_narration_that_conflicts_with_fact_backed_roles() -> None:
    with pytest.raises(RuntimeError, match="Opening validation failed"):
        _llm_bootstrap_opening_lines(
            make_cached_story_state(seed=915),
            _NoBundleDirector(),
            _IncoherentOpeningNarrator(),
            _PassThroughEditor(),
        )


def test_local_bootstrap_uses_an_explicit_opening_agent_only_after_empty_narration() -> None:
    assert _llm_bootstrap_opening_lines(
        make_cached_story_state(seed=912),
        _NoBundleDirector(),
        _EmptyNarrator(),
        _PassThroughEditor(),
        narrator_opening_agent=_OpeningAgent(),
    ) == ["An agent-authored opening."]


def test_hosted_direct_narration_does_not_run_legacy_opening_text_validation() -> None:
    assert _llm_bootstrap_opening_lines(
        make_cached_story_state(seed=913),
        _OpeningDirector(),
        _InvalidOpeningNarrator(),
        _PassThroughEditor(),
        allow_story_director_bootstrap=False,
        narrator_opening_agent=_FailingOpeningAgent(),
    ) == ["The mansion waits. # noqa."]


def test_opening_agent_rejects_editor_introduced_code_artifacts() -> None:
    with pytest.raises(RuntimeError, match="code-comment artifact"):
        _bootstrap_opening_from_narrator_opening_agent(
            make_cached_story_state(seed=914),
            _OpeningAgent(),
            _CommentInjectingEditor(),
        )
