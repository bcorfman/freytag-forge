"""First-reply repair tests for fused Cloudflare narration segments."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
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


def _provider(provider_type=CloudflareTurnProvider):
    state = RuntimeState.bootstrap(PACKAGE)
    kwargs = {"worker_url": "https://worker.example/turn", "token": "", "state": state}
    if provider_type is ItemFactsProvider:
        kwargs.update(item_facts={}, mode="single_call")
    return provider_type(**kwargs)


def _send(monkeypatch, replies):
    calls = []

    def open_request(*_args, **_kwargs):
        calls.append(1)
        return _Response(replies[min(len(calls) - 1, len(replies) - 1)])

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    return calls


def _fused(*, junk="},{", text="first", narration="second", **extra):
    return {"kind": "narration", "text": text, junk: "kind", "narration": narration, **extra}


def _valid(text="valid"):
    return {"kind": "narration", "text": text}


def test_valid_reply_is_untouched_control(monkeypatch, caplog):
    reply = {"segments": [_valid("one"), _valid("two")], "selected_knowledge_ids": []}
    calls = _send(monkeypatch, [reply])

    assert _provider()("Listen.") == reply
    assert len(calls) == 1
    assert not any("repair" in record.message.casefold() for record in caplog.records)


def test_fused_object_with_a_lettered_extra_key_still_goes_to_recovery_control(monkeypatch):
    first = {"segments": [_fused(junk="extra")], "selected_knowledge_ids": []}
    recovery = {"segments": [_valid("recovered")], "selected_knowledge_ids": []}
    calls = _send(monkeypatch, [first, recovery])

    assert _provider()("Listen.") == recovery
    assert len(calls) == 2


def test_fused_object_without_text_still_goes_to_recovery_control(monkeypatch):
    first = {"segments": [{"kind": "narration", "},{": "kind", "narration": "second"}]}
    recovery = {"segments": [_valid("recovered")], "selected_knowledge_ids": []}
    calls = _send(monkeypatch, [first, recovery])

    assert _provider()("Listen.") == recovery
    assert len(calls) == 2


def test_blank_second_text_still_goes_to_recovery_control(monkeypatch):
    first = {"segments": [_fused(narration="   ")], "selected_knowledge_ids": []}
    recovery = {"segments": [_valid("recovered")], "selected_knowledge_ids": []}
    calls = _send(monkeypatch, [first, recovery])

    assert _provider()("Listen.") == recovery
    assert len(calls) == 2


def test_ungrounded_selection_still_goes_to_recovery_control(monkeypatch):
    first = {"segments": [_fused()], "selected_knowledge_ids": ["not-grounded"]}
    recovery = {"segments": [_valid("recovered")], "selected_knowledge_ids": []}
    calls = _send(monkeypatch, [first, recovery])

    assert _provider()("Listen.") == recovery
    assert len(calls) == 2


def test_recovery_reply_is_never_repaired_control(monkeypatch):
    first = {"segments": [{"kind": "narration"}], "selected_knowledge_ids": []}
    second = {"segments": [_fused()], "selected_knowledge_ids": []}
    calls = _send(monkeypatch, [first, second])

    with pytest.raises(NarrationProviderError, match="invalid proposal"):
        _provider()("Listen.")
    assert len(calls) == 2


def test_fused_object_is_split_into_two_segments_without_a_recovery_request(monkeypatch):
    reply = {"segments": [_fused()], "selected_knowledge_ids": []}
    calls = _send(monkeypatch, [reply])

    result = _provider()("Listen.")

    assert len(calls) == 1
    assert [segment["text"] for segment in result["segments"]] == ["first", "second"]
    assert result["segments"][1]["kind"] == "narration"


def test_recorded_greeting_reply_is_repaired_by_the_real_item_facts_provider(monkeypatch):
    reply = {
        "segments": [
            {
                "kind": "narration",
                "text": '"Officer Reyes, what are you doing here?"',
                "},{": "kind",
                "narration": (
                    "Officer Reyes looks at the splintered back door frame and thrown deadbolt, then back at Kristin."
                ),
            }
        ],
        "selected_knowledge_ids": [],
        "item_facts": {
            "Kristin": {"place": "Michelle's kitchen"},
            "Michelle's kitchen": {"place": "Michelle's kitchen"},
            "Officer Reyes": {"place": "Michelle's workstation"},
        },
    }
    calls = _send(monkeypatch, [reply])
    provider = _provider(ItemFactsProvider)

    result = provider("Listen.")

    assert len(calls) == 1
    assert [segment["text"] for segment in result["segments"]] == [
        '"Officer Reyes, what are you doing here?"',
        "Officer Reyes looks at the splintered back door frame and thrown deadbolt, then back at Kristin.",
    ]
    assert provider.pending_item_facts() is not None
    assert "Officer Reyes" in provider.pending_item_facts()


def test_valid_neighbours_are_kept_and_fused_object_is_split(monkeypatch):
    reply = {"segments": [_valid("before"), _fused(), _valid("after")], "selected_knowledge_ids": []}
    _send(monkeypatch, [reply])

    result = _provider()("Listen.")

    assert [segment["text"] for segment in result["segments"]] == ["before", "first", "second", "after"]


def test_repair_is_logged_once_with_shapes_only(monkeypatch, caplog):
    first_text, second_text = "secret first", "secret second"
    reply = {"segments": [_fused(text=first_text, narration=second_text)], "selected_knowledge_ids": []}
    _send(monkeypatch, [reply])

    with caplog.at_level("WARNING", logger="storygame.runtime.cloudflare"):
        _provider()("Listen.")

    warnings = [record.message for record in caplog.records if "repair" in record.message.casefold()]
    assert len(warnings) == 1
    assert "1" in warnings[0]
    for key in ("kind", "text", "narration", "},{"):
        assert key in warnings[0]
    assert first_text not in warnings[0]
    assert second_text not in warnings[0]


def test_repaired_second_segment_carries_no_grounding_or_speaker(monkeypatch):
    fused = _fused(speaker_id="officer_reyes")
    reply = {"segments": [fused], "selected_knowledge_ids": []}
    _send(monkeypatch, [reply])

    result = _provider()("Listen.")

    assert result["segments"][0]["speaker_id"] == "officer_reyes"
    assert "speaker_id" not in result["segments"][1]
    assert "grounding_ids" not in result["segments"][1]

    fused = _fused(speaker_id="officer_reyes", grounding_ids=["known-id"])
    reply = {"segments": [fused], "selected_knowledge_ids": ["known-id"]}
    repaired = _provider()._repair_fused_segments(reply)

    assert repaired is not None
    assert repaired["segments"][0]["speaker_id"] == "officer_reyes"
    assert repaired["segments"][0]["grounding_ids"] == ["known-id"]
    assert "speaker_id" not in repaired["segments"][1]
    assert "grounding_ids" not in repaired["segments"][1]
