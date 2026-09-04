"""Cloudflare transport keeps its small, fail-closed contract."""

from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

import pytest

from storygame.runtime.cloudflare import MAX_TURN_SEGMENTS, CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.contracts import RuntimeContractError, parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
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
    context = captured["payload"]["user"]
    assert '<speaker id="michelle">' not in context
    assert "concrete immediate consequence" in captured["payload"]["system"]
    instruction = captured["payload"]["system"]
    assert "one paragraph per segment" in instruction
    assert "roughly 30 to 55 words" in instruction
    assert f"at most {MAX_TURN_SEGMENTS} segments" in instruction
    # Arm C keeps Arm B's subtraction of beat prose AND Arm A's prohibitions.
    assert "contradict authored text" in instruction
    assert "<rule>Never invent durable evidence, physical objects, items, or container contents.</rule>" in instruction
    assert "already true" in instruction
    assert "at most two sentences" not in instruction
    assert "selected_knowledge_ids" in captured["payload"]["system"]
    assert "Never reuse a beat's sentences" in captured["payload"]["system"]
    assert "<scene_id>1A</scene_id>" in context
    assert "<candidate>" not in context
    serialized = context.casefold()
    for forbidden in ("janus", "plot_beats", "active_storylets", "narrative_history"):
        assert forbidden not in serialized
    state.active_event_ids.add("SL-1A-B")
    provider("I search the desk drawer for Michelle's recording.")
    drawer_context = captured["payload"]["user"]
    assert '<candidate id="k_sl_1a_b_r2">' in drawer_context
    assert '<candidate id="k_sl_1a_b_r1">' in drawer_context
    assert '<must_convey candidate="k_sl_1a_b_r1">memory card</must_convey>' in drawer_context
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

    result = provider("I look around.")

    assert [segment["text"] for segment in result["segments"]] == [f"Opening {i}." for i in range(5)]
    assert state.last_turn_delivery.segments_truncated is True


def test_transport_leaves_short_reply_untouched(monkeypatch) -> None:
    reply = {"segments": [{"kind": "narration", "text": f"Paragraph {index}."} for index in range(3)]}
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    result = provider("I listen.")

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

    assert provider("I search the drawer.") == {
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
        provider("I search the drawer.")
    assert state.last_turn_delivery.segments_dropped == 0


def test_transport_refuses_reply_with_only_malformed_segments(monkeypatch) -> None:
    reply = {"segments": ["not a segment", {"type": "object"}]}
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", lambda *_args, **_kwargs: _Response(reply))
    provider = CloudflareTurnProvider(
        worker_url="https://worker.example/turn", token="", state=RuntimeState.bootstrap(PACKAGE)
    )

    with pytest.raises(NarrationProviderError, match="invalid proposal"):
        provider("I wait.")


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

    result = provider("I search under the drawers.")

    assert len(result["segments"]) == MAX_TURN_SEGMENTS + 1
    assert result["segments"][-1]["grounding_ids"] == ["k_sl_1a_b_r1"]
    assert "memory card" in result["segments"][-1]["text"]


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

    contexts = [payload["user"] for payload in captured]
    assert all('<candidate id="k_sl_1a_b_r2">' not in context for context in contexts[:2])
    assert '<candidate id="k_sl_1a_b_r2">' in contexts[2]

    storylet = next(storylet for storylet in PACKAGE.storylets if storylet.id == "SL-1A-B")
    beats = {anchor: beat for scene in PACKAGE.scenes for anchor, beat in scene.beats.items()}

    def _bare(value: str) -> str:
        return " ".join(value.replace("*", "").replace(">", "").replace("#", "").split())

    assert all(
        all(f"<beat_detail>{d}</beat_detail>" in contexts[2] for d in beats[link].details)
        for link in storylet.source_links[1:]
    )
    assert all(_bare(beats[link].prose) not in _bare(contexts[2]) for link in storylet.source_links[1:])
    assert state.last_turn_delivery.beats_projected == storylet.source_links[1:]
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

    result = provider("I wait.")

    assert result["selected_knowledge_ids"] == []
    assert "grounding_ids" not in result["segments"][0]
    assert provider.grounding_attributions == ()


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
    assert "offers no candidates" in quiet_prompt
    assert "Select at most one candidate" in quiet_prompt
    assert '"grounding_ids":[' not in quiet_prompt
    assert '"selected_knowledge_ids":[]' in quiet_prompt

    state.active_event_ids.add("SL-1A-B")
    provider("I search the desk drawer for Michelle's recording.")
    offered_prompt = payloads[-1]["system"]
    # An offered reveal is a duty, not an option: permissive wording let the model
    # narrate the earned moment without committing it, stalling the scene.
    assert "selected candidate must be conveyed" in offered_prompt
    assert '<candidate id="k_sl_1a_b_r2">' in payloads[-1]["user"], "the offered candidate IDs must be named"
    assert "must_convey" in offered_prompt
    assert "offers no candidates" not in offered_prompt
    offered_id = provider.last_projection.candidates[0].id
    assert offered_id in payloads[-1]["user"], "the offered candidate must still reach the model"
    # The example deliberately does NOT ground. Showing a grounded selection here
    # taught the model to ground on IDs it had not selected: a live sample went
    # from no failures in sixteen turns to six in eighteen, five of them HTTP 409
    # for grounding on knowledge neither committed nor selected. The engine
    # attributes the delivering segment itself.
    assert '"grounding_ids":[' not in offered_prompt
    assert '"selected_knowledge_ids":[]' in offered_prompt


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
    assert "offers no candidates" in payloads[1]["system"]


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
    assert "write only what follows" in captured["payload"]["system"]
    opening_instruction = captured["payload"]["system"]
    assert "one paragraph per segment" in opening_instruction
    assert "roughly 30 to 55 words" in opening_instruction
    assert f"at most {MAX_TURN_SEGMENTS} segments" in opening_instruction
    assert "contradict" in opening_instruction
    assert "invent physical objects, items, or contents" in opening_instruction
    user = captured["payload"]["user"]
    assert "<player_input>" not in user
    beat = PACKAGE.scenes[0].opening_beat
    location = next(item for item in PACKAGE.world.locations if item.id == PACKAGE.scenes[0].metadata.location_id)
    assert "<protagonist>Kristin Schweitzer</protagonist>" in user
    assert f"<location>{location.name}</location>" in user
    assert "<phase>exposition</phase>" in user
    assert f"<objective>{PACKAGE.scenes[0].metadata.objective}</objective>" in user
    assert f"<beat_title>{beat.title}</beat_title>" in user

    def _bare_beat(value: str) -> str:
        return " ".join(value.replace("*", "").replace(">", "").replace("#", "").split())

    assert all(f"<beat_detail>{d}</beat_detail>" in user for d in beat.details)
    assert _bare_beat(beat.prose) not in _bare_beat(user)
    assert "<scene_id>1A</scene_id>" in user


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
        context = captured[-1]["user"]
        return len(context.encode())

    opening = context_bytes("1A", established=False)
    endgame = context_bytes("3C", established=True)

    assert endgame < 12_000, f"late-game context grew to {endgame} bytes"
    assert endgame < opening * 12, "late-game context must not balloon relative to the opening"

    # The player context must not repeat the speakers' dialogue basis.
    context = captured[-1]["user"]
    assert "sayable_knowledge" not in context
    assert "<speaker" in context


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
    assert "echo the request fields" in payloads[0]["system"]
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

        assert f"<entry_text>{scene.metadata.entry_text.rstrip()}</entry_text>" in user
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
    assert '<candidate id="k_sl_1a_b_r2">' in system or "statement" in system
    assert '<candidate id="k_sl_1a_b_r2">Kristin recovers Michelle' in captured["payload"]["user"]


def _instruction_for(prompt_variant, candidates) -> str:
    """Build a turn instruction directly, without a worker or a live projection."""

    provider = CloudflareTurnProvider.__new__(CloudflareTurnProvider)
    provider.prompt_variant = prompt_variant
    provider.last_projection = SimpleNamespace(
        candidates=candidates, hinted_deliveries=(), handoff_deliveries=()
    )
    return CloudflareTurnProvider._turn_instruction(provider)


NO_CANDIDATE_RULE = "This turn offers no candidates, so selected_knowledge_ids must be empty."


def test_the_no_candidate_rule_is_stated_once_not_twice() -> None:
    """The default rules already carry it; appending again repeated it to the narrator.

    A prompt variant REPLACES the rules block, so that case still needs the
    turn-specific rule appended - but the default path must not double it.
    """

    assert _instruction_for(None, ()).count(NO_CANDIDATE_RULE) == 1
    assert _instruction_for(None, ("k_candidate",)).count(NO_CANDIDATE_RULE) == 0


def test_a_replaced_rules_block_still_gets_the_turn_specific_no_candidate_rule() -> None:
    variant = {"rules": ["Narrate the concrete immediate consequence."]}
    assert _instruction_for(variant, ()).count(NO_CANDIDATE_RULE) == 1
    assert _instruction_for(variant, ("k_candidate",)).count(NO_CANDIDATE_RULE) == 0


def test_a_malformed_rules_block_is_rejected_rather_than_sent() -> None:
    """A variation is authored by hand, so a typo must fail loudly, not reach the narrator."""

    with pytest.raises(ValueError, match="non-empty strings"):
        _instruction_for({"rules": ["Narrate the consequence.", ""]}, ())
    with pytest.raises(ValueError, match="non-empty strings"):
        _instruction_for({"rules": ["Narrate the consequence.", 7]}, ())


def test_a_non_string_output_example_is_rejected() -> None:
    with pytest.raises(ValueError, match="output_example must be a string"):
        _instruction_for({"output_example": {"segments": []}}, ())


def test_omitting_the_output_example_drops_only_that_block() -> None:
    kept = _instruction_for(None, ("k_candidate",))
    dropped = _instruction_for({"include_output_example": False}, ("k_candidate",))
    assert "<output_example>" in kept
    assert "<output_example>" not in dropped
    assert dropped.splitlines() == [line for line in kept.splitlines() if "<output_example>" not in line]
