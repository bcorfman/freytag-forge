"""Cloudflare transport keeps its small, fail-closed contract."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError, SelectedRevealResolver
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_transport_sends_bounded_context_and_optional_token(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def open_request(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A valid proposal."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="secret", state=state)

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "A valid proposal."}]}
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert "Mozilla/5.0" in captured["headers"]["User-agent"]
    assert captured["payload"]["max_tokens"] == 2048
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    context = json.loads(captured["payload"]["user"])["knowledge_context"]
    assert "response_schema" in captured["payload"]["user"]
    assert "concrete immediate consequence" in captured["payload"]["system"]
    assert "selected_knowledge_ids" in captured["payload"]["system"]
    assert context["player"]["scene_id"] == "1A"
    assert context["player"]["candidates"] == []
    serialized = json.dumps(context).casefold()
    for forbidden in ("janus", "plot_beats", "entry_text", "active_storylets", "narrative_history"):
        assert forbidden not in serialized
    state.active_event_ids.add("SL-1A-B")
    provider("I search the desk drawer for Michelle's recording.")
    drawer_context = json.loads(captured["payload"]["user"])["knowledge_context"]["player"]
    candidate = next(item for item in drawer_context["candidates"] if item["id"] == "k_sl_1a_b_r2")
    assert "damaged recording" in candidate["statement"]
    assert set(candidate) == {"id", "statement"}
    assert provider.last_projection is not None


def test_recording_candidate_is_absent_until_its_route_is_eligible(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    def open_request(request, **_kwargs):
        captured.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A valid proposal."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider("I inspect the back door.")
    provider("I examine Michelle's phone.")
    state.active_event_ids.add("SL-1A-B")
    provider("I search the desk drawer for a damaged recording.")

    contexts = [json.loads(payload["user"])["knowledge_context"]["player"] for payload in captured]
    assert all(
        all(candidate["id"] != "k_sl_1a_b_r2" for candidate in context["candidates"]) for context in contexts[:2]
    )
    assert any(candidate["id"] == "k_sl_1a_b_r2" for candidate in contexts[2]["candidates"])


def test_transport_unwraps_the_workers_narration_envelope(monkeypatch) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "narration": '{"segments":[{"kind":"narration","text":"A valid proposal."}]}',
                "model": "worker-model",
                "trace_id": "trace-123",
            }
        ),
    )

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "A valid proposal."}]}


def test_transport_is_unavailable_without_url_or_on_bad_worker_responses(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    with pytest.raises(NarrationProviderError, match="unavailable"):
        CloudflareTurnProvider.from_environment(state)

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", " token ")
    configured = CloudflareTurnProvider.from_environment(state)
    assert configured.worker_url == "https://worker.example/turn"
    assert configured.token == "token"

    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response({"status": "error"})
    )
    with pytest.raises(NarrationProviderError, match="failed"):
        provider("I listen.")

    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline"))
    )
    with pytest.raises(NarrationProviderError, match="unavailable"):
        provider("I listen.")


def test_transport_retries_once_without_json_mode_after_worker_rejection(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )

    def open_request(request, timeout):
        payload = json.loads(request.data)
        payloads.append(payload)
        if len(payloads) == 1:
            raise HTTPError(
                "https://worker.example/turn",
                502,
                "json mode rejected",
                {},
                BytesIO(b'{"status":"error","code":"AI_JSON_MODE_REJECTED"}'),
            )
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A recovered proposal."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "A recovered proposal."}]}
    assert payloads[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in payloads[1]


def test_transport_recovers_once_from_a_malformed_provider_envelope(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response({"narration": '{"segments":[]}'})
        return _Response({"narration": '{"segments":[{"kind":"action","text":"Kristin checks the door."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    assert provider("I listen.") == {"segments": [{"kind": "action", "text": "Kristin checks the door."}]}
    assert len(payloads) == 2


def test_transport_recovers_once_when_provider_selects_unavailable_knowledge(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response(
                {
                    "narration": (
                        '{"segments":[{"kind":"narration","text":"An invalid reveal."}],'
                        '"selected_knowledge_ids":["k_future_unavailable"]}'
                    )
                }
            )
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"Michelle\'s damaged recording crackles."}],'
                    '"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I search the desk drawer for Michelle's damaged recording.")

    assert proposal["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert len(payloads) == 2
    assert "previous response was invalid" in payloads[1]["system"]
    assert "k_future_unavailable" in payloads[1]["system"]
    # The retry must lead with the response that always validates. Offering only a menu
    # lets the model keep reaching for the reveal the player's intent implies.
    assert "empty list" in payloads[1]["system"]


def test_transport_recovers_once_when_provider_grounds_on_unselected_knowledge(monkeypatch) -> None:
    """Bad grounding must spend the single recovery, not fail the player's turn with HTTP 409."""

    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response(
                {
                    "narration": (
                        '{"segments":[{"kind":"narration","text":"A recording plays.",'
                        '"grounding_ids":["k_sl_1a_b_r2"]}],"selected_knowledge_ids":[]}'
                    )
                }
            )
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"The drawer sticks, then gives."}],'
                    '"selected_knowledge_ids":[]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I search the desk drawer.")

    assert proposal["segments"][0]["text"] == "The drawer sticks, then gives."
    assert len(payloads) == 2
    assert "previous response was invalid" in payloads[1]["system"]
    # The retry must name the offending ID; a blind retry repeats the same mistake.
    assert "k_sl_1a_b_r2" in payloads[1]["system"]
    assert "grounding_ids" in payloads[1]["system"]


def test_transport_accepts_grounding_on_the_selected_candidate(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"Michelle\'s warning crackles.",'
                    '"grounding_ids":["k_sl_1a_b_r2"]}],"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I play the damaged recording.")

    assert proposal["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert len(payloads) == 1, "grounding on the selected candidate must not spend a recovery"


@pytest.mark.parametrize(
    ("segments", "selected"),
    [
        pytest.param(
            [{"kind": "narration", "text": "Two reveals at once."}],
            ["k_sl_1a_b_r1", "k_sl_1a_b_r2"],
            id="more than one selection",
        ),
        pytest.param(
            [{"kind": "narration", "text": "An unearned reveal."}],
            ["k_future_unavailable"],
            id="selection outside this turn's candidates",
        ),
        pytest.param(
            [{"kind": "narration", "text": "A grounded claim.", "grounding_ids": ["k_sl_1a_b_r2"]}],
            [],
            id="grounding that is neither committed nor selected",
        ),
    ],
)
def test_transport_precheck_mirrors_the_resolver_rules(segments, selected) -> None:
    """Every provider-facing rule the resolver enforces must also fail the transport pre-check.

    A rule the resolver rejects but the transport accepts reaches the player as a
    hard turn failure instead of spending the transport's one recovery attempt.
    """

    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    projector = KnowledgeProjector()
    projection = projector.project(state, "player", "I search the drawer.")
    provider_proposal = parse_turn_proposal({"segments": segments, "selected_knowledge_ids": selected})

    with pytest.raises(ProposalValidationError):
        SelectedRevealResolver(PACKAGE).resolve(state, projection, provider_proposal, projector, "I search the drawer.")

    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider.last_projection = projection
    with pytest.raises(RuntimeContractError):
        provider._parse_eligible_proposal({"segments": segments, "selected_knowledge_ids": selected})


def test_turn_prompt_forbids_selection_when_no_candidate_is_offered(monkeypatch) -> None:
    """A quiet turn must not invite a selection; inventing one costs the player the turn."""

    payloads: list[dict[str, object]] = []

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The room stays quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    provider("I stand still and listen.")
    assert provider.last_projection is not None and provider.last_projection.candidates == ()
    quiet_prompt = payloads[-1]["system"]
    assert "MUST be an empty list" in quiet_prompt
    assert "Select at most one candidate" not in quiet_prompt

    state.active_event_ids.add("SL-1A-B")
    provider("I search the desk drawer for Michelle's recording.")
    offered_prompt = payloads[-1]["system"]
    assert "Select at most one candidate" in offered_prompt
    assert "MUST be an empty list" not in offered_prompt


def test_recovery_hint_tells_the_provider_a_quiet_turn_offers_nothing(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response(
                {
                    "narration": (
                        '{"segments":[{"kind":"narration","text":"An invented reveal."}],'
                        '"selected_knowledge_ids":["k_sl_3c_e_r1"]}'
                    )
                }
            )
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The room stays quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    provider("I stand still and listen.")

    assert len(payloads) == 2
    assert "offers no candidates at all" in payloads[1]["system"]


def test_persistently_ineligible_selection_keeps_the_narration_and_commits_nothing(monkeypatch) -> None:
    """A provider that will not correct itself must not cost the player the turn.

    The narration is kept, the selection and grounding are dropped, so the runtime
    can commit nothing unearned and the player still gets a story beat.
    """

    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"The drawer scrapes open.",'
                    '"grounding_ids":["k_future_unavailable"]}],'
                    '"selected_knowledge_ids":["k_future_unavailable"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I reach for something I have not earned.")

    assert len(payloads) == 2, "the provider still gets exactly one guided recovery"
    assert proposal["selected_knowledge_ids"] == []
    assert proposal["segments"] == [{"kind": "narration", "text": "The drawer scrapes open."}]

    # The sanitized shape must satisfy the runtime rule that rejected it.
    projector = KnowledgeProjector()
    projection = projector.project(state, "player", "I reach for something I have not earned.")
    resolved, _ = SelectedRevealResolver(PACKAGE).resolve(
        state, projection, parse_turn_proposal(proposal), projector, "I reach for something I have not earned."
    )
    assert resolved.selected_knowledge_ids == ()
    assert resolved.events == ()


def test_unparseable_reply_is_still_refused(monkeypatch) -> None:
    """Sanitizing an ineligible selection must not soften a reply we cannot read at all."""

    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response({"narration": '{"segments":[]}'}),
    )

    with pytest.raises(NarrationProviderError, match="invalid proposal"):
        provider("I listen.")


def test_transport_reports_safe_contract_shape_after_failed_recovery(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    with pytest.raises(NarrationProviderError) as caught:
        provider("I listen.")

    assert caught.value.status_code == 502
    assert caught.value.error_code == "INVALID_PROPOSAL"
    assert caught.value.message.endswith("segments:too_short)")
    assert len(payloads) == 2


def test_transport_preserves_worker_capacity_classification(monkeypatch) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )
    error = HTTPError(
        "https://worker.example/turn",
        429,
        "capacity",
        {},
        BytesIO(b'{"status":"error","code":"AI_CAPACITY_EXCEEDED"}'),
    )
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(NarrationProviderError) as caught:
        provider("I listen.")
    assert caught.value.status_code == 429
    assert caught.value.message == "narration service is at capacity"


def test_transport_marks_untyped_worker_errors_for_diagnosis(monkeypatch) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )
    error = HTTPError("https://worker.example/turn", 502, "failure", {}, None)
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(NarrationProviderError) as caught:
        provider("I listen.")
    assert caught.value.error_code == "UNKNOWN"


@pytest.mark.parametrize(("status", "expected"), ((429, 429), (500, 502)))
def test_transport_maps_http_failures(monkeypatch, status, expected) -> None:
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )
    error = HTTPError("https://worker.example/turn", status, "failure", {}, None)
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(NarrationProviderError) as caught:
        provider("I listen.")
    assert caught.value.status_code == expected


def test_opening_prompt_carries_the_authored_scene_frame_without_player_input(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def open_request(request, timeout):
        captured["payload"] = json.loads(request.data)
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The house is silent."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    assert provider.opening() == {"segments": [{"kind": "narration", "text": "The house is silent."}]}
    assert "write only what follows it" in captured["payload"]["system"]
    user = json.loads(captured["payload"]["user"])
    assert "player_input" not in user
    beat = PACKAGE.scenes[0].opening_beat
    assert user["scene_entry"] == {
        "protagonist": "Kristin Schweitzer",
        "location": "McGehee home",
        "phase": "exposition",
        "objective": PACKAGE.scenes[0].metadata.objective,
        "entry_text": PACKAGE.scenes[0].metadata.entry_text,
        "opening_beat": {"id": "1A.1", "title": beat.title, "prose": beat.prose},
    }
    assert user["knowledge_context"]["player"]["scene_id"] == "1A"
    assert "speakers" not in user["knowledge_context"]


def test_request_size_stays_flat_as_the_story_accumulates(monkeypatch) -> None:
    """A late-game turn must not carry a multiple of an early turn's context.

    Context grew three ways at once: committed knowledge accumulated for the whole
    story, the identical list was repeated as sayable_knowledge, and every speaker
    carried another full projection. Together they timed out Act 3 turns.
    """

    captured: list[dict[str, object]] = []

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"ok"}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    def context_bytes(scene_id: str, established: bool) -> int:
        state = RuntimeState.bootstrap(PACKAGE)
        state.current_scene_id = scene_id
        state.phase = next(
            scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id
        )
        if established:
            for fact_id in sorted(PACKAGE.world.facts):
                state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)("I act.")
        context = json.loads(captured[-1]["user"])["knowledge_context"]
        return len(json.dumps(context).encode())

    opening = context_bytes("1A", established=False)
    endgame = context_bytes("3C", established=True)

    assert endgame < 12_000, f"late-game context grew to {endgame} bytes"
    assert endgame < opening * 12, "late-game context must not balloon relative to the opening"

    # The player context must not repeat the speakers' dialogue basis.
    context = json.loads(captured[-1]["user"])["knowledge_context"]
    assert "sayable_knowledge" not in context["player"]
    assert all(set(speaker) == {"sayable_knowledge"} for speaker in context["speakers"].values())
