from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import screen


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden in environment screen tests")

    monkeypatch.setattr(socket, "socket", fail_socket)


def _invoke(tmp_path: Path, *args: str) -> tuple[int, dict | None, str, str]:
    out = tmp_path / "out.json"
    captured = screen.main([*args, "--out", str(out)])
    document = json.loads(out.read_text(encoding="utf-8")) if out.exists() and out.suffix == ".json" else None
    return captured, document, out.read_text(encoding="utf-8") if out.exists() else "", str(out)


def _dry(tmp_path: Path, *, samples: int = 2) -> dict:
    status, document, _text, _path = _invoke(tmp_path, "--dry", "--samples", str(samples))
    assert status == 0
    assert document is not None
    return document


def _contexts(document: dict, start_id: str) -> dict:
    start = next(item for item in document["starts"] if item["id"] == start_id)
    return start["contexts"]


def test_dry_document_freezes_the_six_start_matrix_and_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    assert screen.main(["--dry", "--samples", "2", "--out", str(first)]) == 0
    assert screen.main(["--dry", "--samples", "2", "--out", str(second)]) == 0
    assert first.read_bytes() == second.read_bytes()

    document = json.loads(first.read_text(encoding="utf-8"))
    assert len(document["starts"]) == 6
    assert {item["id"] for item in document["starts"]} == {f"S{i}" for i in range(1, 7)}
    assert document["cells"] == 36
    assert document["cost"]["calls"] == 36 * 2

    for start in document["starts"]:
        existing = start["contexts"]["existing"]
        proposed = start["contexts"]["proposed"]
        assert existing["system"] == proposed["system"]
        assert existing["package_hash"]
        assert proposed["package_hash"]
        assert existing["request"]["kind"] == proposed["request"]["kind"]
        assert existing["request"]["focus"] == proposed["request"]["focus"]

    s1 = _contexts(document, "S1")
    assert "Show these in your reply: Kristin's laptop" in s1["proposed"]["user"]
    assert "Just before this:" in s1["existing"]["user"]

    s2 = _contexts(document, "S2")
    assert "Kristin's laptop" in s2["proposed"]["user"].split("CONSTRAINTS:", 1)[0]
    assert "Kristin's laptop" not in s2["existing"]["user"].split("CONSTRAINTS:", 1)[0]

    s3 = _contexts(document, "S3")
    assert "Kristin's laptop. Held by: Kristin." in s3["existing"]["user"]
    assert "Kristin's laptop. Held by: Kristin." in s3["proposed"]["user"]

    s5 = _contexts(document, "S5")
    assert "Nothing is left in or under the drawer. Searching the drawer finds nothing." in s5["proposed"]["user"]
    assert "Nothing is left in or under the drawer. Searching the drawer finds nothing." not in s5["existing"]["user"]

    s6 = _contexts(document, "S6")
    assert "Kristin's truck" not in s6["proposed"]["user"]


def test_dry_cost_is_the_sum_of_per_call_ceilings(tmp_path: Path) -> None:
    document = _dry(tmp_path, samples=3)
    cost = document["cost"]
    assert cost["calls"] == 108
    assert cost["ceiling_usd"] > 0
    assert cost["ceiling_usd"] == sum(cell["ceiling_usd"] for cell in cost["per_cell"] for _ in range(3))
    assert cost["smoke"]["calls"] == 6
    assert cost["smoke"]["ceiling_usd"] > 0


def test_live_guards_refuse_without_confirmation_url_call_cap_or_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out = tmp_path / "rows.json"
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    assert screen.main(["--smoke", "--out", str(out)]) != 0

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    assert screen.main(["--smoke", "--out", str(out)]) != 0
    assert screen.main(["--smoke", "--confirm", "--max-calls", "0", "--out", str(out)]) != 0
    assert screen.main(["--run", "--samples", "1", "--confirm", "--max-calls", "36", "--out", str(out)]) != 0
    opener = _FakeOpener([])
    monkeypatch.setattr(screen, "urlopen", opener)
    assert screen.main(["--run", "--samples", "1", "--confirm", "--max-usd", "0", "--out", str(out)]) != 0
    assert not opener.requests


class _FakeResponse:
    def __init__(self, status: int, body: object, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self._body = json.dumps(body).encode()
        self.headers = headers or {}

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _FakeOpener:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self.responses = responses
        self.requests: list[object] = []

    def __call__(self, request: object, timeout: float) -> _FakeResponse:
        self.requests.append((request, timeout))
        if not self.responses:
            raise AssertionError("fake opener was called after the run should have stopped")
        return self.responses.pop(0)


def _success(model: str, *, narration: str = "A test narration.") -> _FakeResponse:
    return _FakeResponse(200, {"model": model, "narration": narration}, {"X-Worker-Revision": "test-rev"})


def test_fake_transport_sends_model_interleaves_and_stops_on_quota(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    opener = _FakeOpener(
        [_success(screen.MODELS[index % 3]) for index in range(3)] + [_FakeResponse(429, "AI_QUOTA_EXCEEDED")]
    )
    monkeypatch.setattr(screen, "urlopen", opener)
    out = tmp_path / "rows.json"
    writes: list[int] = []
    original_write = screen._write_json

    def observe_write(path: Path, value: object) -> None:
        original_write(path, value)
        if path == out and isinstance(value, dict):
            writes.append(len(value.get("rows", [])))

    monkeypatch.setattr(screen, "_write_json", observe_write)

    assert screen.main(["--smoke", "--confirm", "--out", str(out)]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert len(result["rows"]) == 4
    assert result["stop_reason"] == "AI_QUOTA_EXCEEDED"
    assert len(opener.requests) == 4
    assert writes[-4:] == [1, 2, 3, 4]
    requests = [request for request, _timeout in opener.requests]
    assert [request.get_header("X-bench-model") for request in requests[:3]] == list(screen.MODELS)
    assert [(row["start"], row["context"]) for row in result["rows"][:4]] == [
        ("S1", "existing"),
        ("S1", "existing"),
        ("S1", "existing"),
        ("S1", "proposed"),
    ]
    assert result["rows"][3]["status"] == 429


def test_fake_transport_stops_on_rejection_and_echo_mismatch_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    opener = _FakeOpener([_FakeResponse(400, {"code": "BENCH_MODEL_REJECTED"})])
    monkeypatch.setattr(screen, "urlopen", opener)
    rejected = tmp_path / "rejected.json"
    assert screen.main(["--smoke", "--confirm", "--out", str(rejected)]) == 0
    result = json.loads(rejected.read_text(encoding="utf-8"))
    assert len(result["rows"]) == 1
    assert result["stop_reason"] == "BENCH_MODEL_REJECTED"
    assert result["invalid"] is True

    mismatch_opener = _FakeOpener([_success(screen.MODELS[1])])
    monkeypatch.setattr(screen, "urlopen", mismatch_opener)
    mismatch = tmp_path / "mismatch.json"
    assert screen.main(["--smoke", "--confirm", "--out", str(mismatch)]) == 0
    mismatch_result = json.loads(mismatch.read_text(encoding="utf-8"))
    assert len(mismatch_result["rows"]) == 1
    assert mismatch_result["invalid"] is True
    assert mismatch_result["stop_reason"] == "MODEL_ECHO_MISMATCH"
    assert len(mismatch_opener.requests) == 1


def test_failed_worker_call_is_recorded_once_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    responses = [_FakeResponse(500, {"error": "temporary failure"})]
    responses.extend(_success(screen.MODELS[(index + 1) % 3]) for index in range(5))
    opener = _FakeOpener(responses)
    monkeypatch.setattr(screen, "urlopen", opener)
    out = tmp_path / "rows.json"

    assert screen.main(["--smoke", "--confirm", "--out", str(out)]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert len(opener.requests) == 6
    assert result["rows"][0]["status"] == 500
    assert result["rows"][0]["usable"] is False


def test_report_renders_success_and_failure_rows(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rows = tmp_path / "rows.json"
    rows.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "start": "S1",
                        "context": "existing",
                        "model": screen.MODELS[0],
                        "sample": 0,
                        "status": 200,
                        "latency_ms": 12,
                        "usable": True,
                        "narration": "The laptop is on the passenger seat.",
                        "raw_response": "{}",
                    },
                    {
                        "start": "S1",
                        "context": "proposed",
                        "model": screen.MODELS[0],
                        "sample": 0,
                        "status": 500,
                        "latency_ms": 4,
                        "usable": False,
                        "narration": None,
                        "raw_response": "worker failure",
                    },
                ],
                "starts": [
                    {
                        "id": "S1",
                        "label": "boarding",
                        "expected_observations": {"required": ["Kristin's laptop"], "forbidden": ["driving"]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = tmp_path / "report.md"
    assert screen.main(["--report", "--rows", str(rows), "--out", str(report)]) == 0
    text = report.read_text(encoding="utf-8")
    assert "The laptop is on the passenger seat." in text
    assert "worker failure" in text
    assert "usable" in text and "unusable" in text
    assert "Kristin's laptop" in text
    assert "driving" in text
    assert "#### @cf/meta/llama-3.1-8b-instruct-fast — sample 0" in text
    assert text.count("#### @cf/meta/llama-3.1-8b-instruct-fast — sample 0") == 2
    assert "report:" in capsys.readouterr().out
