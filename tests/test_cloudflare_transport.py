"""Cloudflare transport keeps its small, fail-closed contract."""

from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from storygame.runtime.cloudflare import (
    DEFAULT_OUTPUT_EXAMPLE,
    MAX_TURN_SEGMENTS,
    CloudflareTurnProvider,
    NarrationProviderError,
)
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError, SelectedRevealResolver
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ItemPlacement

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
AUTHORED_DELIVERY = (
    "Michelle's hidden memory card holds a damaged recording that warns Kristin not to trust emergency broadcasts."
)


def _authored_handoff_package():
    knowledge_id = "k_sl_1a_b_r2"
    knowledge = next(item for item in PACKAGE.knowledge.knowledge if item.id == knowledge_id)
    authored = knowledge.model_copy(update={"delivery_text": AUTHORED_DELIVERY})
    catalog = PACKAGE.knowledge.model_copy(
        update={
            "knowledge": tuple(authored if item.id == knowledge_id else item for item in PACKAGE.knowledge.knowledge),
        }
    )
    indexes = PACKAGE.knowledge_indexes.model_copy(
        update={"by_id": {**PACKAGE.knowledge_indexes.by_id, knowledge_id: authored}}
    )
    return PACKAGE.model_copy(update={"knowledge": catalog, "knowledge_indexes": indexes})


def _assert_memory_card_in_custody(state: RuntimeState) -> None:
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))


def _rendered_character_line(character_id: str) -> str:
    character = next(item for item in PACKAGE.characters if item.id == character_id)
    bio = character.bio
    article = next((item for item in ("A ", "An ") if bio.startswith(item)), None)
    return f"{character.name} is {article.lower()}{bio[len(article) :]}" if article else f"{character.name}: {bio}"


def test_scene_1a_context_uses_only_authored_physical_evidence() -> None:
    frame = next(item for item in PACKAGE.knowledge.scene_frames if item.scene_id == "1A")
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_a_r1"]

    assert "facedown" not in frame.situation.casefold()
    assert "blood" not in reveal.statement.casefold()
    for detail in ("forced entry", "overturned chair", "missing tablet", "work bag"):
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

    assert provider("Listen.") == {"segments": [{"kind": "narration", "text": "A valid proposal."}]}
    assert len(attempts) == 1
    assert state.last_turn_delivery.beats_projected == ()
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert "Mozilla/5.0" in captured["headers"]["User-agent"]
    assert captured["payload"]["max_tokens"] == 1024
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    context = captured["payload"]["user"]
    assert "Dr. Michelle McGehee may say this aloud" not in context
    assert "Show what happens right after the player acts." in captured["payload"]["user"]
    instruction = captured["payload"]["system"]
    assert "Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately." in instruction
    assert "Write each paragraph as one segment and return only JSON in this form:" in instruction
    # Arm C keeps Arm B's subtraction of beat prose AND Arm A's prohibitions.
    assert "Do not say anything that goes against the SCENE section." in captured["payload"]["user"]
    prohibition = "- Do not make up new objects, clues, or things inside containers."
    assert prohibition in captured["payload"]["user"]
    assert "already true" in captured["payload"]["user"]
    assert "at most two sentences" not in instruction
    assert "selected_knowledge_ids" in captured["payload"]["system"]
    assert "Do not copy sentences from the SCENE section." in captured["payload"]["user"]
    # The sections prompt carries the scene as authored situation, never as a runtime id.
    assert "1A" not in context
    assert context.startswith("CHARACTERS:")
    assert "\n\nSCENE:\n" in context and "\n\nCONSTRAINTS:\n" in context
    serialized = context.casefold()
    for forbidden in ("janus", "plot_beats", "active_storylets", "narrative_history"):
        assert forbidden not in serialized
    _assert_memory_card_in_custody(state)
    state.active_event_ids.add("SL-1A-B")
    provider("Search the desk drawer for Michelle's recording.")
    drawer_context = captured["payload"]["user"]
    assert "k_sl_1a_b_r2 in selected_knowledge_ids" in drawer_context
    assert "k_sl_1a_b_r1 in selected_knowledge_ids" in drawer_context
    assert "If you reveal k_sl_1a_b_r1, you must say this: memory card" in drawer_context
    assert provider.last_projection is not None
    assert "damaged recording" in next(
        item.statement for item in provider.last_projection.candidates if item.id == "k_sl_1a_b_r2"
    )
    unbeat_context = provider._serialized_player_context({"beats": []})
    assert "statement" in next(item for item in unbeat_context["candidates"] if item["id"] == "k_sl_1a_b_r2")


def test_transport_caps_long_reply_and_records_telemetry(monkeypatch) -> None:
    reply = {"segments": [{"kind": "narration", "text": f"Opening {index}."} for index in range(9)]}
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    result = provider("Look around.")

    assert [segment["text"] for segment in result["segments"]] == [f"Opening {i}." for i in range(5)]
    assert state.last_turn_delivery.segments_truncated is True


def test_transport_leaves_short_reply_untouched(monkeypatch) -> None:
    reply = {"segments": [{"kind": "narration", "text": f"Paragraph {index}."} for index in range(3)]}
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    result = provider("Listen.")

    assert result == reply
    assert state.last_turn_delivery.segments_truncated is False


@pytest.mark.parametrize(
    "bad_segment",
    [
        "a bare string",
        {"type": "object", "items": {"type": "string"}, "selected_knowledge_ids": []},
    ],
)
def test_transport_salvages_valid_segments_around_malformed_entry(monkeypatch, bad_segment) -> None:
    reply = {
        "segments": [
            {"kind": "narration", "text": "The drawer opens."},
            bad_segment,
            {"kind": "narration", "text": "Dust spills across the floor."},
        ]
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    assert provider("Search the drawer.") == {
        "segments": [
            {"kind": "narration", "text": "The drawer opens."},
            {"kind": "narration", "text": "Dust spills across the floor."},
        ],
        "selected_knowledge_ids": [],
    }
    assert state.last_turn_delivery.segments_dropped == 1


def test_transport_refuses_salvage_when_selected_reveal_is_in_malformed_segment(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    reply = {
        "segments": [
            {"kind": "narration", "text": "The drawer opens."},
            {"grounding_ids": ["k_sl_1a_b_r1"]},
        ],
        "selected_knowledge_ids": ["k_sl_1a_b_r1"],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    with pytest.raises(NarrationProviderError, match="invalid proposal"):
        provider("Search the drawer.")
    assert state.last_turn_delivery.segments_dropped == 0


def test_transport_refuses_reply_with_only_malformed_segments(monkeypatch) -> None:
    reply = {"segments": ["not a segment", {"type": "object"}]}
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    with pytest.raises(NarrationProviderError, match="invalid proposal"):
        provider("Search the drawer.")


def test_transport_keeps_selected_reveal_delivery_after_segment_cap(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    filler = [{"kind": "narration", "text": f"Filler {index}."} for index in range(MAX_TURN_SEGMENTS + 1)]
    delivery = {
        "kind": "narration",
        "text": "Taped beneath the drawer she finds Michelle's hidden memory card and a damaged recording, "
        "naming a dead drop at a bench in the park.",
        "grounding_ids": ["k_sl_1a_b_r1"],
    }
    reply = {"segments": [*filler, delivery], "selected_knowledge_ids": ["k_sl_1a_b_r1"]}
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    result = provider("Search under the drawers.")

    assert len(result["segments"]) == MAX_TURN_SEGMENTS + 1
    assert result["segments"][-1]["grounding_ids"] == ["k_sl_1a_b_r1"]
    assert "memory card" in result["segments"][-1]["text"]


def test_beat_covered_candidate_without_must_convey_keeps_its_statement() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    _assert_memory_card_in_custody(state)
    state.facts.assert_fact(Fact(predicate="michelle_warning_known", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-C")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider.last_projection = provider.projector.project(state, "player", "Search the desk drawer.")

    scene_setting = provider._scene_setting()
    context = provider._serialized_player_context(scene_setting)
    candidate = next(item for item in context["candidates"] if item["id"] == "k_sl_1a_c_r1")

    assert candidate["must_convey"] == []
    assert candidate["statement"] == PACKAGE.knowledge_indexes.by_id["k_sl_1a_c_r1"].statement


def test_recording_candidate_is_absent_until_its_route_is_eligible(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    def open_request(request, **_kwargs):
        captured.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A valid proposal."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider("Inspect the back door.")
    provider("Examine Michelle's phone.")
    _assert_memory_card_in_custody(state)
    state.active_event_ids.clear()
    state.active_event_ids.add("SL-1A-B")
    provider("Search the desk drawer for a damaged recording.")

    contexts = [payload["user"] for payload in captured]
    assert all("k_sl_1a_b_r2" not in context for context in contexts[:2])
    assert "k_sl_1a_b_r2 in selected_knowledge_ids" in contexts[2]

    storylet = next(storylet for storylet in PACKAGE.storylets if storylet.id == "SL-1A-B")
    beats = {anchor: beat for scene in PACKAGE.scenes for anchor, beat in scene.beats.items()}

    def _bare(value: str) -> str:
        return " ".join(value.replace("*", "").replace(">", "").replace("#", "").split())

    assert all(all(f"- {d}" in contexts[2] for d in beats[link].details) for link in storylet.source_links[1:])
    assert all(_bare(beats[link].prose) not in _bare(contexts[2]) for link in storylet.source_links[1:])
    assert state.last_turn_delivery.beats_projected == storylet.source_links
    assert len(storylet.source_links[1:]) < len(PACKAGE.scenes[0].beats)


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

    assert provider("Listen.") == {"segments": [{"kind": "narration", "text": "A valid proposal."}]}


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
        provider("Listen.")

    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline"))
    )
    with pytest.raises(NarrationProviderError, match="unavailable"):
        provider("Listen.")


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

    assert provider("Listen.") == {"segments": [{"kind": "narration", "text": "A recovered proposal."}]}
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

    assert provider("Listen.") == {"segments": [{"kind": "action", "text": "Kristin checks the door."}]}
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

    assert provider("Listen.") == {"segments": [{"kind": "narration", "text": "She opens the drawer."}]}
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

    assert provider("Listen.") == {"segments": [{"kind": "narration", "text": "Recovered."}]}
    assert len(payloads) == 2
    assert "Your last answer was not valid." in payloads[1]["system"]


def test_transport_recovers_once_when_provider_selects_unavailable_knowledge(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    _assert_memory_card_in_custody(state)
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
                    '{"segments":[{"kind":"narration","text":"Kristin finds and secures '
                    "Michelle's hidden memory card, "
                    'then plays its damaged recording: do not trust emergency broadcasts.",'
                    '"grounding_ids":["k_sl_1a_b_r2"]}],'
                    '"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("Search the desk drawer for Michelle's damaged recording.")

    assert proposal["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert len(payloads) == 2
    assert "last answer was not valid" in payloads[1]["system"]
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

    proposal = provider("Search the desk drawer.")

    assert proposal["segments"][0]["text"] == "The drawer sticks, then gives."
    assert len(payloads) == 2
    assert "last answer was not valid" in payloads[1]["system"]
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

    proposal = provider("Look under the workstation.")

    assert proposal["selected_knowledge_ids"] == ["k_sl_1a_b_r1"]
    assert len(payloads) == 1
    assert state.last_turn_delivery.recovery_used is False


def test_transport_auto_selects_one_candidate_when_narration_proves_it(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [
            {
                "kind": "narration",
                "text": (
                    "Kristin finds Michelle's hidden memory card and plays the damaged recording. "
                    "Her warning is not to trust emergency broadcasts."
                ),
            }
        ],
        "selected_knowledge_ids": [],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Recover the interrupted recording and listen to it.")

    assert result["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert result["segments"][0]["grounding_ids"] == ["k_sl_1a_b_r2"]
    assert provider.model_selected_knowledge_ids == ()
    assert provider.recovery_count == 0


def test_authored_handoff_composes_delivery_and_ignores_model_selection(monkeypatch) -> None:
    package = _authored_handoff_package()
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [
            {
                "kind": "narration",
                "text": "Kristin turns toward the desk.",
                "grounding_ids": ["k_future_unavailable"],
            }
        ],
        "selected_knowledge_ids": ["k_future_unavailable"],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Recover the damaged recording and listen to it.")

    assert result["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert result["segments"] == [
        {"kind": "narration", "text": "Kristin turns toward the desk.", "speaker_id": None, "grounding_ids": []},
        {
            "kind": "narration",
            "text": AUTHORED_DELIVERY,
            "speaker_id": None,
            "grounding_ids": ["k_sl_1a_b_r2"],
        },
    ]
    assert provider.model_selected_knowledge_ids == ("k_future_unavailable",)
    assert provider.recovery_count == 0


def test_authored_handoff_uses_normal_validation_and_commits_atomically(monkeypatch) -> None:
    package = _authored_handoff_package()
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {"segments": [{"kind": "narration", "text": "The room settles."}], "selected_knowledge_ids": []}
        ),
    )
    before = state.snapshot()

    proposal = RuntimeEngine(state, provider).turn("Recover the damaged recording and listen to it.")

    assert proposal.selected_knowledge_ids == ("k_sl_1a_b_r2",)
    assert proposal.segments[-1].text == AUTHORED_DELIVERY
    assert state.facts.has("michelle_warning_known", "story", value="true")

    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {
                "segments": [{"kind": "narration", "text": "Brandon reveals the protected future."}],
                "selected_knowledge_ids": [],
            }
        ),
    )

    with pytest.raises(ProposalValidationError):
        RuntimeEngine(state, provider).turn("Recover the damaged recording and listen to it.")

    assert state.snapshot() == before


def test_authored_handoff_prompt_hides_candidate_contract(monkeypatch) -> None:
    package = _authored_handoff_package()
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        prompt_variant={
            "selection_prepass": True,
            "output_example": f'{{"candidate":"k_sl_1a_b_r2","text":"{AUTHORED_DELIVERY}"}}',
        },
    )
    captured: list[dict[str, object]] = []

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return _Response({"segments": [{"kind": "narration", "text": "The room settles."}]})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    result = provider("Recover the damaged recording and listen to it.")

    assert result["segments"][-1]["text"] == AUTHORED_DELIVERY
    assert len(captured) == 1
    prompt = f"{captured[0]['system']}\n{captured[0]['user']}"
    candidate = next(item for item in package.knowledge.knowledge if item.id == "k_sl_1a_b_r2")
    assert candidate.id not in prompt
    assert candidate.statement not in prompt
    assert AUTHORED_DELIVERY not in prompt
    assert "must_convey" not in prompt
    assert "selected_knowledge_ids" not in captured[0]["user"]
    assert "grounding_ids" not in captured[0]["user"]


def test_authored_handoff_recovery_keeps_candidate_contract_hidden(monkeypatch) -> None:
    package = _authored_handoff_package()
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    captured: list[dict[str, object]] = []
    responses = iter(
        [
            {"segments": [{"kind": "narration"}]},
            {"segments": [{"kind": "narration", "text": "The room settles."}]},
        ]
    )

    def open_request(request, timeout):
        captured.append(json.loads(request.data))
        return _Response(next(responses))

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    result = provider("Recover the damaged recording and listen to it.")

    assert result["segments"][-1]["text"] == AUTHORED_DELIVERY
    assert provider.recovery_count == 1
    assert len(captured) == 2
    recovery_system = captured[1]["system"]
    candidate = next(item for item in package.knowledge.knowledge if item.id == "k_sl_1a_b_r2")
    assert candidate.id not in recovery_system
    assert candidate.statement not in recovery_system
    assert AUTHORED_DELIVERY not in recovery_system
    assert "grounding_ids" not in recovery_system
    assert "Put" not in recovery_system
    assert "Do not select a fact." in recovery_system


def test_harness_selected_candidate_still_uses_the_normal_runtime_resolver(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [
            {
                "kind": "narration",
                "text": (
                    "Kristin finds Michelle's hidden memory card and plays the damaged recording. "
                    "Her warning is not to trust emergency broadcasts."
                ),
            }
        ],
        "selected_knowledge_ids": [],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    provider_proposal = provider("Recover the interrupted recording and listen to it.")
    RuntimeEngine(state, lambda _: provider_proposal).turn("Recover the interrupted recording and listen to it.")

    assert "SL-1A-B" in state.fired_event_ids


def test_transport_leaves_ambiguous_or_incomplete_candidates_unselected(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [{"kind": "narration", "text": "Kristin searches the desk and finds a card."}],
        "selected_knowledge_ids": [],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Search the desk.")

    assert result["selected_knowledge_ids"] == []
    assert "grounding_ids" not in result["segments"][0]


def test_transport_harness_selection_can_be_disabled_for_comparison(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        prompt_variant={"auto_select_unambiguous_candidates": False},
    )
    reply = {
        "segments": [
            {
                "kind": "narration",
                "text": "Kristin finds Michelle's hidden memory card and plays the damaged recording.",
            }
        ],
        "selected_knowledge_ids": [],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Recover the interrupted recording and listen to it.")

    assert result["selected_knowledge_ids"] == []


def test_transport_attributes_a_groupless_statement_and_records_telemetry(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "3C"
    state.facts.assert_fact(Fact(predicate="broadcast_started", subject="story", value="true"))
    RuntimeEngine(state, lambda *args, **kwargs: {"segments": []})._activate_pacing()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [
            {"kind": "narration", "text": "The chamber fills with static."},
            {
                "kind": "narration",
                "text": "Michelle broadcasts the captives and JANUS records to independent networks.",
            },
        ],
        "selected_knowledge_ids": ["k_sl_3c_a_r1"],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("We broadcast the evidence.")

    assert result["segments"][1]["grounding_ids"] == ["k_sl_3c_a_r1"]
    assert provider.grounding_attributions == ("k_sl_3c_a_r1",)


def test_transport_drops_an_ungrounded_groupless_selection(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "3C"
    state.facts.assert_fact(Fact(predicate="broadcast_started", subject="story", value="true"))
    RuntimeEngine(state, lambda *args, **kwargs: {"segments": []})._activate_pacing()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [{"kind": "narration", "text": "She waits in the corridor and listens to the vents."}],
        "selected_knowledge_ids": ["k_sl_3c_a_r1"],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Inspect the corridor.")

    assert result["selected_knowledge_ids"] == []
    assert "grounding_ids" not in result["segments"][0]
    assert provider.grounding_attributions == ()


def test_transport_auto_attributes_a_committed_known_term(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    RuntimeEngine(state, lambda *args, **kwargs: {"segments": []})._activate_pacing()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [{"kind": "narration", "text": "Kristin examines Michelle's phone on the kitchen floor."}],
        "selected_knowledge_ids": [],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Look carefully at Michelle's phone.")

    assert "k_scene_1a_entry" in result["segments"][0]["grounding_ids"]
    assert provider.model_grounding_ids == ()


def test_transport_does_not_attribute_an_unavailable_future_term(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    RuntimeEngine(state, lambda *args, **kwargs: {"segments": []})._activate_pacing()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    future_term = "facility entrance"
    future_owner_ids = PACKAGE.knowledge_indexes.term_to_knowledge[future_term]
    committed_ids = {item.id for item in KnowledgeProjector().project(state, "player", "").committed_knowledge}
    assert len(future_owner_ids) == 1
    assert future_owner_ids[0] not in committed_ids
    reply = {
        "segments": [{"kind": "narration", "text": f"The {future_term} waits beyond the trees."}],
        "selected_knowledge_ids": [],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Search the grounds.")

    assert future_owner_ids[0] not in result["segments"][0].get("grounding_ids", [])


def test_transport_does_not_duplicate_existing_committed_grounding(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    RuntimeEngine(state, lambda *args, **kwargs: {"segments": []})._activate_pacing()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    reply = {
        "segments": [
            {
                "kind": "narration",
                "text": "Michelle's phone remains on the kitchen floor.",
                "grounding_ids": ["k_scene_1a_entry"],
            }
        ],
        "selected_knowledge_ids": [],
    }
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))

    result = provider("Check Michelle's phone.")

    assert result["segments"][0]["grounding_ids"].count("k_scene_1a_entry") == 1


def test_transport_retries_a_reveal_the_narration_never_delivers(monkeypatch) -> None:
    """Selecting a candidate without telling it must cost a guided retry, not the player's turn."""

    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    _assert_memory_card_in_custody(state)
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
                    '{"segments":[{"kind":"narration","text":"Kristin finds and secures '
                    "Michelle's hidden memory card, "
                    'then plays its damaged recording: do not trust emergency broadcasts.",'
                    '"grounding_ids":["k_sl_1a_b_r2"]}],"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("Look under the workstation.")

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

    proposal = provider("Search Michelle's workstation.")

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

    proposal = provider("Look under the workstation.")

    assert proposal["selected_knowledge_ids"] == []
    assert proposal["segments"][0]["text"] == "A faint scratch and a few loose screws."
    assert len(payloads) == 2


def test_transport_accepts_grounding_on_the_selected_candidate(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []
    state = RuntimeState.bootstrap(PACKAGE)
    _assert_memory_card_in_custody(state)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"Kristin finds and secures '
                    "Michelle's hidden memory card, "
                    'then plays its damaged recording: do not trust emergency broadcasts.",'
                    '"grounding_ids":["k_sl_1a_b_r2"]}],"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)

    proposal = provider("Play the damaged recording.")

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
    projection = projector.project(state, "player", "Search the drawer.")
    provider_proposal = parse_turn_proposal({"segments": segments, "selected_knowledge_ids": selected})

    with pytest.raises(ProposalValidationError):
        SelectedRevealResolver(PACKAGE).resolve(state, projection, provider_proposal, projector, "Search the drawer.")

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

    provider("Inspect the room.")
    assert provider.last_projection is not None and provider.last_projection.candidates == ()
    quiet_prompt = payloads[-1]["user"]
    assert "This turn has no candidates." in quiet_prompt
    assert "When one or more offered candidates match the player's action, randomly pick one candidate" in quiet_prompt
    assert '"grounding_ids":[' not in payloads[-1]["system"]
    assert '"selected_knowledge_ids":[]' in payloads[-1]["system"]

    state.active_event_ids.add("SL-1A-B")
    provider("Search the desk drawer for Michelle's recording.")
    offered_prompt = payloads[-1]["user"]
    # An offered reveal is a duty, not an option: permissive wording let the model
    # narrate the earned moment without committing it, stalling the scene.
    assert (
        "When one or more offered candidates match the player's action, randomly pick one candidate" in offered_prompt
    )
    assert "k_sl_1a_b_r2" in payloads[-1]["user"], "the offered candidate IDs must be named"
    assert "you must say this" in offered_prompt
    assert "This turn has no candidates." not in offered_prompt
    offered_id = provider.last_projection.candidates[0].id
    assert offered_id in payloads[-1]["user"], "the offered candidate must still reach the model"
    # The coupled selection example remains a bench-only experiment until its
    # live selection rate meets the reliability bar. Ordinary play retains the
    # neutral example.
    assert '"grounding_ids":[' not in offered_prompt
    assert '"selected_knowledge_ids":[]' in payloads[-1]["system"]


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

    provider("Inspect the room.")

    assert len(payloads) == 2
    assert "This turn has no candidates." in payloads[1]["user"]


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

    proposal = provider("Open the drawer under the workstation.")

    assert len(payloads) == 2, "the provider still gets exactly one guided recovery"
    assert proposal["selected_knowledge_ids"] == []
    assert proposal["segments"] == [{"kind": "narration", "text": "The drawer scrapes open."}]

    # The sanitized shape must satisfy the runtime rule that rejected it.
    projector = KnowledgeProjector()
    projection = projector.project(state, "player", "Open the drawer under the workstation.")
    resolved, _ = SelectedRevealResolver(PACKAGE).resolve(
        state, projection, parse_turn_proposal(proposal), projector, "Open the drawer under the workstation."
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
        provider("Listen.")


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
        provider("Listen.")

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
        provider("Listen.")
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
        provider("Listen.")
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
        provider("Listen.")

    assert len(payloads) == 2
    assert "Your last answer was not valid." in payloads[1]["system"]
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
        provider("Listen.")
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
    assert (
        "The player already read the entry text. Write only what comes next. Keep the same voice and tense."
        in captured["payload"]["user"]
    )
    opening_instruction = captured["payload"]["system"]
    assert "Describe each scene in 2-3 paragraphs of 2-3 short sentences, then stop immediately." in opening_instruction
    assert "Write each paragraph as one segment and return only JSON in this form:" in opening_instruction
    assert "Do not say anything that goes against the entry text or the beat details." in captured["payload"]["user"]
    assert "Do not make up new objects, clues, or things inside containers." in captured["payload"]["user"]
    assert "Keep each object where the scene puts it." in captured["payload"]["user"]
    assert "Michelle's phone is on the kitchen floor." in captured["payload"]["user"]
    user = captured["payload"]["user"]
    assert "<player_input>" not in user
    beat = PACKAGE.scenes[0].opening_beat
    location = next(item for item in PACKAGE.world.locations if item.id == PACKAGE.scenes[0].metadata.location_id)
    assert _rendered_character_line("kristin") in user
    assert f"The scene takes place at {location.name}." in user
    objective = PACKAGE.scenes[0].metadata.objective
    assert f"objective is to {objective[0].lower()}{objective[1:]}." in user

    def _bare_beat(value: str) -> str:
        return " ".join(value.replace("*", "").replace(">", "").replace("#", "").split())

    assert all(f"- {d}" in user for d in beat.details)
    assert _bare_beat(beat.prose) not in _bare_beat(user)
    assert "1A" not in user


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
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)("Act.")
        context = captured[-1]["user"]
        return len(context.encode())

    opening = context_bytes("1A", established=False)
    endgame = context_bytes("3C", established=True)

    assert endgame < 12_000, f"late-game context grew to {endgame} bytes"
    assert endgame < opening * 12, "late-game context must not balloon relative to the opening"

    # The player context must not repeat the speakers' dialogue basis.
    context = captured[-1]["user"]
    assert "sayable_knowledge" not in context
    assert "may say this aloud" in context


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

    assert provider("Listen.") == {"segments": [{"kind": "narration", "text": "A recovered proposal."}]}
    assert "Do not repeat the request's labels back." in payloads[0]["user"]
    assert "Do not repeat the request's labels." in payloads[1]["system"]


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

    assert provider("Listen.") == {"segments": [{"kind": "narration", "text": "The corridor holds."}]}
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
        provider("Listen.")
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
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)("Act.")
        user = captured[-1]["user"]
        scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == scene_id)

        assert scene.metadata.entry_text.strip().splitlines()[0] in user
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
    _assert_memory_card_in_custody(state)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    captured: dict[str, object] = {}

    def open_request(request, *_args, **_kwargs):
        captured["payload"] = json.loads(request.data)
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"A reply."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider("Search the desk drawer for Michelle's recording.")

    system = captured["payload"]["system"]
    assert "k_sl_1a_b_r2" in captured["payload"]["user"] or "statement" in system
    assert "Kristin finds and secures Michelle's hidden memory card" in captured["payload"]["user"]


def _instruction_for(prompt_variant, candidates) -> str:
    """Build a turn's rule block directly, without a worker or a live projection."""

    provider = CloudflareTurnProvider.__new__(CloudflareTurnProvider)
    provider.state = RuntimeState.bootstrap(PACKAGE)
    provider.prompt_variant = prompt_variant
    provider.last_projection = SimpleNamespace(candidates=candidates, hinted_deliveries=(), handoff_deliveries=())
    return "\n".join(CloudflareTurnProvider._turn_rules(provider))


NO_CANDIDATE_RULE = "This turn has no candidates. Leave selected_knowledge_ids empty."


def test_turn_rules_name_possessive_items_in_the_current_scene() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    rules = provider._turn_rules()

    assert "Say who owns a thing the first time you name it: Michelle's phone, Kristin's laptop." in rules


def test_turn_rules_omit_owner_rule_when_scene_items_are_not_possessive() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    assert not any("owner" in rule for rule in provider._turn_rules())


def test_turn_rules_derive_owner_name_from_the_package() -> None:
    phone = next(item for item in PACKAGE.world.items if item.id == "michelle_phone")
    custom_phone = phone.model_copy(update={"name": "Avery's handset"})
    custom_world = PACKAGE.world.model_copy(
        update={"items": tuple(custom_phone if item.id == phone.id else item for item in PACKAGE.world.items)}
    )
    custom_package = PACKAGE.model_copy(update={"world": custom_world})
    provider = CloudflareTurnProvider(worker_url="", token="", state=RuntimeState.bootstrap(custom_package))

    rules = provider._turn_rules()

    assert "Avery's handset" in next(rule for rule in rules if "Say who owns" in rule)


def test_turn_rules_include_authored_item_placement() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    assert "Michelle's phone is on the kitchen floor." in provider._turn_rules()


def test_turn_rules_include_kristins_laptop_placement() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    assert "Kristin's laptop is in Kristin's truck outside the house." in provider._turn_rules()


def test_turn_rules_omit_item_placement_when_scene_has_none() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    assert not any("kitchen floor" in rule for rule in provider._turn_rules())


def test_item_placement_rule_uses_package_name_and_placement() -> None:
    phone = next(item for item in PACKAGE.world.items if item.id == "michelle_phone")
    custom_phone = phone.model_copy(update={"name": "Avery's handset"})
    custom_world = PACKAGE.world.model_copy(
        update={"items": tuple(custom_phone if item.id == phone.id else item for item in PACKAGE.world.items)}
    )
    scene = PACKAGE.scenes[0]
    custom_metadata = scene.metadata.model_copy(update={"item_placements": {"michelle_phone": "beneath the window"}})
    custom_scene = scene.model_copy(update={"metadata": custom_metadata})
    custom_package = PACKAGE.model_copy(update={"world": custom_world, "scenes": (custom_scene, *PACKAGE.scenes[1:])})
    provider = CloudflareTurnProvider(worker_url="", token="", state=RuntimeState.bootstrap(custom_package))

    assert "Avery's handset is beneath the window." in provider._turn_rules()


def test_guarded_item_placement_rule_tracks_guard_fact() -> None:
    scene = PACKAGE.scenes[0]
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    assert "Hidden memory card is taped under a drawer in Michelle's workstation." in provider._turn_rules()

    _assert_memory_card_in_custody(state)
    assert "Hidden memory card is taped under a drawer in Michelle's workstation." not in provider._turn_rules()

    metadata = scene.metadata.model_copy(
        update={
            "item_placements": {
                "memory_card": ItemPlacement(
                    placement="taped beneath the workstation drawer",
                    while_fact_false="michelle_abduction_suspicion",
                )
            }
        }
    )
    custom_package = PACKAGE.model_copy(
        update={"scenes": (scene.model_copy(update={"metadata": metadata}), *PACKAGE.scenes[1:])}
    )
    state = RuntimeState.bootstrap(custom_package)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    assert "Hidden memory card is taped beneath the workstation drawer." in provider._turn_rules()

    state.facts.assert_fact(Fact(predicate="michelle_abduction_suspicion", subject="story", value="false"))
    assert "Hidden memory card is taped beneath the workstation drawer." in provider._turn_rules()
    state.facts.assert_fact(Fact(predicate="michelle_abduction_suspicion", subject="story", value="true"))
    assert "Hidden memory card is taped beneath the workstation drawer." not in provider._turn_rules()


def test_turn_rules_sharpen_the_authored_place_rule() -> None:
    rules = _instruction_for(None, ()).splitlines()

    assert "Use the places and details the story gives you." in rules
    assert "Keep each object where the scene puts it." in rules


def test_selection_duty_uses_one_random_choice_rule() -> None:
    rules = _instruction_for(None, ("k_candidate",)).splitlines()

    assert (
        rules.count(
            "When one or more offered candidates match the player's action, randomly pick one candidate from that "
            "list and put its ID in selected_knowledge_ids."
        )
        == 1
    )


def test_candidate_prompt_includes_earning_cue_and_a_selected_example() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(
        worker_url="", token="", state=state, prompt_variant={"positive_selection_example": True}
    )

    prompt = provider.assemble_turn_prompt("Recover Michelle's damaged recording and listen to it.")

    assert (
        "Earn it when the player recovers Michelle's damaged recording and listens to it."
        in provider._section_user_prompt(prompt["context"])
    )
    assert '"selected_knowledge_ids":["k_sl_1a_b_r1"]' in prompt["system"]
    assert '"grounding_ids":["k_sl_1a_b_r1"]' in prompt["system"]


def test_selection_probe_asks_for_only_an_offered_id(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def open_request(request, timeout):
        captured["payload"] = json.loads(request.data)
        return _Response({"narration": '{"selected_knowledge_ids":["k_sl_1a_b_r1"]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    selected = provider.selection_probe("Recover Michelle's damaged recording and listen to it.")

    assert selected == ("k_sl_1a_b_r1",)
    payload = captured["payload"]
    assert payload["max_tokens"] == 32
    assert "segments" not in payload["system"]
    assert "grounding_ids" not in payload["system"]
    assert "narration" not in payload["user"]
    assert "k_sl_1a_b_r1" in payload["user"]
    assert "k_sl_1a_b_r2" in payload["user"]


def test_two_pass_selection_uses_only_a_matcher_backed_id(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []

    def open_request(request, timeout):
        payload = json.loads(request.data)
        payloads.append(payload)
        if len(payloads) == 1:
            return _Response({"narration": '{"selected_knowledge_ids":["k_sl_1a_b_r2"]}'})
        return _Response(
            {
                "narration": (
                    '{"segments":[{"kind":"narration","text":"Michelle\'s memory card holds a damaged '
                    'recording that says not to trust emergency broadcasts."}],'
                    '"selected_knowledge_ids":["k_sl_1a_b_r2"]}'
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        prompt_variant={"selection_prepass": True, "narrow_to_shadow_match": True, "model_grounding": False},
    )

    response = provider(
        "Try to recover the interrupted message she was recording, and listen to whatever survives of it."
    )

    assert response["selected_knowledge_ids"] == ["k_sl_1a_b_r2"]
    assert provider.preselected_knowledge_id == "k_sl_1a_b_r2"
    assert len(payloads) == 2
    assert payloads[0]["max_tokens"] == 32
    assert payloads[1]["max_tokens"] == 1024
    assert "Earn it only when" in payloads[0]["user"]
    assert "first check picked k_sl_1a_b_r2" in payloads[1]["user"]
    assert '"selected_knowledge_ids":["k_sl_1a_b_r2"]' in payloads[1]["system"]
    assert "grounding_ids" not in payloads[1]["system"]


def test_two_pass_selection_fails_closed_without_matcher_evidence(monkeypatch) -> None:
    payloads: list[dict[str, object]] = []

    def open_request(request, timeout):
        payloads.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"Kristin searches the drawers."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        prompt_variant={"selection_prepass": True, "narrow_to_shadow_match": True},
    )

    provider("Search the office drawers for a spare key.")

    assert provider.model_selected_knowledge_ids == ()
    assert provider.preselected_knowledge_id is None
    assert len(payloads) == 1
    assert payloads[0]["max_tokens"] == 1024
    assert "first check found no earned candidate" in payloads[0]["user"]


def test_unmatched_action_does_not_receive_an_offered_candidate_as_an_example() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(
        worker_url="", token="", state=state, prompt_variant={"positive_selection_example": True}
    )

    prompt = provider.assemble_turn_prompt("Inspect the room for signs of a struggle.")

    assert '"selected_knowledge_ids":[]' in prompt["system"]
    assert '"k_sl_1a_b_r1"' not in prompt["system"]


def test_shadow_matcher_records_a_unique_candidate_without_changing_the_prompt() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)

    prompt = provider.assemble_turn_prompt("Recover the interrupted message and listen to it.")

    assert provider.shadow_matched_candidate_id == "k_sl_1a_b_r2"
    assert "action_evidence" not in prompt["system"]
    assert "action_evidence" not in provider._section_user_prompt(prompt["context"])


def test_shadow_narrowing_hides_other_candidates_from_the_prompt_not_the_resolver() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(
        worker_url="", token="", state=state, prompt_variant={"narrow_to_shadow_match": True}
    )

    prompt = provider.assemble_turn_prompt("Recover the interrupted message and listen to it.")
    user = provider._section_user_prompt(prompt["context"])

    assert provider.shadow_matched_candidate_id == "k_sl_1a_b_r2"
    assert provider.prompt_candidate_ids == ("k_sl_1a_b_r2",)
    assert {candidate.id for candidate in provider.last_projection.candidates} == {"k_sl_1a_b_r1", "k_sl_1a_b_r2"}
    assert "k_sl_1a_b_r2" in user
    assert "k_sl_1a_b_r1" not in user


def test_selection_only_variant_does_not_ask_the_model_to_ground_candidates() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, prompt_variant={"model_grounding": False})

    prompt = provider.assemble_turn_prompt("Recover Michelle's damaged recording and listen to it.")
    user = provider._section_user_prompt(prompt["context"])

    assert "grounding_ids" not in user
    assert "Put k_sl_1a_b_r2 in selected_knowledge_ids." in user


def test_the_no_candidate_rule_is_stated_once_not_twice() -> None:
    """The default rules already carry it; appending again repeated it to the narrator.

    A prompt variant REPLACES the rules block, so that case still needs the
    turn-specific rule appended - but the default path must not double it.
    """

    assert _instruction_for(None, ()).count(NO_CANDIDATE_RULE) == 1
    assert _instruction_for(None, ("k_candidate",)).count(NO_CANDIDATE_RULE) == 0


def test_a_replaced_rules_block_still_gets_the_turn_specific_no_candidate_rule() -> None:
    variant = {"rules": ["Show what happens right after the player acts."]}
    assert _instruction_for(variant, ()).count(NO_CANDIDATE_RULE) == 1
    assert _instruction_for(variant, ("k_candidate",)).count(NO_CANDIDATE_RULE) == 0


def test_a_malformed_rules_block_is_rejected_rather_than_sent() -> None:
    """A variation is authored by hand, so a typo must fail loudly, not reach the narrator."""

    with pytest.raises(ValueError, match="non-empty strings"):
        _instruction_for({"rules": ["Narrate the consequence.", ""]}, ())
    with pytest.raises(ValueError, match="non-empty strings"):
        _instruction_for({"rules": ["Narrate the consequence.", 7]}, ())


def test_a_non_string_output_example_is_rejected() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(
        worker_url="", token="", state=state, prompt_variant={"output_example": {"segments": []}}
    )

    with pytest.raises(ValueError, match="output_example must be a string"):
        provider._system_prompt()


def test_omitting_the_output_example_drops_only_that_block() -> None:
    """The example is the last two lines of the system prompt; the rest must not move."""

    state = RuntimeState.bootstrap(PACKAGE)
    kept = CloudflareTurnProvider(worker_url="", token="", state=state)._system_prompt()
    dropped = CloudflareTurnProvider(
        worker_url="", token="", state=state, prompt_variant={"include_output_example": False}
    )._system_prompt()

    assert DEFAULT_OUTPUT_EXAMPLE in kept
    assert DEFAULT_OUTPUT_EXAMPLE not in dropped
    assert "Send back only JSON" not in dropped
    assert dropped.splitlines() == kept.splitlines()[: len(dropped.splitlines())]


def test_sections_prompt_introduces_only_the_characters_this_scene_involves() -> None:
    """A package's cast is written for a reader who finished the story.

    Sending all of it would hand the narrator characters the player has not met
    and motives the plot has not reached, so only the scene's own participants
    are introduced.
    """

    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    RuntimeEngine(state, provider)._activate_pacing()

    user = provider._section_user_prompt(provider.assemble_turn_prompt("Look around the kitchen.")["context"])
    characters = user.split("SCENE:")[0]

    assert _rendered_character_line("kristin") in characters
    assert _rendered_character_line("michelle") in characters
    for absent in ("Charles Jenkins", "Rebecca Jenkins", "Brandon Corfman"):
        assert absent not in characters, f"{absent} does not appear in Scene 1A"


def test_a_characters_concealed_history_never_reaches_the_narrator() -> None:
    """plot.md may state what a character hides; the narrator may not be told it.

    Brandon Corfman's authored biography names the involvement he conceals, and
    that is brandon_history, which world.yaml declares protected. Protected
    knowledge is otherwise enforced only against fact mutation, so nothing but
    this substitution keeps it out of the prompt.
    """

    brandon = next(item for item in PACKAGE.characters if item.id == "brandon")
    plot_text = Path("data/stories/continuity-initiative/plot.md").read_text(encoding="utf-8")

    assert "conceals his own past involvement" in plot_text
    assert "brandon_history" in PACKAGE.world.protected_knowledge
    assert "conceals" not in brandon.bio
    assert "AI software" not in brandon.bio
