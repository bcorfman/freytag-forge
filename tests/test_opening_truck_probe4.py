from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.opening_truck import probe4
from scripts.ringer.transcript_1a.boarding_probe import QuotaExceeded
from storygame.runtime import cloudflare

pytestmark = pytest.mark.usefixtures("provider_opening_story")

COMMANDS = ("head out to the truck", "go to the truck")
ACTION = "- Kristin takes in what she can see and reach from the driver's seat."


@pytest.fixture(autouse=True)
def hermetic_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")

    def fail_urlopen(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("real urlopen reached during probe 4 test")

    monkeypatch.setattr(cloudflare, "urlopen", fail_urlopen)


def _ok_reply() -> dict[str, object]:
    return {
        "status": 200,
        "raw_response": "{}",
        "raw_reply": {},
        "narration": "A reply.",
        "usable": True,
        "error": None,
    }


def test_document_arms_have_committed_prompt_and_exact_action_diff() -> None:
    document = probe4.build_document()

    assert document["totals"] == {"total": 40}
    for command in COMMANDS:
        arm_a = document["requests"][command]["A"]
        arm_b = document["requests"][command]["B"]
        user_a = arm_a["user"]
        user_b = arm_b["user"]
        lines_a = user_a.splitlines()
        assert "- Kristin can reach anything inside Kristin's truck from the driver's seat." in lines_a
        assert "- Already done:" in user_a
        place = "- Kristin. Place: driver's seat."
        assert place in lines_a
        assert f"- {command}" not in lines_a
        assert arm_a["system"] == arm_b["system"]
        assert ACTION in user_b
        assert user_b.index(place) < user_b.index(ACTION) < user_b.index("- Already done:")
        assert document["diffs"][command]["B"]
        assert document["diffs"][command]["A"] == ""


def test_plan_total_and_cap_check_happen_before_a_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    document = probe4.build_document()
    calls: list[object] = []

    def fake_sender(*_args: object, **_kwargs: object) -> dict[str, object]:
        calls.append(True)
        return _ok_reply()

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    monkeypatch.setattr(probe4, "_send_narrator", fake_sender)
    with pytest.raises(probe4.CallCapExceeded, match="40"):
        probe4.run(document, mode="run", max_calls=39, out=tmp_path / "cap.json")
    assert calls == []


def test_billed_modes_without_confirmation_make_zero_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[object] = []
    monkeypatch.setattr(probe4, "_send_narrator", lambda *args, **kwargs: calls.append(True))

    assert probe4.main(["--run", "--out", str(tmp_path / "run.json")]) != 0
    assert probe4.main(["--smoke", "--out", str(tmp_path / "smoke.json")]) != 0
    assert calls == []


def test_placeholder_url_is_refused_without_a_call(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[object] = []
    monkeypatch.setattr(probe4, "_send_narrator", lambda *args, **kwargs: calls.append(True))

    assert probe4.main(["--smoke", "--confirm", "--out", str(tmp_path / "placeholder.json")]) != 0
    assert calls == []


def test_full_run_records_40_rows_in_round_robin_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    document = probe4.build_document()
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    sent: list[tuple[str, str, int]] = []

    def fake_sender(system: str, user: str, url: str, counter: object) -> dict[str, object]:
        assert system
        assert url == "https://worker.example"
        sent.append((user, "", len(sent) + 1))
        counter.before_call()  # type: ignore[attr-defined]
        return _ok_reply()

    monkeypatch.setattr(probe4, "_send_narrator", fake_sender)
    output = tmp_path / "run.json"
    result = probe4.run(document, mode="run", max_calls=48, out=output)

    assert result["calls_made"] == 40
    assert len(result["rows"]) == 40
    assert result["stop_reason"] is None
    assert [(row["command"], row["variant"], row["sample"]) for row in result["rows"][:8]] == [
        ("head out to the truck", "A", 1),
        ("head out to the truck", "B", 1),
        ("go to the truck", "A", 1),
        ("go to the truck", "B", 1),
        ("head out to the truck", "A", 2),
        ("head out to the truck", "B", 2),
        ("go to the truck", "A", 2),
        ("go to the truck", "B", 2),
    ]
    assert all({"command", "variant", "sample", "system", "user", "narration"} <= row.keys() for row in result["rows"])
    assert json.loads(output.read_text())["calls_made"] == 40


def test_429_stops_immediately_and_keeps_partial_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    document = probe4.build_document()
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    calls = 0

    def quota_sender(*args: object, **kwargs: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        args[3].before_call()  # type: ignore[attr-defined]
        if calls == 3:
            raise QuotaExceeded("HTTP_429", "rate limit")
        return _ok_reply()

    monkeypatch.setattr(probe4, "_send_narrator", quota_sender)
    output = tmp_path / "quota.json"
    result = probe4.run(document, mode="run", max_calls=48, out=output)

    assert result["calls_made"] == 3
    assert len(result["rows"]) == 3
    assert result["rows"][-1]["status"] == 429
    assert result["stop_reason"] == "HTTP_429"
    assert json.loads(output.read_text())["calls_made"] == 3


def test_smoke_is_exactly_two_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    document = probe4.build_document()
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    sent: list[tuple[str, str, int]] = []

    def fake_sender(system: str, user: str, url: str, counter: object) -> dict[str, object]:
        sent.append((user, "", len(sent) + 1))
        counter.before_call()  # type: ignore[attr-defined]
        return _ok_reply()

    monkeypatch.setattr(probe4, "_send_narrator", fake_sender)
    result = probe4.run(document, mode="smoke", max_calls=48, out=tmp_path / "smoke.json")

    assert result["calls_made"] == 2
    assert len(result["rows"]) == 2
    assert [(row["command"], row["variant"], row["sample"]) for row in result["rows"]] == [
        ("head out to the truck", "A", 1),
        ("go to the truck", "B", 1),
    ]
