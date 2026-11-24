import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from factory.checks.carry_matrix import CarryReport, StuckCell
from factory.checks.gap_delta import DEFAULT_ROOT, all_anchors, save_baseline, snapshot
from factory.checks.world_need import check_needs, tickets_for
from factory.line import FactoryLine
from factory.state import FactoryState
from factory.stations import build_handlers
from factory.stations import free_gates as free_gates_module
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


def stale_story_copy(tmp_path: Path) -> tuple[Path, Path, dict[Path, bytes]]:
    tree = tmp_path / "tree"
    tree.mkdir()
    story_root = tree / DEFAULT_ROOT.relative_to(ROOT)
    shutil.copytree(DEFAULT_ROOT, story_root)
    source_file = next(story_root.rglob("*.yaml"))
    source_file.write_bytes(source_file.read_bytes() + b"#")
    before = {path.relative_to(tree): path.read_bytes() for path in tree.rglob("*") if path.is_file()}
    return tree, story_root, before


def noncanonical_story_copy(tmp_path: Path) -> tuple[Path, Path, Path, dict[Path, bytes]]:
    tree = tmp_path / "tree"
    tree.mkdir()
    story_root = tree / DEFAULT_ROOT.relative_to(ROOT)
    shutil.copytree(DEFAULT_ROOT, story_root)
    source_file = story_root / "source" / "scenes" / "1A.yaml"
    text = source_file.read_text(encoding="utf-8")
    lines = text.replace("schema: 1\n", "schema: 1\n# inserted comment\n", 1).splitlines(keepends=True)
    in_participants = False
    for index, line in enumerate(lines):
        if line == "participants:\n":
            in_participants = True
        elif in_participants and line.startswith("- "):
            lines[index] = f"  {line}"
        elif in_participants:
            in_participants = False
    source_file.write_text("".join(lines), encoding="utf-8")
    before = {path.relative_to(tree): path.read_bytes() for path in tree.rglob("*") if path.is_file()}
    return tree, story_root, source_file, before


def stub_gap_delta(monkeypatch, baseline: Path) -> dict[str, object]:
    baseline.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(free_gates_module, "snapshot", lambda root, anchors=None: {})
    monkeypatch.setattr(free_gates_module, "load_baseline", lambda path: {})
    monkeypatch.setattr(free_gates_module, "new_results", lambda baseline, current: {})
    return {"gap_baseline": str(baseline), "carry_matrix": False}


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
        "entry_snapshots": False,
        "story_format": False,
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
        "entry_snapshots": False,
        "story_format": False,
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
        "entry_snapshots": False,
        "story_format": False,
        "paths": ["notes.md", "changed.py"],
    }

    result = free_gates_handler(ROOT, runner)(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "ruff"
    assert "timed out" in result.output
    assert len(runner.calls) == 1
    assert runner.calls[0][0][-1] == "changed.py"


def test_free_gates_uses_ticket_tree_for_paths_and_commands(tmp_path: Path, monkeypatch) -> None:
    tree = tmp_path / "tree"
    tree.mkdir()
    baseline = tmp_path / "gaps.json"
    baseline.write_text("{}", encoding="utf-8")
    runner = Runner([0, 0, 0])
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: tree)
    monkeypatch.setattr(free_gates_module, "snapshot", lambda root, anchors=None: {})
    monkeypatch.setattr(free_gates_module, "load_baseline", lambda path: {})

    result = free_gates_handler(ROOT, runner)(
        make_ticket(
            {
                "gap_baseline": str(baseline),
                "story_root": "data/stories/continuity-initiative",
                "carry_matrix": False,
                "entry_snapshots": False,
                "story_format": False,
                "paths": [str(ROOT / "factory/line.py")],
                "tests": [str(ROOT / "tests/test_factory_line.py")],
            },
            station=Station.FREE_GATES,
        ),
        NOW,
    )

    assert result.passed
    assert all(kwargs["cwd"] == tree for _, kwargs in runner.calls)
    assert runner.calls[-1][0][-1] == "tests/test_factory_line.py"
    assert str(tree) in runner.calls[-1][1]["env"]["PYTHONPATH"].split(":")


def test_free_gates_gap_delta_reports_new_result_and_missing_key(tmp_path: Path) -> None:
    baseline, anchor = gap_baseline(tmp_path)
    data = json.loads(baseline.read_text(encoding="utf-8"))
    data[anchor].pop(0)
    baseline.write_text(json.dumps(data), encoding="utf-8")
    runner = Runner([])

    result = free_gates_handler(ROOT, runner)(
        make_ticket(
            {
                "gap_baseline": str(baseline),
                "anchors": [anchor],
                "carry_matrix": False,
                "entry_snapshots": False,
                "story_format": False,
            },
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
        make_ticket(
            {
                "gap_baseline": str(baseline),
                "anchors": [anchor],
                "entry_snapshots": False,
                "story_format": False,
            },
            station=Station.FREE_GATES,
        ),
        NOW,
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
        make_ticket(
            {
                "gap_baseline": str(baseline),
                "anchors": [anchor],
                "entry_snapshots": False,
                "story_format": False,
            },
            station=Station.FREE_GATES,
        ),
        NOW,
    )

    assert not result.passed
    assert result.output == "\n".join([report.lines()[0], report.lines()[-2], report.lines()[-1]])


def test_free_gates_refreshes_entry_snapshots_only_in_ticket_tree(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, _ = stale_story_copy(tmp_path)
    original_entry = {
        path.relative_to(DEFAULT_ROOT): path.read_bytes() for path in (DEFAULT_ROOT / "entry").glob("*.json")
    }
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload["story_root"] = str(DEFAULT_ROOT)
    payload["story_format"] = False
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: tree)

    result = free_gates_handler(ROOT, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert result == result.__class__(True, "free_gates", "all free gates passed")
    fingerprints = {
        json.loads(path.read_text(encoding="utf-8"))["source_fingerprint"]
        for path in (story_root / "entry").glob("*.json")
    }
    assert len(fingerprints) == 1
    assert fingerprints != {json.loads(data.decode("utf-8"))["source_fingerprint"] for data in original_entry.values()}
    assert free_gates_module.check_entry_snapshots(story_root) == []
    assert {
        path.relative_to(DEFAULT_ROOT): path.read_bytes() for path in (DEFAULT_ROOT / "entry").glob("*.json")
    } == original_entry


def test_free_gates_checks_but_does_not_write_without_ticket_tree(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, before = stale_story_copy(tmp_path)
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload["story_root"] = str(story_root.relative_to(tree))
    payload["story_format"] = False
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: None)

    result = free_gates_handler(tree, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "entry_snapshots"
    assert "stale fingerprint for scene" in result.output
    assert {path.relative_to(tree): path.read_bytes() for path in tree.rglob("*") if path.is_file()} == before


def test_free_gates_reports_entry_snapshot_check_problems(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, _ = stale_story_copy(tmp_path)
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload["story_root"] = str(story_root.relative_to(tree))
    payload["story_format"] = False
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: None)
    problem = "carry-in gate problem: scene 2C fact clue consumer gate is not supplied"
    monkeypatch.setattr(free_gates_module, "check_entry_snapshots", lambda root: [problem])

    result = free_gates_handler(tree, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "entry_snapshots"
    assert result.output == problem


def test_free_gates_can_skip_entry_snapshot_check(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, _ = stale_story_copy(tmp_path)
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload.update({"story_root": str(story_root.relative_to(tree)), "entry_snapshots": False, "story_format": False})
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: None)
    calls: list[Path] = []
    monkeypatch.setattr(free_gates_module, "check_entry_snapshots", lambda root: calls.append(root) or [])

    result = free_gates_handler(tree, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert result == result.__class__(True, "free_gates", "all free gates passed")
    assert calls == []


def test_free_gates_formats_ticket_tree_before_refreshing_snapshots(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, source_file, _ = noncanonical_story_copy(tmp_path)
    original_default = {path.relative_to(ROOT): path.read_bytes() for path in DEFAULT_ROOT.rglob("*") if path.is_file()}
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload["story_root"] = str(DEFAULT_ROOT)
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: tree)

    result = free_gates_handler(ROOT, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert result == result.__class__(True, "free_gates", "all free gates passed")
    assert "\nparticipants:\n- kristin\n" in source_file.read_text(encoding="utf-8")
    assert free_gates_module.check_entry_snapshots(story_root) == []
    assert {
        path.relative_to(ROOT): path.read_bytes() for path in DEFAULT_ROOT.rglob("*") if path.is_file()
    } == original_default


def test_free_gates_checks_format_without_ticket_tree(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, source_file, before = noncanonical_story_copy(tmp_path)
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload.update({"story_root": str(story_root.relative_to(tree)), "entry_snapshots": False})
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: None)

    result = free_gates_handler(tree, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "story_format"
    assert "scenes/1A.yaml" in result.output
    assert "story_cli fmt" in result.output
    assert {path.relative_to(tree): path.read_bytes() for path in tree.rglob("*") if path.is_file()} == before
    assert "# inserted comment" in source_file.read_text(encoding="utf-8")


def test_free_gates_reports_format_refusals(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, _, _ = noncanonical_story_copy(tmp_path)
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload.update({"story_root": str(story_root.relative_to(tree)), "entry_snapshots": False})
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: tree)
    monkeypatch.setattr(
        free_gates_module,
        "format_source_tree",
        lambda root, *, check: ([], ["scenes/1A.yaml"]),
    )

    result = free_gates_handler(tree, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert not result.passed
    assert result.check == "story_format"
    assert "scenes/1A.yaml" in result.output
    assert "reformatting would change a value" in result.output


def test_free_gates_can_skip_story_format(tmp_path: Path, monkeypatch) -> None:
    tree, story_root, source_file, before = noncanonical_story_copy(tmp_path)
    payload = stub_gap_delta(monkeypatch, tmp_path / "gaps.json")
    payload.update({"story_root": str(story_root.relative_to(tree)), "entry_snapshots": False, "story_format": False})
    monkeypatch.setattr(free_gates_module, "ticket_tree", lambda *_args: None)
    monkeypatch.setattr(free_gates_module, "format_source_tree", lambda *args, **kwargs: pytest.fail("called"))

    result = free_gates_handler(tree, Runner([]))(make_ticket(payload, station=Station.FREE_GATES), NOW)

    assert result == result.__class__(True, "free_gates", "all free gates passed")
    assert source_file.read_text(encoding="utf-8") == before[source_file.relative_to(tree)].decode("utf-8")


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

    assert set(handlers) == {
        Station.WORLD_NEED,
        Station.FREE_GATES,
        Station.PROMPT_SNAPSHOT,
        Station.TRIAGE,
        Station.DELIVER,
    }
    assert Station.FUN_REVIEW in handlers
    assert Station.PROBE in handlers
    assert line.step(NOW).kind == "advanced"
    assert queue.get("ticket").station is Station.PROSE
