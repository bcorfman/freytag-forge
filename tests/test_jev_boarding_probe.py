from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import jev_boarding_probe as probe
from storygame.runtime import jev

TOKEN = "jev-probe-secret-token"


class FakeResponse:
    def __init__(self, body: dict, status: int = 200) -> None:
        self.status = status
        self._body = json.dumps(body).encode()

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class FakeOpener:
    def __init__(self, answers_by_command: dict[str, float] | None = None) -> None:
        self.answers_by_command = answers_by_command or {}
        self.requests: list[tuple[object, float]] = []
        self.calls = 0

    def __call__(self, request: object, timeout: float) -> FakeResponse:
        self.calls += 1
        self.requests.append((request, timeout))
        payload = json.loads(request.data)
        command = payload["input"]["state"]["command"]
        value = self.answers_by_command.get(command, 0.0)
        return FakeResponse({"answers": {"boards_vehicle": {"noul": value}}})


@pytest.fixture(autouse=True)
def hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_socket(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network access is forbidden in Jev probe tests")

    monkeypatch.setattr(socket, "socket", fail_socket)
    monkeypatch.setattr("urllib.request.urlopen", fail_socket)
    monkeypatch.setattr(jev, "urlopen", fail_socket)


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _answers() -> dict[str, float]:
    return {command: (1.0 if expected else 0.0) for command, expected in probe.COMMANDS}


def test_dry_plan_has_100_calls_and_50_with_one_sample(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    default_out = tmp_path / "default-plan.json"
    assert probe.main(["--dry", "--out", str(default_out)]) == 0
    default = _read(default_out)
    assert len(default["calls"]) == 100
    assert "100 calls" in capsys.readouterr().out

    one_sample_out = tmp_path / "one-sample-plan.json"
    assert probe.main(["--dry", "--samples", "1", "--out", str(one_sample_out)]) == 0
    one_sample = _read(one_sample_out)
    assert len(one_sample["calls"]) == 50
    assert [(call["command"], call["arm"], call["sample"]) for call in one_sample["calls"][:4]] == [
        (probe.COMMANDS[0][0], "old", 0),
        (probe.COMMANDS[0][0], "current", 0),
        (probe.COMMANDS[1][0], "old", 0),
        (probe.COMMANDS[1][0], "current", 0),
    ]


@pytest.mark.parametrize(
    ("argv", "env", "message"),
    [
        (["--run", "--out", "rows.json", "--confirm"], {}, "CLOUDFLARE_WORKER_URL"),
        (
            ["--run", "--out", "rows.json"],
            {"CLOUDFLARE_WORKER_URL": "https://w.example", "CLOUDFLARE_WORKER_TOKEN": TOKEN},
            "confirm",
        ),
        (
            ["--run", "--out", "rows.json", "--confirm", "--max-calls", "1"],
            {"CLOUDFLARE_WORKER_URL": "https://w.example", "CLOUDFLARE_WORKER_TOKEN": TOKEN},
            "exceed",
        ),
    ],
)
def test_run_guards_before_network(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    env: dict[str, str],
    message: str,
) -> None:
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    args = [str(tmp_path / value) if value == "rows.json" else value for value in argv]
    assert probe.main(args) == 2
    captured = capsys.readouterr()
    assert message.lower() in (captured.out + captured.err).lower()


def test_run_writes_after_each_call_interleaves_and_has_no_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    opener = FakeOpener(_answers())
    client = jev.JevClient("https://w.example", TOKEN, opener=opener)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", TOKEN)
    monkeypatch.setattr(probe.JevClient, "from_environment", classmethod(lambda cls: client))
    out = tmp_path / "rows.json"
    writes: list[int] = []
    write_json = probe._write_json

    def record_write(path: Path, document: dict) -> None:
        writes.append(len(document["rows"]))
        write_json(path, document)

    monkeypatch.setattr(probe, "_write_json", record_write)

    assert probe.main(["--run", "--samples", "1", "--confirm", "--max-calls", "50", "--out", str(out)]) == 0
    document = _read(out)
    rows = document["rows"]
    assert len(rows) == 50
    assert opener.calls == 50
    assert writes == list(range(1, 51))
    assert [(row["command"], row["arm"]) for row in rows[:4]] == [
        (probe.COMMANDS[0][0], "old"),
        (probe.COMMANDS[0][0], "current"),
        (probe.COMMANDS[1][0], "old"),
        (probe.COMMANDS[1][0], "current"),
    ]
    assert all(row["correct"] is True for row in rows)
    assert all(TOKEN not in json.dumps(value) for value in (document, capsys.readouterr().out))


def test_run_stops_after_three_unusable_rows_without_retry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class UnusableOpener(FakeOpener):
        def __call__(self, request: object, timeout: float) -> FakeResponse:
            self.calls += 1
            self.requests.append((request, timeout))
            return FakeResponse({"answers": {}})

    opener = UnusableOpener()
    client = jev.JevClient("https://w.example", TOKEN, opener=opener)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", TOKEN)
    monkeypatch.setattr(probe.JevClient, "from_environment", classmethod(lambda cls: client))
    out = tmp_path / "rows.json"

    assert probe.main(["--run", "--samples", "1", "--confirm", "--max-calls", "50", "--out", str(out)]) == 0
    document = _read(out)
    assert len(document["rows"]) == 3
    assert opener.calls == 3
    assert document["stop_reason"] == "three_consecutive_unusable"
    assert all(row["correct"] is None for row in document["rows"])


def test_report_lists_every_row_commands_and_wrong_or_unusable_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows_path = tmp_path / "rows.json"
    rows = [
        {
            "call_index": 1,
            "arm": "old",
            "command": "Go to my truck.",
            "expected": True,
            "sample": 0,
            "raw_noul": 0.0,
            "predicted": False,
            "correct": False,
            "latency_ms": 3.0,
        },
        {
            "call_index": 2,
            "arm": "current",
            "command": "Go to my truck.",
            "expected": True,
            "sample": 0,
            "raw_noul": None,
            "predicted": None,
            "correct": None,
            "latency_ms": 5.0,
        },
    ]
    rows_path.write_text(json.dumps({"rows": rows, "stop_reason": "three_consecutive_unusable"}), encoding="utf-8")
    report = tmp_path / "report.md"

    assert probe.main(["--report", "--rows", str(rows_path), "--out", str(report)]) == 0
    text = report.read_text(encoding="utf-8")
    assert "old: 0 / 1" in text
    assert "current: 0 / 1" in text
    assert "Expected True accuracy" in text
    assert "Expected False accuracy" in text
    assert "Go to my truck." in text
    assert "Wrong or unusable rows" in text
    assert "Call 1" in text and "Call 2" in text
    assert TOKEN not in text
    assert TOKEN not in capsys.readouterr().out


def test_jev_client_fake_opener_is_hermetic_and_has_no_retry() -> None:
    opener = FakeOpener({"Go to my truck.": 1.0})
    client = jev.JevClient("https://w.example", TOKEN, opener=opener)
    assert client.ask({"command": "Go to my truck.", "vehicle": "Kristin's truck"}, probe.OLD_QUESTION)
    assert client.request_count == 1
    assert opener.calls == 1
