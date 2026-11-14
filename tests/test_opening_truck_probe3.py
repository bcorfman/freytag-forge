from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.opening_truck import probe2, probe3
from scripts.ringer.transcript_1a.boarding_probe import QuotaExceeded
from storygame.runtime import cloudflare
from tests.fixtures.opening_truck_probe import recorded_control_request

pytestmark = pytest.mark.usefixtures("provider_opening_story")


@pytest.fixture(autouse=True)
def hermetic_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")

    def fail_urlopen(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("real urlopen reached during probe 3 test")

    monkeypatch.setattr(cloudflare, "urlopen", fail_urlopen)


@pytest.fixture(autouse=True)
def recorded_boarding_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        probe3,
        "_control_request",
        lambda command: recorded_control_request(probe2, command),
    )


def test_document_arms_and_plan_are_preregistered() -> None:
    document = probe3.build_document()

    assert document["totals"] == {"q1": 40, "q2": 20, "q3": 10, "total": 70}
    assert len(document["plan"]["q1"]) == 40
    assert len(document["plan"]["q2"]) == 20
    assert len(document["plan"]["q3"]) == 10

    expected_q1_lines = {
        "q1_arm3": "- Kristin looks around from the driver's seat.",
        "q1_arm4": "- Kristin takes in what she can see and reach from the driver's seat.",
    }
    for command, arms in document["q1_arms"].items():
        control = document["q1_controls"][command]["user"]
        assert f"- {command}" in control
        for variant, line in expected_q1_lines.items():
            user = arms[variant]["user"]
            assert line in user
            assert user.count(line) == 1
            assert "- Kristin. Place: driver's seat." in user
            assert "- Already done:" in user
            assert user.index("- Kristin. Place: driver's seat.") < user.index(line)
            assert user.index(line) < user.index("- Already done:")
            assert document["diffs"]["q1"][command][variant]

    q2_control = document["q2_control"]
    assert "- go out to the truck" in q2_control["user"]
    assert "Already done:" not in q2_control["user"]
    assert not any(line.startswith("- Kristin's truck. Place") for line in q2_control["user"].splitlines())
    assert "- Kristin's truck. Place: outside the house." in document["q2_t1"]["user"]

    opening = document["q3_arms"]["q3_o2"]["user"]
    additions = [
        "- Kristin has already stepped inside and stands in Michelle's kitchen, beside the forced back door.",
        "- The workstation is across the kitchen from the back door. Its chair lies on its side in front of it.",
        "- Michelle's phone lies on the kitchen floor.",
        "- The KMS cuts in the drawer front are pale and clean. They are Kristin's own initials, "
        "carved into Michelle's workstation.",
    ]
    assert all(opening.count(line) == 1 for line in additions)
    assert all(opening.index(line) > opening.index("- Kristin Schweitzer's objective is") for line in additions)


def test_cap_and_billed_guards_happen_without_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[object] = []

    def fake_sender(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append((args, kwargs))
        return {"status": 200, "raw_response": "{}", "raw_reply": {}, "narration": "ok", "usable": True, "error": None}

    monkeypatch.setattr(probe3, "_send_narrator", fake_sender)
    assert probe3.main(["--run", "--out", str(tmp_path / "no-confirm.json")]) != 0
    assert calls == []

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", probe3.WORKER_PLACEHOLDER)
    assert probe3.main(["--smoke", "--confirm", "--out", str(tmp_path / "placeholder.json")]) != 0
    assert calls == []

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    document = probe3.build_document()
    with pytest.raises(probe3.CallCapExceeded):
        probe3.run(document, mode="run", max_calls=69, out=tmp_path / "cap.json")
    assert calls == []


def test_full_run_is_round_robin_and_records_70_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    document = probe3.build_document()
    calls: list[tuple[str, str]] = []

    def fake_sender(system: str, user: str, url: str, counter: object) -> dict[str, object]:
        assert url == "https://worker.example"
        calls.append((system, user))
        counter.before_call()  # type: ignore[attr-defined]
        return {"status": 200, "raw_response": "{}", "raw_reply": {}, "narration": "ok", "usable": True, "error": None}

    monkeypatch.setattr(probe3, "_send_narrator", fake_sender)
    result = probe3.run(document, mode="run", max_calls=80, out=tmp_path / "run.json")

    assert result["calls_made"] == 70
    assert len(result["rows"]) == 70
    assert result["stop_reason"] is None
    assert [(row["variant"], row["command"], row["sample"]) for row in result["rows"][:8]] == [
        ("q1_arm3", "head out to the truck", 1),
        ("q1_arm4", "head out to the truck", 1),
        ("q1_arm3", "go to the truck", 1),
        ("q1_arm4", "go to the truck", 1),
        ("q1_arm3", "head out to the truck", 2),
        ("q1_arm4", "head out to the truck", 2),
        ("q1_arm3", "go to the truck", 2),
        ("q1_arm4", "go to the truck", 2),
    ]
    assert [row["variant"] for row in result["rows"][40:44]] == ["q2_control", "q2_t1", "q2_control", "q2_t1"]
    assert all(
        {"part", "question", "variant", "command", "sample", "system", "user", "narration"} <= row.keys()
        for row in result["rows"]
    )
    saved = json.loads((tmp_path / "run.json").read_text())
    assert saved["calls_made"] == 70


def test_quota_keeps_partial_rows_and_smoke_is_five_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example")
    document = probe3.build_document()
    calls = 0
    quota_enabled = True

    def quota_sender(*_args: object) -> dict[str, object]:
        nonlocal calls
        calls += 1
        counter = _args[3]
        counter.before_call()  # type: ignore[attr-defined]
        if quota_enabled and calls == 3:
            raise QuotaExceeded("HTTP_429", "rate limit")
        return {"status": 200, "raw_response": "{}", "raw_reply": {}, "narration": "ok", "usable": True, "error": None}

    monkeypatch.setattr(probe3, "_send_narrator", quota_sender)
    result = probe3.run(document, mode="run", max_calls=80, out=tmp_path / "quota.json")
    assert result["calls_made"] == 3
    assert len(result["rows"]) == 3
    assert result["stop_reason"] == "HTTP_429"
    assert result["rows"][-1]["status"] == 429

    calls = 0
    quota_enabled = False
    result = probe3.run(document, mode="smoke", max_calls=80, out=tmp_path / "smoke.json")
    assert result["calls_made"] == 5
    assert len(result["rows"]) == 5
    assert [(row["variant"], row["command"]) for row in result["rows"]] == [
        ("q1_arm3", "head out to the truck"),
        ("q1_arm4", "go to the truck"),
        ("q2_control", "go out to the truck"),
        ("q2_t1", "go out to the truck"),
        ("q3_o2", None),
    ]
