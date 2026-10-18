from __future__ import annotations

import json

import pytest

from scripts.ringer.stage7.segment_replay_probe import MAX_CALLS, classify_body, parse_args, replay


class _Provider:
    def _decode_narration(self, value):
        return json.loads(value)

    def _clean_reply(self, value):
        return value


def test_classifier_flags_stray_segment():
    result = classify_body(
        '{"segments":[{"kind":"narration","text":"ok"},{"selected_knowledge_ids":["x"]}]}', _Provider()
    )
    assert not result["ok"]
    assert result["stray_selected_ids"]


def test_classifier_flags_invalid_kind():
    result = classify_body('{"segments":[{"kind":"thought","text":"no"}]}', _Provider())
    assert not result["ok"]
    assert result["invalid_kind"]
    assert result["bad_segments"][0]["kind_value"] == "thought"


def test_classifier_accepts_clean_reply():
    assert classify_body(
        '{"segments":[{"kind":"action","text":"A door opens."}],"selected_knowledge_ids":[]}', _Provider()
    )["ok"]


def test_parse_args_requires_confirmation(monkeypatch):
    monkeypatch.setattr("sys.argv", ["probe", "--n", "1", "--out", "/tmp/out"])
    with pytest.raises(SystemExit):
        parse_args()


def test_parse_args_refuses_over_twenty(monkeypatch):
    monkeypatch.setattr("sys.argv", ["probe", "--n", "21", "--out", "/tmp/out", "--confirm"])
    with pytest.raises(SystemExit):
        parse_args()


def test_replay_never_exceeds_cap(monkeypatch, tmp_path):
    prompts = {
        cell: {"system": "s", "user": "u", "max_tokens": 1024, "response_format": {"type": "json_object"}}
        for cell in ("reveal", "dialogue", "plain")
    }
    sent = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return b'{"narration":"{\\"segments\\":[{\\"kind\\":\\"narration\\",\\"text\\":\\"ok\\"}]}"}'

    def sender(*_args, **_kwargs):
        sent.append(1)
        return Response()

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setattr("scripts.ringer.stage7.segment_replay_probe.urlopen", sender)
    summary = replay(prompts, 20, tmp_path)
    assert len(sent) == MAX_CALLS
    assert summary["calls"] == MAX_CALLS
