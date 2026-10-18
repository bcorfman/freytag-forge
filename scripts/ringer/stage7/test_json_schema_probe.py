from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from scripts.ringer.stage7 import json_schema_probe as probe


def payload(system: str = "before\n" + probe.ANCHOR + "\nafter") -> dict[str, object]:
    return {"system": system, "user": "same", "max_tokens": 1024, "response_format": {"type": "json_object"}}


def test_arms_differ_only_in_response_format(monkeypatch):
    schema = {"type": "object", "properties": {"segments": {"type": "array"}}}
    monkeypatch.setattr(probe, "_schema", lambda: schema)
    arms = probe.build_arms(payload())
    assert {key: value for key, value in arms["json_object"].items() if key != "response_format"} == {
        key: value for key, value in arms["json_schema"].items() if key != "response_format"
    }
    assert arms["json_object"]["response_format"] == {"type": "json_object"}
    assert arms["json_schema"]["response_format"] == {"type": "json_schema", "json_schema": schema}


@pytest.mark.parametrize("system", ["before", "before\n" + probe.ANCHOR + "\n" + probe.ANCHOR])
def test_build_arms_rejects_missing_or_duplicate_anchor(system):
    with pytest.raises(AssertionError):
        probe.build_arms(payload(system))


class Provider:
    def _decode_narration(self, value):
        return json.loads(value)

    def _clean_reply(self, value):
        return value


def test_replay_records_http_error_without_aborting(monkeypatch, tmp_path):
    class Sender:
        def __init__(self):
            self.calls = 0

        def __call__(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise HTTPError(
                    "https://worker.invalid", 400, "bad schema", {"X-Freytag-Rejection-Code": "schema"}, None
                )
            return Response()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return b'{"segments":[{"kind":"narration","text":"ok"}]}'

    sender = Sender()
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setattr(probe, "_make_provider", lambda: Provider())
    arms = {arm: payload() for arm in probe.ARMS}
    summary = probe.replay(arms, 1, tmp_path, sender=sender)
    row = json.loads((tmp_path / "replies.jsonl").read_text().splitlines()[0])
    assert row["http_status"] == 400
    assert row["error_body"] == ""
    assert row["http_error_headers"]["X-Freytag-Rejection-Code"] == "schema"
    assert summary["calls"] == 2


def test_cap_is_forty(monkeypatch, tmp_path):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return b'{"segments":[{"kind":"narration","text":"ok"}]}'

    sent = []

    def sender(*_args, **_kwargs):
        sent.append(1)
        return Response()

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setattr(probe, "_make_provider", lambda: Provider())
    summary = probe.replay({arm: payload() for arm in probe.ARMS}, 20, tmp_path, sender=sender)
    assert len(sent) == probe.MAX_CALLS
    assert summary["calls"] == probe.MAX_CALLS


def test_schema_http_error_stop_rule(monkeypatch, tmp_path):
    def sender(*_args, **_kwargs):
        raise HTTPError("https://worker.invalid", 400, "bad schema", {}, None)

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setattr(probe, "_make_provider", lambda: Provider())
    summary = probe.replay({arm: payload() for arm in probe.ARMS}, 20, tmp_path, sender=sender)
    assert summary["calls"] == 6
    assert (tmp_path / "run-stopped.txt").exists()


def test_parse_args_refuses_over_twenty(monkeypatch):
    monkeypatch.setattr("sys.argv", ["probe", "--n", "21", "--out", "/tmp/out", "--confirm"])
    with pytest.raises(SystemExit):
        probe.parse_args()
