import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import factory.preflight as preflight_module
from factory.__main__ import main
from factory.guard import SpendLedger, Usage
from factory.limits import LimitReport, Window
from factory.line import FactoryLine, StationResult
from factory.state import FactoryState
from factory.tickets import Station, Status, Ticket, TicketQueue
from tests.test_factory_preflight import make_config, successful_command

NOW = datetime(2026, 11, 16, 12, tzinfo=UTC)


def test_preflight_writes_and_removes_marker(tmp_path, monkeypatch, capsys):
    config = make_config(tmp_path)
    monkeypatch.setattr(preflight_module, "changed_paths", lambda root, base: [])
    args = ["--root", str(tmp_path), "--config", str(config), "preflight"]

    assert main(args, run_command=successful_command) == 0
    marker = tmp_path / "factory/state/preflight.ok"
    assert marker.exists()

    data = json.loads(config.read_text(encoding="utf-8"))
    data["caps"]["total_budget_usd"] = 0.0
    config.write_text(json.dumps(data), encoding="utf-8")
    assert main(args, run_command=successful_command) == 1
    assert not marker.exists()
    assert "FAIL caps_set" in capsys.readouterr().out


def test_status_reports_empty_state_and_breaker(tmp_path, capsys):
    config = make_config(tmp_path)
    args = ["--root", str(tmp_path), "--config", str(config), "status"]

    assert main(args, now_fn=lambda: NOW) == 0
    output = capsys.readouterr().out
    assert "queued: 0" in output
    assert "sleeping lanes: none" in output
    assert "breaker: clear" in output
    assert "total spend: 0.000000 USD" in output
    assert "estimate vs actual" not in output

    from factory.state import FactoryState

    state = FactoryState.load(tmp_path / "factory/state/state.json")
    state.trip_breaker("test breaker", NOW)
    assert main(args, now_fn=lambda: NOW) == 0
    assert "breaker: tripped (test breaker)" in capsys.readouterr().out


def test_wake_clears_lane_and_makes_provider_tickets_ready(tmp_path, capsys):
    config = make_config(tmp_path)
    state = FactoryState.load(tmp_path / "factory/state/state.json")
    state.sleep_lane("codex", NOW + datetime.resolution, since=NOW - datetime.resolution)
    queue = TicketQueue(tmp_path / "factory/state/tickets")
    ticket = Ticket("sleeping", "scene", Station.PROSE, 100, NOW.isoformat(), NOW.isoformat())
    ticket.status = Status.SLEEPING
    ticket.provider = "codex"
    ticket.sleep_until = (NOW + datetime.resolution).isoformat()
    queue.add(ticket)

    args = ["--root", str(tmp_path), "--config", str(config), "wake", "codex"]
    assert main(args, now_fn=lambda: NOW) == 0
    assert "codex: lane cleared, 1 ticket(s) ready" in capsys.readouterr().out
    assert state.load(tmp_path / "factory/state/state.json").limited_since == {
        "codex": (NOW - datetime.resolution).isoformat()
    }
    assert queue.get("sleeping").sleep_until == NOW.isoformat()

    called = []
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "factory/state/state.json"),
        handlers={Station.PROSE: lambda ticket, now: called.append(ticket.id) or StationResult(True, "ok", "ok")},
        provider_for=lambda ticket: ticket.provider,
        check_breakers=lambda now: [],
    )
    assert line.step(NOW).kind == "advanced"
    assert called == ["sleeping"]


def test_wake_reports_non_sleeping_lane(tmp_path, capsys):
    config = make_config(tmp_path)

    assert main(["--root", str(tmp_path), "--config", str(config), "wake", "codex"], now_fn=lambda: NOW) == 0
    assert "codex: lane was not sleeping, 0 ticket(s) ready" in capsys.readouterr().out


def test_status_reports_unknown_minimum_limits_and_limited_since(tmp_path, capsys):
    config = make_config(tmp_path)
    state = FactoryState.load(tmp_path / "factory/state/state.json")
    state.sleep_lane("codex", NOW + datetime.resolution, since=NOW - timedelta(hours=2))
    ledger = SpendLedger(tmp_path / "factory/state/ledger.jsonl")
    ledger.record(Usage(NOW, "codex", "model", "station", "scene", "unknown", 1, None, cost_kind="unknown"))
    ledger.record(
        Usage(
            NOW,
            "codex",
            "model",
            "station",
            "scene",
            "limits",
            1,
            None,
            cost_kind="subscription",
            limits=LimitReport(
                "codex",
                (Window("seven_day", 0.06, None, False), Window("five_hour", 0.19, None, False)),
                None,
                10.0,
            ),
        )
    )

    assert main(["--root", str(tmp_path), "--config", str(config), "status"], now_fn=lambda: NOW) == 0
    output = capsys.readouterr().out
    assert "total spend: 0.000000 USD (a minimum: 1 calls of unknown cost)" in output
    assert "codex windows: five_hour 19%, seven_day 6%" in output
    assert f"codex limited since {(NOW - timedelta(hours=2)).isoformat()}" in output


def test_status_reports_estimate_vs_actual_when_available(tmp_path, capsys):
    config = make_config(tmp_path)
    ledger = SpendLedger(tmp_path / "factory/state/ledger.jsonl")
    ledger.record(Usage(NOW, "cloudflare", "model", "probe", "scene", "ticket", 1, 0.5, estimate_usd=0.25))

    assert main(["--root", str(tmp_path), "--config", str(config), "status"], now_fn=lambda: NOW) == 0
    output = capsys.readouterr().out
    assert "estimate vs actual probe: estimated 0.250000 USD, actual 0.500000 USD, ratio 2.00 over 1 call(s)" in output


def test_run_refusals_and_one_passing_ticket(tmp_path, monkeypatch, capsys):
    config = make_config(tmp_path)
    base_args = ["--root", str(tmp_path), "--config", str(config)]
    assert main([*base_args, "run"], now_fn=lambda: NOW) == 2
    assert "preflight required" in capsys.readouterr().out

    monkeypatch.setattr(preflight_module, "changed_paths", lambda root, base: [])
    assert main([*base_args, "preflight"], run_command=successful_command) == 0
    assert main([*base_args, "run"], now_fn=lambda: NOW) == 2
    assert "no station handlers wired" in capsys.readouterr().out

    handlers_module = tmp_path / "tiny_handlers.py"
    handlers_module.write_text(
        "from factory.line import StationResult\n"
        "from factory.tickets import Station\n"
        "def handlers():\n"
        "    return {Station.DELIVER: lambda ticket, now: StationResult(True, 'test', 'ok')}\n",
        encoding="utf-8",
    )
    sys.path.insert(0, str(tmp_path))
    try:
        queue = TicketQueue(tmp_path / "factory/state/tickets")
        queue.add(Ticket("tiny", "scene", Station.DELIVER, 100, NOW.isoformat(), NOW.isoformat()))
        assert main([*base_args, "run", "--handlers", "tiny_handlers:handlers"], now_fn=lambda: NOW) == 0
    finally:
        sys.path.remove(str(tmp_path))
    assert queue.get("tiny").status.value == "passed"
    assert "run completed" in capsys.readouterr().out


def test_run_refuses_tripped_breaker(tmp_path, monkeypatch, capsys):
    config = make_config(tmp_path)
    args = ["--root", str(tmp_path), "--config", str(config)]
    monkeypatch.setattr(preflight_module, "changed_paths", lambda root, base: [])
    assert main([*args, "preflight"], run_command=successful_command) == 0
    from factory.state import FactoryState

    state = FactoryState.load(tmp_path / "factory/state/state.json")
    state.trip_breaker("already stopped", NOW)
    assert main([*args, "run", "--handlers", "missing:handlers"], now_fn=lambda: NOW) == 2
    assert "breaker already tripped" in capsys.readouterr().out


class DrillResult:
    def __init__(self, name: str, passed: bool, detail: str):
        self.name = name
        self.passed = passed
        self.detail = detail


def test_drill_uses_injected_function_without_importing_drill(tmp_path, capsys):
    seen = {}

    def passing(workdir: Path, now: datetime):
        seen["workdir"] = workdir
        seen["now"] = now
        return [DrillResult("tiny", True, "ok")]

    assert main(["--root", str(tmp_path), "drill"], now_fn=lambda: NOW, drill_fn=passing) == 0
    assert seen["workdir"] != tmp_path
    assert not seen["workdir"].exists()
    assert seen["now"] == NOW
    assert "PASS tiny: ok" in capsys.readouterr().out

    def failing(workdir: Path, now: datetime):
        return [DrillResult("tiny", False, "bad")]

    assert main(["--root", str(tmp_path), "drill"], now_fn=lambda: NOW, drill_fn=failing) == 1
    assert "FAIL tiny: bad" in capsys.readouterr().out
