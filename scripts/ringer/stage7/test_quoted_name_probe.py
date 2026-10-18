from __future__ import annotations

import json

import pytest

from scripts.ringer.stage7 import quoted_name_probe as probe


def payload(system: str = "before\n" + probe.ANCHOR + "\nafter") -> dict[str, object]:
    return {"system": system, "user": "same", "max_tokens": 1024}


def test_build_arms_inserts_lines_and_preserves_user():
    arms = probe.build_arms(payload())
    assert set(arms) == set(probe.ARMS)
    assert all(arms[name]["user"] == "same" for name in probe.ARMS)
    assert arms["no_name_quotes"]["system"] == (
        "before\n" + probe.RULE + "\n" + probe.NO_NAME_QUOTES + "\n" + probe.ANCHOR + "\nafter"
    )
    assert arms["speech_only"]["system"] == (
        "before\n" + probe.RULE + "\n" + probe.SPEECH_ONLY + "\n" + probe.ANCHOR + "\nafter"
    )


@pytest.mark.parametrize("system", ["before", "before\n" + probe.ANCHOR + "\n" + probe.ANCHOR])
def test_build_arms_rejects_bad_anchor(system):
    with pytest.raises(AssertionError):
        probe.build_arms(payload(system))


def test_arm_order_rotates_first_slot_equally():
    assert [probe.arm_order(rep)[0] for rep in range(3)] == list(probe.ARMS)


class Provider:
    def _decode_narration(self, value):
        return json.loads(value)

    def _clean_reply(self, value):
        return value


def test_quoted_name_flag():
    raw = '{"segments":[{"kind":"narration","text":"It was called the \\""}]}'
    assert probe.quoted_name_flags(raw, Provider())[:2] == (True, True)
    clean = '{"segments":[{"kind":"narration","text":"It was called the program."}]}'
    assert probe.quoted_name_flags(clean, Provider())[:2] == (False, False)


def test_replay_never_exceeds_cap(monkeypatch, tmp_path):
    sent = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return b'{"segments":[{"kind":"narration","text":"ok"}]}'

    def sender(*_args, **_kwargs):
        sent.append(1)
        return Response()

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid")
    monkeypatch.setattr(probe, "_make_provider", lambda: Provider())
    summary = probe.replay({arm: payload() for arm in probe.ARMS}, 20, tmp_path, sender=sender)
    assert len(sent) == probe.MAX_CALLS
    assert summary["calls"] == probe.MAX_CALLS


def test_parse_args_refuses_over_twenty(monkeypatch):
    monkeypatch.setattr("sys.argv", ["probe", "--n", "21", "--out", "/tmp/out", "--confirm"])
    with pytest.raises(SystemExit):
        probe.parse_args()
