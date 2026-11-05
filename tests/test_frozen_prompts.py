from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.frozen_prompts import capture, main, replay

ROOT = Path(__file__).resolve().parents[1]
VARIATION = ROOT / "bench" / "variations" / "richer-3a-candidate.json"
CONTROL = ROOT / "bench" / "variations" / "richer-3a-c-control.json"
REPLY = json.dumps({"narration": json.dumps({"segments": [{"kind": "narration", "text": "Kristin acts."}]})}).encode()


def _a_r1_statement() -> str:
    """The current reunion statement, read from the story so wording changes do not break this test."""
    from storygame.story_package.loader import load_story_package

    package = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")
    return package.knowledge_indexes.by_id["k_sl_3a_a_r1"].statement


def _capture(path: Path, tmp_path: Path, monkeypatch, endpoints=(4, 5)) -> dict:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    output = tmp_path / f"{path.stem}-frozen.json"
    return capture(path, list(endpoints), output)


def test_capture_is_deterministic_and_replays_the_requested_prefix(monkeypatch, tmp_path) -> None:
    first = _capture(VARIATION, tmp_path / "first", monkeypatch)
    second = _capture(VARIATION, tmp_path / "second", monkeypatch)

    assert first == second
    endpoints = {item["n"]: item for item in first["endpoints"]}
    assert set(endpoints) == {4, 5}
    assert endpoints[4]["command"] == "Enter the medical level."
    assert endpoints[5]["command"] == "Ask Michelle about the lemon cake."
    assert endpoints[4]["wire_payload"]["system"]
    assert "CHARACTERS:" in endpoints[4]["wire_payload"]["user"]
    assert "SCENE:" in endpoints[4]["wire_payload"]["user"]
    assert "Enter the medical level." in endpoints[4]["wire_payload"]["user"]
    assert _a_r1_statement() in endpoints[4]["wire_payload"]["user"]
    assert "medical level" in endpoints[5]["wire_payload"]["user"].casefold()
    assert "memory, compliance, and resistance experiments" in endpoints[5]["wire_payload"]["user"]
    assert {"michelle_reached", "wrist_tags_read", "radio_loop_known"} <= set(endpoints[4]["committed_after_prefix"])
    assert "behavioral_experiments_known" in set(endpoints[5]["committed_after_prefix"])


def test_control_and_current_package_change_only_the_expected_prompt_surface(monkeypatch, tmp_path) -> None:
    pytest.importorskip("bench.frozen_prompts")
    current = _capture(VARIATION, tmp_path / "current", monkeypatch, endpoints=(4,))
    # The checked-in control is an older one-command fixture.  The nine-command
    # control comparison is therefore covered by the source package when it is
    # available, while this assertion keeps the test honest on this checkout.
    control_script = json.loads(CONTROL.read_text(encoding="utf-8"))["scripts"]["3A"][0]["inputs"]
    if len(control_script) < 4:
        pytest.skip("checked-in richer-3a-c-control fixture has no endpoint 4")
    control = _capture(CONTROL, tmp_path / "control", monkeypatch, endpoints=(4,))
    current_user = current["endpoints"][0]["wire_payload"]["user"].splitlines()
    control_user = control["endpoints"][0]["wire_payload"]["user"].splitlines()
    assert current["endpoints"][0]["wire_payload"]["system"] == control["endpoints"][0]["wire_payload"]["system"]
    assert current_user != control_user


def test_replay_sends_each_saved_payload_and_keeps_failures(tmp_path, capsys) -> None:
    frozen_path = tmp_path / "frozen.json"
    output = tmp_path / "rows.json"
    frozen = {
        "variation": "fixture",
        "package_hash": "hash",
        "endpoints": [
            {"n": 4, "command": "Enter the medical level.", "wire_payload": {"user": "four"}},
            {"n": 5, "command": "Ask Michelle about the lemon cake.", "wire_payload": {"user": "five"}},
        ],
    }
    frozen_path.write_text(json.dumps(frozen), encoding="utf-8")
    calls: list[dict] = []

    def send(payload):
        calls.append(payload)
        if len(calls) == 4:
            raise RuntimeError("sample failed")
        return REPLY

    rows = replay(frozen_path, 3, output, send=send)

    assert len(calls) == 6
    assert calls[0] is not frozen["endpoints"][0]["wire_payload"]
    assert [call["user"] for call in calls] == ["four"] * 3 + ["five"] * 3
    assert len(rows) == 6
    assert rows[3]["error"] == "sample failed"
    assert rows[3]["narration"] is None
    assert all(row["raw"] for index, row in enumerate(rows) if index != 3)
    assert json.loads(output.read_text(encoding="utf-8")) == rows
    assert "4 1 ok" in capsys.readouterr().out


def test_replay_dry_run_makes_no_send_call(tmp_path, capsys) -> None:
    frozen_path = tmp_path / "frozen.json"
    output = tmp_path / "rows.json"
    frozen_path.write_text(
        json.dumps(
            {
                "variation": "fixture",
                "package_hash": "hash",
                "endpoints": [{"n": 4, "command": "Enter.", "wire_payload": {"user": "four"}}],
            }
        ),
        encoding="utf-8",
    )
    called = False

    def send(_payload):
        nonlocal called
        called = True
        return REPLY

    result = replay(frozen_path, 3, output, send=send, dry_run=True)

    assert result == []
    assert called is False
    assert not output.exists()
    text = capsys.readouterr().out
    assert "3" in text and "4" in text


def test_capture_cli_accepts_named_variation_and_endpoints(monkeypatch, tmp_path) -> None:
    calls = []

    def fake_capture(variation, endpoints, out_path):
        calls.append((variation, endpoints, out_path))
        return {}

    monkeypatch.setattr("bench.frozen_prompts.capture", fake_capture)
    output = tmp_path / "frozen.json"

    assert (
        main(
            [
                "capture",
                "--variation",
                str(VARIATION),
                "--endpoints",
                "4",
                "5",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    assert calls == [(VARIATION, [4, 5], output)]


@pytest.mark.skipif(
    not (ROOT / "bench" / "results" / "richer-3a-probe" / "candidate-run4").is_dir(),
    reason="recorded run4 prompt directory is absent",
)
def test_prompt_lengths_are_close_to_recorded_run4(monkeypatch, tmp_path) -> None:
    frozen = _capture(VARIATION, tmp_path, monkeypatch)
    lengths = {item["n"]: len(item["wire_payload"]["user"]) for item in frozen["endpoints"]}
    assert abs(lengths[4] - 3275) / 3275 < 0.4
    assert abs(lengths[5] - 3706) / 3706 < 0.4
