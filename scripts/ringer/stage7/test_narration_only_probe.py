from __future__ import annotations

import json

import pytest

from scripts.ringer.stage7 import narration_only_probe as probe


def payload(system: str = "before\n" + probe.ANCHOR + "\nafter") -> dict[str, object]:
    return {"system": system, "user": "same", "max_tokens": 1024, "response_format": {"type": "json_object"}}


def test_build_arms_inserts_one_rule_and_preserves_user():
    arms = probe.build_arms(payload())
    assert set(arms) == set(probe.ARMS)
    assert all(arms["control"]["user"] == arms[name]["user"] for name in probe.ARMS)
    assert arms["narration_only"]["system"] == "before\n" + probe.RULE + "\n" + probe.ANCHOR + "\nafter"
    assert arms["single_quote"]["system"] == "before\n" + probe.SINGLE_QUOTE_RULE + "\n" + probe.ANCHOR + "\nafter"
    assert probe.RULE == (
        "Every paragraph uses the kind narration. Put spoken words inside the paragraph, in quotation marks. "
        "Do not use any other kind."
    )
    assert probe.SINGLE_QUOTE_RULE == (
        "Every paragraph uses the kind narration. Put spoken words inside the paragraph, in single quotation marks. "
        "Do not use any other kind."
    )


def test_arm_order_rotates_first_slot_equally():
    orders = [probe.arm_order(rep) for rep in range(3)]
    assert [order[0] for order in orders] == list(probe.ARMS)
    assert all(sorted(order) == sorted(probe.ARMS) for order in orders)


@pytest.mark.parametrize("system", ["before", "before\n" + probe.ANCHOR + "\n" + probe.ANCHOR])
def test_build_arms_rejects_missing_or_duplicate_anchor(system):
    with pytest.raises(AssertionError):
        probe.build_arms(payload(system))


class Provider:
    def _decode_narration(self, value):
        return json.loads(value)

    def _clean_reply(self, value):
        return value


def test_classifier_reports_visible_speech_and_brandon():
    clean = probe.classify_body('{"segments":[{"kind":"narration","text":"Brandon says, \\"Stay.\\""}]}', Provider())
    assert clean["ok"]
    assert clean["kinds"] == ["narration"]
    assert clean["speech_visible"]
    assert clean["brandon_named"]

    character = probe.classify_body('{"segments":[{"kind":"character","text":"Brandon: \'Stay.\'"}]}', Provider())
    assert not character["ok"]
    assert character["invalid_kind"]
    assert character["kinds"] == ["character"]
    assert character["speech_visible"]
    assert character["brandon_named"]


def test_replay_never_exceeds_cap(monkeypatch, tmp_path):
    arms = {arm: payload() for arm in probe.ARMS}
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
    summary = probe.replay(arms, 20, tmp_path, sender=sender)
    assert len(sent) == probe.MAX_CALLS
    assert summary["calls"] == probe.MAX_CALLS


@pytest.mark.parametrize(
    ("raw_body", "expected"),
    [
        ('{"narration":"{\\"segments\\":["}', True),
        ('{"narration":"{\\"segments\\":[]}"}', False),
        ('{"segments":[]}', False),
    ],
)
def test_truncated_tracks_strict_inner_narration_json(raw_body, expected):
    assert probe._is_truncated(raw_body) is expected


def test_parse_args_refuses_over_twenty(monkeypatch):
    monkeypatch.setattr("sys.argv", ["probe", "--n", "21", "--out", "/tmp/out", "--confirm"])
    with pytest.raises(SystemExit):
        probe.parse_args()
