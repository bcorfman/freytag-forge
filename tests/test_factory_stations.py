import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from factory.checks.carry_matrix import CarryReport, StuckCell
from factory.checks.gap_delta import DEFAULT_ROOT, all_anchors, save_baseline, snapshot
from factory.checks.world_need import check_needs, tickets_for
from factory.line import FactoryLine
from factory.state import FactoryState
from factory.stations import build_handlers
from factory.stations.free_gates import free_gates_handler
from factory.stations.world_need import world_need_handler
from factory.tickets import Station, Ticket, TicketQueue
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
CONTRACT = ROOT / "tests/fixtures/factory_contracts/ok.json"


def make_ticket(payload: dict, *, station: Station = Station.WORLD_NEED, scene: str = "1A") -> Ticket:
    timestamp = NOW.isoformat()
    return Ticket(
        id="ticket",
        scene=scene,
        station=station,
        token_budget=1000,
        created_at=timestamp,
        updated_at=timestamp,
        payload=payload,
    )


def gap_baseline(tmp_path: Path) -> tuple[Path, str]:
    for anchor in all_anchors(DEFAULT_ROOT):
        current = snapshot(DEFAULT_ROOT, [anchor])
        if current.get(anchor):
            path = tmp_path / "gaps.json"
            save_baseline(current, path)
            return path, anchor
    raise AssertionError("expected a gap result in the committed story")


class Runner:
    def __init__(self, results: list[int | BaseException], output: str = "") -> None:
        self.results = list(results)
        self.output = output
        self.calls: list[tuple[list[str], dict]] = []

    def __call__(self, command: list[str], **kwargs):
        self.calls.append((command, kwargs))
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        return subprocess.CompletedProcess(command, result, stdout=self.output, stderr="")


def test_world_need_matches_check_and_filters_to_ticket_scene() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    package = load_story_package(DEFAULT_ROOT)
    results = check_needs(contract, package)
    expected = not tickets_for([result for result in results if result.scene_id == "1A"])

    result = world_need_handler(ROOT)(make_ticket({"contract": str(CONTRACT)}), NOW)

    assert result.passed is expected
    assert result.tokens == 0
    assert "story_hole 1A 1a-need:" in result.output


def test_world_need_bad_need_and_file_errors_are_plain_failures(tmp_path: Path) -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["scenes"][0]["world_needs"][0].update(relation="know", object="unproduced-fact")
    edited = tmp_path / "edited.json"
    edited.write_text(json.dumps(contract), encoding="utf-8")
    handler = world_need_handler(ROOT)

    bad_need = handler(make_ticket({"contract": str(edited)}), NOW)
    missing = handler(make_ticket({"contract": str(tmp_path / "missing.json")}), NOW)
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not json", encoding="utf-8")
    invalid = handler(make_ticket({"contract": str(invalid_path)}), NOW)

    assert not bad_need.passed
    assert "story_hole 1A 1a-need:" in bad_need.output
    assert not missing.passed and "could not read contract" in missing.output
    assert not invalid.passed and "invalid contract JSON" in invalid.output


def test_world_need_missing_contract_key_does_not_raise() -> None:
    result = world_need_handler(ROOT)(make_ticket({}), NOW)

    assert result == result.__class__(False, "world_need", "missing payload key: contract")


def test_free_gates_run_in_order_and_all_pass(tmp_path: Path) -> None:
    baseline, anchor = gap_baseline(tmp_path)
    runner = Runner([0, 0, 0])
    payload = {
        "source_root": str(DEFAULT_ROOT / "source"),
        "gap_baseline": str(baseline),
        "anchors": [anchor],
        "carry_matrix": False,
        "paths": ["factory/line.py", "README.md"],
        "tests": ["tests/test_factory_line.py"],
    }

    result = free_gates_handler(ROOT, runner)(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert result.passed
    assert result.check == "free_gates"
    assert result.output == "all free gates passed"
    assert [call[0][3] for call in runner.calls[:2]] == ["check", "format"]
    assert runner.calls[2][0][0:8] == [".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-n", "0"]
    assert runner.calls[2][1]["timeout"] == 1200


def test_free_gates_stop_at_ruff_failure_and_keep_tail(tmp_path: Path) -> None:
    baseline, anchor = gap_baseline(tmp_path)
    runner = Runner([1], output="x" * 5000)
    payload = {
        "gap_baseline": str(baseline),
        "anchors": [anchor],
        "carry_matrix": False,
        "paths": ["changed.py", "notes.md"],
        "tests": ["tests/test_factory_line.py"],
    }

    result = free_gates_handler(ROOT, runner)(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "ruff"
    assert result.output == "x" * 4000
    assert len(runner.calls) == 1
    assert runner.calls[0][0] == [".venv/bin/python", "-m", "ruff", "check", "changed.py"]


def test_free_gates_filter_non_python_paths_and_timeout_is_failure(tmp_path: Path) -> None:
    baseline, anchor = gap_baseline(tmp_path)
    runner = Runner([subprocess.TimeoutExpired("ruff", 1)])
    payload = {
        "gap_baseline": str(baseline),
        "anchors": [anchor],
        "carry_matrix": False,
        "paths": ["notes.md", "changed.py"],
    }

    result = free_gates_handler(ROOT, runner)(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "ruff"
    assert "timed out" in result.output
    assert len(runner.calls) == 1
    assert runner.calls[0][0][-1] == "changed.py"


def test_free_gates_gap_delta_reports_new_result_and_missing_key(tmp_path: Path) -> None:
    baseline, anchor = gap_baseline(tmp_path)
    data = json.loads(baseline.read_text(encoding="utf-8"))
    data[anchor].pop(0)
    baseline.write_text(json.dumps(data), encoding="utf-8")
    runner = Runner([])

    result = free_gates_handler(ROOT, runner)(
        make_ticket(
            {"gap_baseline": str(baseline), "anchors": [anchor], "carry_matrix": False},
            station=Station.FREE_GATES,
        ),
        NOW,
    )
    missing = free_gates_handler(ROOT, runner)(make_ticket({}, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "gap_delta"
    assert f"NEW {anchor} " in result.output
    assert not missing.passed and missing.check == "gap_delta"
    assert "missing payload key: gap_baseline" in missing.output
    assert runner.calls == []


def test_free_gates_carry_matrix_failure_is_station_check(tmp_path: Path, monkeypatch) -> None:
    baseline, anchor = gap_baseline(tmp_path)
    report = CarryReport(
        mode="one_branch",
        entry_states={"1A": 1},
        branches={"1A": 1},
        searches=1,
        turns=1,
        memo_hits=0,
        cache_hits=0,
        stuck=[],
        seconds=0.01,
        seconds_by_scene={"1A": 0.01},
        unreachable={"2C": "1A"},
    )
    monkeypatch.setattr("factory.stations.free_gates.load_story_package", lambda _root: object())
    monkeypatch.setattr("factory.stations.free_gates.carry_matrix", lambda *args, **kwargs: report)

    result = free_gates_handler(ROOT, Runner([]))(
        make_ticket({"gap_baseline": str(baseline), "anchors": [anchor]}, station=Station.FREE_GATES), NOW
    )

    assert not result.passed
    assert result.check == "carry_matrix"
    assert result.output == report.lines()[0]


def test_free_gates_carry_matrix_tail_keeps_first_stuck_and_every_unreachable(tmp_path: Path, monkeypatch) -> None:
    baseline, anchor = gap_baseline(tmp_path)
    report = CarryReport(
        mode="one_branch",
        entry_states={"3A": 100},
        branches={"3A": 100},
        searches=100,
        turns=100,
        memo_hits=0,
        cache_hits=0,
        stuck=[
            StuckCell("3A", index, (), f"t{index}:candidate", "no_path", 1, ("carried-fact",) * 8)
            for index in range(100)
        ],
        seconds=0.01,
        seconds_by_scene={"3A": 0.01},
        unreachable={"3B": "3A", "3C": "3A"},
    )
    monkeypatch.setattr("factory.stations.free_gates.load_story_package", lambda _root: object())
    monkeypatch.setattr("factory.stations.free_gates.carry_matrix", lambda *args, **kwargs: report)

    result = free_gates_handler(ROOT, Runner([]))(
        make_ticket({"gap_baseline": str(baseline), "anchors": [anchor]}, station=Station.FREE_GATES), NOW
    )

    assert not result.passed
    assert result.output == "\n".join([report.lines()[0], report.lines()[-2], report.lines()[-1]])


def test_build_handlers_and_factory_line_advance(tmp_path: Path) -> None:
    contract = tmp_path / "empty.json"
    contract.write_text(json.dumps({"scenes": []}), encoding="utf-8")
    handlers = build_handlers(ROOT)
    ticket = make_ticket({"contract": str(contract)})
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    state = FactoryState.load(tmp_path / "state.json")
    line = FactoryLine(
        queue=queue,
        state=state,
        handlers=handlers,
        provider_for=lambda ticket: None,
        check_breakers=lambda now: [],
    )

    assert set(handlers) == {Station.WORLD_NEED, Station.FREE_GATES, Station.PROMPT_SNAPSHOT}
    assert line.step(NOW).kind == "advanced"
    assert queue.get("ticket").station is Station.PROSE
