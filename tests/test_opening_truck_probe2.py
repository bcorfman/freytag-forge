from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

import scripts.ringer.opening_truck.probe2 as probe2
from tests.fixtures.opening_truck_probe import recorded_control_request

pytestmark = pytest.mark.usefixtures("provider_opening_story")


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import storygame.runtime.cloudflare as cloudflare

    def fail_urlopen(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("a test attempted a real network call")

    monkeypatch.setattr(cloudflare, "urlopen", fail_urlopen)


@pytest.fixture(autouse=True)
def recorded_boarding_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        probe2,
        "_control_request",
        lambda command: recorded_control_request(probe2, command),
    )


def test_build_document_has_exact_command_arms_and_opening_diff() -> None:
    document = probe2.build_document()
    reach = "- Kristin can reach anything inside Kristin's truck from where she sits."
    opening_lines = {
        "- Kristin is in Michelle's kitchen, just inside the forced back door.",
        "- The workstation stands in the kitchen. Its chair lies overturned beside it.",
        "- Michelle is Kristin's best friend, and Kristin knows this house. It is far too quiet.",
        "- The KMS initials on the drawer are fresh cuts: Kristin's own initials on Michelle's furniture. "
        "Kristin cannot explain them.",
    }

    for command, arms in document["arms"].items():
        control = document["control_requests"][command]["user"]
        arm_one = arms["1"]["user"]
        assert control.count(f"- {command}\n") == 1
        assert arm_one.count(f"- {command}\n") == 0
        arm_one_lines = document["diffs"][command]["arm_1"].splitlines()
        assert [line for line in arm_one_lines if line.startswith("+") and not line.startswith("+++")] == []
        assert [line for line in arm_one_lines if line.startswith("-") and not line.startswith("---")] == [
            f"-- {command}"
        ]

        arm_two = arms["2"]["user"]
        diff_lines = document["diffs"][command]["arm_2"].splitlines()
        assert [line for line in diff_lines if line.startswith("+") and not line.startswith("+++")] == [f"+{reach}"]
        assert arm_two.count(reach) == 1
        assert arm_two.index(reach) > arm_one.index("driver's seat")

    opening = document["opening_request"]["user"]
    opening_o1 = document["opening_arms"]["O1"]["user"]
    assert opening_o1.count("Kristin is in Michelle's kitchen") == 1
    added = [
        line[1:]
        for line in document["diffs"]["opening"]["O1"].splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    assert added == [
        "- Kristin is in Michelle's kitchen, just inside the forced back door.",
        "- The workstation stands in the kitchen. Its chair lies overturned beside it.",
        "- Michelle is Kristin's best friend, and Kristin knows this house. It is far too quiet.",
        "- The KMS initials on the drawer are fresh cuts: Kristin's own initials on Michelle's furniture. "
        "Kristin cannot explain them.",
    ]
    assert all(line in opening_o1 for line in opening_lines)
    assert opening_o1 != opening


def test_plan_totals_and_call_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.test")
    document = probe2.build_document()
    assert document["totals"] == {"part1": 48, "part2": 36, "part3": 10, "total": 94}
    assert len(document["plan"]["part1"]) == 48
    assert len(document["plan"]["part2"]) == 36
    assert len(document["plan"]["part3"]) == 10

    with pytest.raises(probe2.CallCapExceeded, match="94 calls exceeds max-calls 93"):
        probe2.run(document, mode="run", max_calls=93, out=Path("/tmp/probe2-cap.json"))


def test_revised_question_changes_only_registered_fields() -> None:
    command = "head out to the truck"
    vehicle = "Kristin's truck"
    shipped_state, shipped = probe2._shipped_boards_vehicle_payload(command, vehicle)
    revised_state, revised = probe2._revised_boards_vehicle_payload(command, vehicle)
    assert revised_state == shipped_state == {"command": command, "vehicle": vehicle}
    assert set(revised) == set(shipped) == {"boards_vehicle"}
    assert revised["boards_vehicle"]["type"] == shipped["boards_vehicle"]["type"] == "noul"
    assert revised["boards_vehicle"]["instructions"] == (
        "Decide whether the command has the player go to the vehicle in order to get in it. "
        "Going to, going out to, or heading out to a vehicle means the player gets in. "
        "Getting in, climbing in, sitting in, or driving it also counts."
    )
    assert revised["boards_vehicle"]["criteria"] == {
        "true": "The command has the player go to, go out to, head out to, get into, sit in, or drive the vehicle.",
        "false": (
            "The command only looks at, touches, or talks about the vehicle, or only walks up to it "
            "or stands beside it. "
            "It is not boarding if it leaves the vehicle."
        ),
    }
    assert shipped["boards_vehicle"]["instructions"] != revised["boards_vehicle"]["instructions"]
    assert shipped["boards_vehicle"]["criteria"] != revised["boards_vehicle"]["criteria"]


def test_billed_guards_make_no_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    called = False

    def fail_build() -> dict[str, object]:
        nonlocal called
        called = True
        raise AssertionError("billed guard should run before building or calling")

    monkeypatch.setattr(probe2, "build_document", fail_build)
    assert probe2.main(["--run", "--out", str(tmp_path / "run.json")]) != 0
    assert called is False
    assert probe2.main(["--run", "--confirm", "--out", str(tmp_path / "run2.json")]) != 0


def _fake_jev(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[tuple[object, object]],
    *,
    quota_at: int | None = None,
    none_at: int | None = None,
) -> None:
    import storygame.runtime.jev as jev

    class FakeClient:
        def ask(self, state: object, questions: object) -> dict[str, dict[str, float]]:
            calls.append((state, questions))
            if quota_at is not None and len(calls) == quota_at:
                raise HTTPError("https://worker.test", 429, "quota", {}, None)
            if none_at is not None and len(calls) == none_at:
                return {}
            return {"boards_vehicle": {"noul": 1.0}}

    monkeypatch.setattr(jev.JevClient, "from_environment", classmethod(lambda cls: FakeClient()))


def test_full_run_is_94_calls_and_preserves_interleaving(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.test")
    document = probe2.build_document()
    jev_calls: list[tuple[object, object]] = []
    narrator_calls: list[tuple[str, str]] = []
    _fake_jev(monkeypatch, jev_calls, none_at=1)

    def fake_narrator(system: str, user: str, url: str, counter: object) -> dict[str, object]:
        narrator_calls.append((system, user))
        counter.before_call()  # type: ignore[attr-defined]
        return {
            "status": 200,
            "raw_response": "{}",
            "raw_reply": "{}",
            "narration": "ok",
            "usable": True,
            "error": None,
        }

    monkeypatch.setattr(probe2, "_send_narrator", fake_narrator)
    result = probe2.run(document, mode="run", max_calls=105, out=tmp_path / "run.json")

    assert result["calls_made"] == result["planned_calls"] == 94
    assert len(result["rows"]) == 94
    assert len(jev_calls) == 48
    assert len(narrator_calls) == 46
    assert result["rows"][0]["raw_answer"] is None
    assert result["rows"][0]["is_yes"] is None
    assert [(row["arm"], row["phrasing"]) for row in result["rows"][:4]] == [
        ("S", "head out to {v}"),
        ("R", "head out to {v}"),
        ("S", "head out to {v}"),
        ("R", "head out to {v}"),
    ]
    assert result["rows"][48]["part"] == "part2"
    assert result["rows"][48]["command"] == "head out to the truck"
    assert result["rows"][48]["arm"] == 2
    assert result["rows"][-1]["part"] == "part3"


def test_none_answer_and_quota_stop_keep_partial_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.test")
    document = probe2.build_document()
    jev_calls: list[tuple[object, object]] = []
    _fake_jev(monkeypatch, jev_calls, quota_at=2)
    result = probe2.run(document, mode="run", max_calls=105, out=tmp_path / "quota.json")
    assert result["calls_made"] == 2
    assert result["stop_reason"] == "HTTP_429"
    assert len(result["rows"]) == 2
    assert result["rows"][-1]["error"] == "HTTP_429"
    assert json.loads((tmp_path / "quota.json").read_text())["calls_made"] == 2


def test_smoke_is_three_revised_jev_and_two_narrator_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.test")
    document = probe2.build_document()
    jev_calls: list[tuple[object, object]] = []
    narrator_calls: list[tuple[str, str]] = []
    _fake_jev(monkeypatch, jev_calls)

    def fake_narrator(system: str, user: str, url: str, counter: object) -> dict[str, object]:
        narrator_calls.append((system, user))
        counter.before_call()  # type: ignore[attr-defined]
        return {
            "status": 200,
            "raw_response": "{}",
            "raw_reply": "{}",
            "narration": "ok",
            "usable": True,
            "error": None,
        }

    monkeypatch.setattr(probe2, "_send_narrator", fake_narrator)
    result = probe2.run(document, mode="smoke", max_calls=105, out=tmp_path / "smoke.json")
    assert result["calls_made"] == result["planned_calls"] == 5
    assert len(result["rows"]) == 5
    assert [call[0]["command"] for call in jev_calls] == [
        "head out to the truck",
        "go out to the truck",
        "walk up to the truck",
    ]
    assert all("get to the vehicle in order" not in str(call[1]) for call in jev_calls)
    assert len(narrator_calls) == 2
    assert result["rows"][3]["part"] == "part2"
    assert result["rows"][4]["part"] == "part3"
