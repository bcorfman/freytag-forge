from __future__ import annotations

import io
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

import storygame.runtime.cloudflare as cloudflare
from scripts.ringer.opening_truck import probe
from storygame.runtime.jev import JevClient


class _Response:
    status = 200

    def __init__(self, body: object) -> None:
        self._body = json.dumps(body).encode()

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> bool:
        return False


def _narrator_response(text: str = "A reply.") -> _Response:
    return _Response({"narration": json.dumps({"segments": [{"kind": "narration", "text": text}]})})


def test_import_has_no_network_side_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[object] = []
    monkeypatch.setattr(cloudflare, "urlopen", lambda *args, **kwargs: calls.append((args, kwargs)))
    assert calls == []


def test_dry_document_has_exact_arm_one_diff_and_control_markers() -> None:
    document = probe.build_document()
    control = document["control_request"]
    arm = document["arm_1"]

    assert arm["system"] == control["system"]
    control_lines = control["user"].splitlines()
    arm_lines = arm["user"].splitlines()
    assert control_lines.count("- head out to the truck") == 1
    assert (
        arm_lines
        == control_lines[: control_lines.index("- head out to the truck")]
        + control_lines[control_lines.index("- head out to the truck") + 1 :]
    )
    assert document["diffs"]["arm_1"].count("\n-") == 1
    assert "- head out to the truck" in document["diffs"]["arm_1"]
    assert "Already done:" in control["user"]
    assert "- head out to the truck" in control["user"]
    assert any("driver's seat" in line for line in control["user"].splitlines() if line.startswith("- "))


def test_plan_totals_and_cap_check(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # The cap check is independent of the billed URL guard.
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    document = probe.build_document()
    assert document["totals"] == {"part1": 40, "part2": 24, "part3": 10, "total": 74}
    with pytest.raises(probe.CallCapExceeded, match="74"):
        probe.run(document, mode="run", max_calls=73, out=tmp_path / "rows.json")


def test_billed_modes_require_confirmation_and_placeholder_is_refused(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    calls: list[object] = []
    monkeypatch.setattr(cloudflare, "urlopen", lambda *args, **kwargs: calls.append(args))

    assert probe.main(["--run", "--out", str(tmp_path / "run.json")]) == 2
    assert probe.main(["--smoke", "--confirm", "--out", str(tmp_path / "smoke.json")]) == 2
    assert calls == []


def test_full_run_records_interleaving_and_none_answer(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    narrator_calls: list[object] = []
    jev_calls: list[tuple[object, object]] = []

    monkeypatch.setattr(
        cloudflare,
        "urlopen",
        lambda request, **kwargs: narrator_calls.append(request) or _narrator_response(),
    )

    def fake_ask(self: JevClient, state: object, questions: object) -> dict | None:
        jev_calls.append((state, questions))
        if len(jev_calls) == 1:
            return None
        return {key: {"noul": 1.0} for key in questions} if isinstance(questions, dict) else None

    monkeypatch.setattr(JevClient, "ask", fake_ask)
    output = tmp_path / "rows.json"
    assert probe.main(["--run", "--confirm", "--out", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["calls_made"] == 74
    assert len(result["rows"]) == 74
    assert result["stop_reason"] is None
    assert len(jev_calls) == 40
    assert len(narrator_calls) == 34
    assert result["rows"][0]["answer"] is None
    assert result["rows"][0]["is_yes"] is None
    assert [row["arm"] for row in result["rows"][40:64]] == [0, 1] * 12
    assert [row["part"] for row in result["rows"]] == ["part1"] * 40 + ["part2"] * 24 + ["part3"] * 10


def test_quota_429_keeps_partial_rows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    calls = 0

    def opener(request: object, **kwargs: object) -> _Response:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise HTTPError(
                getattr(request, "full_url", "https://worker.example/turn"),
                429,
                "quota",
                {},
                io.BytesIO(b'{"code":"AI_QUOTA_EXCEEDED"}'),
            )
        return _narrator_response()

    monkeypatch.setattr(cloudflare, "urlopen", opener)
    monkeypatch.setattr(JevClient, "ask", lambda self, state, questions: {key: {"noul": 1.0} for key in questions})
    output = tmp_path / "rows.json"
    assert probe.main(["--run", "--confirm", "--out", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["calls_made"] == 42
    assert len(result["rows"]) == 42
    assert result["stop_reason"] == "AI_QUOTA_EXCEEDED"
    assert json.loads(output.read_text())["stop_reason"] == "AI_QUOTA_EXCEEDED"


def test_smoke_makes_exactly_five_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    jev_calls: list[object] = []
    narrator_calls: list[object] = []
    monkeypatch.setattr(
        cloudflare,
        "urlopen",
        lambda request, **kwargs: narrator_calls.append(request) or _narrator_response(),
    )
    monkeypatch.setattr(
        JevClient,
        "ask",
        lambda self, state, questions: (
            jev_calls.append((state, questions)) or {key: {"noul": 1.0} for key in questions}
        ),
    )
    output = tmp_path / "smoke.json"
    assert probe.main(["--smoke", "--confirm", "--out", str(output)]) == 0
    result = json.loads(output.read_text())
    assert result["calls_made"] == 5
    assert len(result["rows"]) == 5
    assert len(jev_calls) == 3
    assert len(narrator_calls) == 2
