"""Cloudflare transport keeps its small, fail-closed contract."""

from __future__ import annotations

import json
import logging
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


def test_scene_1a_context_uses_only_authored_physical_evidence() -> None:
    frame = next(item for item in PACKAGE.knowledge.scene_frames if item.scene_id == "1A")
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_a_r1"]

    assert "facedown" not in frame.situation.casefold()
    assert "blood" not in reveal.statement.casefold()
    for detail in ("forced entry", "overturned chair", "missing laptop", "work bag"):
        assert detail in reveal.statement.casefold()


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
    attempts: list[int] = []

    def open_request(request, timeout):
        attempts.append(1)
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A valid proposal."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="secret", state=state)

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "A valid proposal."}]}
    assert len(attempts) == 1
    assert state.last_turn_delivery.beats_projected == ()
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert "Mozilla/5.0" in captured["headers"]["User-agent"]
    assert captured["payload"]["max_tokens"] == 1024
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    response_schema = json.loads(captured["payload"]["user"])["response_schema"]
    assert len(json.dumps(response_schema)) <= 700
    assert set(response_schema["properties"]) == {"segments", "selected_knowledge_ids"}
    assert set(response_schema["properties"]["segments"]["items"]["properties"]) == {
        "kind",
        "text",
        "speaker_id",
        "grounding_ids",
    }
    context = json.loads(captured["payload"]["user"])["knowledge_context"]
    assert "michelle" not in context["speakers"]
    assert "response_schema" in captured["payload"]["user"]
    assert "concrete immediate consequence" in captured["payload"]["system"]
    instruction = captured["payload"]["system"]
    assert "several paragraphs as separate segments" in instruction
    assert "roughly 30 to 55 words" in instruction
    assert "authored entry_text and authored beat details are already true" not in instruction
    assert "invent physical objects, items, or contents" not in instruction
    assert "at most two sentences" not in instruction
    assert "selected_knowledge_ids" in captured["payload"]["system"]
    assert "Never copy, reproduce, or reuse a beat's own sentences verbatim" in captured["payload"]["system"]
    assert context["player"]["scene_id"] == "1A"
    assert context["player"]["candidates"] == []
    serialized = json.dumps(context).casefold()
    for forbidden in ("janus", "plot_beats", "entry_text", "active_storylets", "narrative_history"):
        assert forbidden not in serialized
    state.active_event_ids.add("SL-1A-B")
    provider("I search the desk drawer for Michelle's recording.")
    drawer_context = json.loads(captured["payload"]["user"])["knowledge_context"]["player"]
    candidate = next(item for item in drawer_context["candidates"] if item["id"] == "k_sl_1a_b_r2")
    assert "statement" in candidate
    assert set(candidate) == {"id", "statement", "must_convey"}
    assert candidate["must_convey"] == []
    grouped_candidate = next(item for item in drawer_context["candidates"] if item["id"] == "k_sl_1a_b_r1")
    assert "statement" not in grouped_candidate
    assert set(grouped_candidate) == {"id", "must_convey"}
    assert provider.last_projection is not None
    assert "damaged recording" in next(
        item.statement for item in provider.last_projection.candidates if item.id == candidate["id"]
    )
    unbeat_context = provider._serialized_player_context({"beats": []})
    assert "statement" in next(item for item in unbeat_context["candidates"] if item["id"] == candidate["id"])


def test_beat_covered_candidate_without_must_convey_keeps_its_statement() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider.last_projection = provider.projector.project(state, "player", "I search the desk drawer.")

    scene_setting = provider._scene_setting()
    context = provider._serialized_player_context(scene_setting)
    candidate = next(item for item in context["candidates"] if item["id"] == "k_sl_1a_b_r2")

    assert candidate["must_convey"] == []
    assert candidate["statement"] == PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r2"].statement


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

    scene_setting = json.loads(captured[2]["user"])["scene_setting"]
    storylet = next(storylet for storylet in PACKAGE.storylets if storylet.id == "SL-1A-B")
    beats = {anchor: beat for scene in PACKAGE.scenes for anchor, beat in scene.beats.items()}
    expected_beats = [
        {
            "title": beats[link].title,
            "anchor": beats[link].anchor,
            "details": list(beats[link].details),
            "your_job": "Cover these concrete details as far as the player's action reaches.",
        }
        for link in storylet.source_links[1:]
    ]
    assert scene_setting["beats"] == expected_beats
    assert state.last_turn_delivery.beats_projected == storylet.source_links[1:]
    assert len(scene_setting["beats"]) < len(PACKAGE.scenes[0].beats)


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


def test_transport_keeps_the_finished_segments_of_a_truncated_reply(monkeypatch) -> None:
    """A reply cut off mid-word still costs the player nothing but its unfinished tail."""

    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"She opens the drawer."},'
                    '{"kind":"narration","text":"The card is co'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "She opens the drawer."}]}
    assert len(payloads) == 1
    assert state.last_turn_delivery.recovery_used


def test_transport_recovers_once_from_a_reply_with_no_salvageable_segment(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response({"narration": '{"segments":[{"kind":"narration","text":"cut off befo'})
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"Recovered."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "Recovered."}]}
    assert len(payloads) == 2
    assert "Your previous response was invalid." in payloads[1]["system"]


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
                    '{"segments":[{"kind":"narration","text":"Michelle\'s damaged recording crackles.",'
                    '"grounding_ids":["k_sl_1a_b_r2"]}],'
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


def test_transport_derives_grounding_without_a_recovery_request(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"Kristin finds Michelle\'s memory card and '
                    'damaged recording; the card points to a dead drop at the park bench."}],'
                    '"selected_knowledge_ids":["k_sl_1a_b_r1"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I look under the workstation.")

    assert proposal["selected_knowledge_ids"] == ["k_sl_1a_b_r1"]
    assert len(payloads) == 1
    assert state.last_turn_delivery.recovery_used is False


def test_transport_retries_a_reveal_the_narration_never_delivers(monkeypatch) -> None:
    """Selecting a candidate without telling it must cost a guided retry, not the player's turn."""

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
                        '{"segments":[{"kind":"narration","text":"A faint scratch and a few loose screws."}],'
                        '"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                    )
                }
            )
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"Taped under the drawer, a card and a recording.",'
                    '"grounding_ids":["k_sl_1a_b_r2"]}],"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I look under the workstation.")

    assert proposal["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert len(payloads) == 2
    assert "k_sl_1a_b_r2" in payloads[1]["system"]
    # The correction must say what is missing: the telling, not just the ID.
    assert "would never learn it" in payloads[1]["system"]


def test_transport_retries_a_partially_conveyed_reveal(monkeypatch) -> None:
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
                        '{"segments":[{"kind":"narration","text":"Michelle fears the emergency broadcasts.",'
                        '"grounding_ids":["k_sl_1a_b_r1"]}],"selected_knowledge_ids":["k_sl_1a_b_r1"]}'
                    )
                }
            )
        return _Response(
            {
                "narration": json.dumps(
                    {
                        "segments": [
                            {
                                "kind": "narration",
                                "text": PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r1"].statement,
                                "grounding_ids": ["k_sl_1a_b_r1"],
                            }
                        ],
                        "selected_knowledge_ids": ["k_sl_1a_b_r1"],
                    }
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I search Michelle's workstation.")

    assert proposal["selected_knowledge_ids"] == ["k_sl_1a_b_r1"]
    assert len(payloads) == 2
    assert "memory card" in payloads[1]["system"]
    assert "must_convey" in payloads[1]["system"]
    assert state.last_turn_delivery.must_convey_misses == ("k_sl_1a_b_r1",)
    assert state.last_turn_delivery.recovery_used is True
    assert state.last_turn_delivery.fallback_used is False


def test_transport_drops_a_reveal_it_will_not_narrate_rather_than_committing_it(monkeypatch) -> None:
    """A provider that never delivers the reveal loses the selection, not the turn."""

    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"A faint scratch and a few loose screws."}],'
                    '"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("I look under the workstation.")

    assert proposal["selected_knowledge_ids"] == []
    assert proposal["segments"][0]["text"] == "A faint scratch and a few loose screws."
    assert len(payloads) == 2


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


def test_turn_prompt_matches_what_the_turn_actually_offers(monkeypatch) -> None:
    """A quiet turn must not invite a selection, and an offered reveal must be claimed.

    Inventing an ID on a quiet turn costs the player the turn; declining an earned
    reveal costs the story its progress and stalls the scene.
    """

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
    # An offered reveal is a duty, not an option: permissive wording let the model
    # narrate the earned moment without committing it, stalling the scene.
    assert "MUST reveal it" in offered_prompt
    assert "k_sl_1a_b_r2" in offered_prompt, "the offered candidate IDs must be named"
    assert "must_convey" in offered_prompt
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


def test_transport_preserves_worker_capacity_classification(monkeypatch, caplog) -> None:
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

    with (
        caplog.at_level(logging.WARNING, logger="storygame.runtime.cloudflare"),
        pytest.raises(NarrationProviderError) as caught,
    ):
        provider("I listen.")
    assert caught.value.status_code == 429
    assert caught.value.message == "narration service is at capacity"
    assert any("AI_CAPACITY_EXCEEDED" in record.getMessage() for record in caplog.records)


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


def test_unsalvageable_worker_response_fails_closed_after_one_recovery_and_logs_decode_cause(
    monkeypatch, caplog
) -> None:
    payloads: list[dict[str, object]] = []
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=RuntimeState.bootstrap(PACKAGE),
    )

    def open_request(request, **_kwargs):
        payloads.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"cut off befo'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    with (
        caplog.at_level(logging.WARNING, logger="storygame.runtime.cloudflare"),
        pytest.raises(NarrationProviderError, match="unavailable"),
    ):
        provider("I listen.")

    assert len(payloads) == 2
    assert "Your previous response was invalid." in payloads[1]["system"]
    assert any(
        record.levelno >= logging.WARNING and "JSONDecodeError" in record.getMessage() for record in caplog.records
    )


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
    opening_instruction = captured["payload"]["system"]
    assert "several paragraphs as separate segments" in opening_instruction
    assert "roughly 30 to 55 words" in opening_instruction
    assert "authored entry_text and authored beat details are already true" not in opening_instruction
    assert "invent physical objects, items, or contents" not in opening_instruction
    user = json.loads(captured["payload"]["user"])
    assert "player_input" not in user
    beat = PACKAGE.scenes[0].opening_beat
    location = next(item for item in PACKAGE.world.locations if item.id == PACKAGE.scenes[0].metadata.location_id)
    assert user["scene_entry"] == {
        "protagonist": "Kristin Schweitzer",
        "location": location.name,
        "phase": "exposition",
        "objective": PACKAGE.scenes[0].metadata.objective,
        "entry_text": PACKAGE.scenes[0].metadata.entry_text,
        "opening_beat": {"id": "1A.1", "title": beat.title, "details": list(beat.details)},
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


def test_prompts_forbid_echoing_the_request(monkeypatch) -> None:
    """A provider that echoed the request back cost the player a turn with HTTP 502.

    The reply carried knowledge_context, player_input and response_schema instead of
    a proposal, which is unparseable and so cannot be salvaged after the fact.
    """

    payloads: list[dict[str, object]] = []

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response({"narration": '{"player_input":"x","knowledge_context":{},"response_schema":{}}'})
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A recovered proposal."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "A recovered proposal."}]}
    assert "never echo" in payloads[0]["system"]
    assert "echoed back" in payloads[1]["system"]


def test_one_transient_connection_failure_does_not_lose_the_turn(monkeypatch) -> None:
    """A momentary connection failure ended a thirty-turn playthrough on its third turn."""

    attempts: list[int] = []

    def open_request(request, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            raise URLError("connection reset")
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The corridor holds."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    assert provider("I listen.") == {"segments": [{"kind": "narration", "text": "The corridor holds."}]}
    assert len(attempts) == 2


def test_a_sustained_outage_still_fails_closed(monkeypatch) -> None:
    attempts: list[int] = []

    def open_request(request, timeout):
        attempts.append(1)
        raise URLError("offline")

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    with pytest.raises(NarrationProviderError, match="unavailable"):
        provider("I listen.")
    assert len(attempts) == 2, "exactly one retry, never an unbounded loop"


def test_turn_carries_the_scene_entry_text_but_never_its_protected_beat(monkeypatch) -> None:
    """A turn needs authored place detail, but not the reveal the scene is built around.

    Without any authored setting the narrator answered an apt search with "you find
    nothing". With the beat prose or the location's own name, Scene 2B would hand it
    JANUS before the player earns it - the archive is literally named "JANUS archive".
    """

    captured: list[dict[str, object]] = []

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"ok"}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    for scene_id in ("1A", "2B", "3C"):
        state = RuntimeState.bootstrap(PACKAGE)
        state.current_scene_id = scene_id
        state.phase = next(
            scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id
        )
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)("I act.")
        user = captured[-1]["user"]
        scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == scene_id)

        assert json.loads(user)["scene_setting"] == {"entry_text": scene.metadata.entry_text.rstrip()}
        assert scene.opening_beat.prose not in user, f"{scene_id} leaked its opening beat prose"
        assert "janus" not in user.casefold(), f"{scene_id} leaked protected knowledge into an ordinary turn"


def test_instruction_points_at_the_statement_for_a_candidate_with_no_groups(monkeypatch) -> None:
    """A reveal with no must_convey groups must still be deliverable.

    Fifty-three of the story's sixty-one reveals declare no groups. An earlier
    instruction told the model to convey a candidate "through the beat plus its
    must_convey groups", which names nothing at all for those reveals, and
    scene 3C - whose ten reveals all declare no groups - stalled twice in
    hosted playthroughs because nothing ever committed.
    """

    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    captured: dict[str, object] = {}

    def open_request(request, *_args, **_kwargs):
        captured["payload"] = json.loads(request.data)
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A reply."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider("I search the desk drawer for Michelle's recording.")

    system = captured["payload"]["system"]
    assert "statement" in system, "the instruction must name the statement as a delivery source"
    candidates = json.loads(captured["payload"]["user"])["knowledge_context"]["player"]["candidates"]
    groupless = [item for item in candidates if not item.get("must_convey")]
    assert groupless, "the fixture must offer a candidate that declares no must_convey groups"
    assert all((item.get("statement") or "").strip() for item in groupless), (
        "a candidate with no groups must carry a statement, or the model is told to deliver nothing"
    )
