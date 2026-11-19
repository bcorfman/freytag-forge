"""Tests for the deterministic prompt snapshot station."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

import factory.stations.prompt_snapshot as snapshots
from factory.line import StationResult
from factory.stations.prompt_snapshot import SnapshotError, capture_scene, diff_captures, unintended
from factory.tickets import Station, Ticket

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make_ticket(payload: dict) -> Ticket:
    return Ticket(
        id="ticket",
        scene="1A",
        station=Station.PROMPT_SNAPSHOT,
        token_budget=1000,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload=payload,
    )


def scripted_run(entry: str = "entry\n", beats: dict[str, str] | None = None):
    beats = beats or {"1A.1": "beat one\n", "1A.2": "beat two\n"}
    calls: list[tuple[list[str], dict]] = []

    def run(command: list[str], **kwargs):
        calls.append((command, kwargs))
        if "--list-beats" in command:
            stdout = "1A.1  First\n1A.2  Second\n\nSL-1A-A  Storylet\n"
        elif "--beat" in command:
            stdout = beats[command[command.index("--beat") + 1]]
        else:
            stdout = entry
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    return run, calls


def test_capture_scene_writes_entry_and_beats_and_passes_package(tmp_path: Path) -> None:
    run, calls = scripted_run()

    names = capture_scene("1A", tmp_path / "captures", root=ROOT, package="packages/custom", run=run)

    assert names == ["1A.beat-1A.1.txt", "1A.beat-1A.2.txt", "1A.entry.txt"]
    assert (tmp_path / "captures/1A.entry.txt").read_text() == "entry\n"
    assert (tmp_path / "captures/1A.beat-1A.1.txt").read_text() == "beat one\n"
    assert (tmp_path / "captures/1A.beat-1A.2.txt").read_text() == "beat two\n"
    assert len(calls) == 4
    assert all(command[command.index("--package") + 1] == "packages/custom" for command, _ in calls)
    assert all(kwargs == {"cwd": ROOT, "capture_output": True, "text": True, "timeout": 120} for _, kwargs in calls)


@pytest.mark.parametrize("failure", ["returncode", "timeout"])
def test_capture_scene_reports_command_failure_and_timeout(tmp_path: Path, failure: str) -> None:
    def run(command: list[str], **kwargs):
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], stderr="timed out here")
        return subprocess.CompletedProcess(command, 3, stdout="", stderr="failed here")

    with pytest.raises(SnapshotError, match="failed here|timed out here"):
        capture_scene("1A", tmp_path, root=ROOT, run=run)


def write_capture(directory: Path, name: str, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(text, encoding="utf-8")


def test_diff_captures_handles_identical_changed_new_removed_and_blank_lines(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    current = tmp_path / "current"
    write_capture(baseline, "same.txt", "same\n")
    write_capture(current, "same.txt", "same\n")
    write_capture(baseline, "changed.txt", "old\n")
    write_capture(current, "changed.txt", "new\n")
    write_capture(current, "new.txt", "added\n")
    write_capture(baseline, "removed.txt", "gone\n")
    write_capture(baseline, "blank.txt", "one\n\n")
    write_capture(current, "blank.txt", "one\n\n\n")

    assert diff_captures(baseline, current) == {
        "changed.txt": ["-old", "+new"],
        "new.txt": ["+added"],
        "removed.txt": ["-gone"],
    }


def test_unintended_supports_all_capture_aliases_and_new_capture(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    current = tmp_path / "current"
    for name in (
        "1B.entry.txt",
        "1B.beat-1B.4.txt",
        "1B.beat-1B.5.txt",
        "1B.beat-1B.6.txt",
        "1B.beat-1B.7.txt",
        "1B.beat-1B.9.txt",
    ):
        write_capture(baseline, name, "old\n")
    for name, text in (
        ("1B.entry.txt", "exact changed\n"),
        ("1B.beat-1B.4.txt", "entry changed\n"),
        ("1B.beat-1B.5.txt", "bare changed\n"),
        ("1B.beat-1B.6.txt", "star changed\n"),
        ("1B.beat-1B.7.txt", "unmatched changed\n"),
        ("1B.beat-1B.8.txt", "new\n"),
    ):
        write_capture(current, name, text)

    changes = diff_captures(baseline, current)
    allowed = [
        {"capture": "1B.entry.txt", "contains": ["old", "exact"]},
        {"capture": "entry", "contains": ["old", "entry changed"]},
        {"capture": "beat-1B.4", "contains": ["old", "entry changed"]},
        {"capture": "1B.5", "contains": ["old", "bare"]},
        {"capture": "*", "contains": ["old", "star"]},
        {"capture": "1B.8", "contains": ["never occurs"], "new_capture": True},
    ]

    assert unintended(changes, allowed, baseline, current) == [
        "1B.beat-1B.7.txt: +unmatched changed",
        "1B.beat-1B.9.txt: removed capture",
    ]

    assert unintended(
        {"1B.entry.txt": ["+changed"]},
        [{"capture": "1B.entry", "contains": ["changed"]}],
        baseline,
        current,
    ) == ["1B.entry.txt: +changed"]


def test_handler_passes_unchanged_and_allowed_line(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    run, _ = scripted_run()
    capture_scene("1A", baseline, root=ROOT, run=run)

    result = snapshots.prompt_snapshot_handler(ROOT, run=run)(make_ticket({"baseline_dir": baseline}), NOW)
    assert result == StationResult(True, "prompt_snapshot", "3 captures compared, 0 intended changed lines")

    changed_run, _ = scripted_run(entry="allowed line\n")
    (baseline / "1A.entry.txt").write_text("old line\n", encoding="utf-8")
    result = snapshots.prompt_snapshot_handler(ROOT, run=changed_run)(
        make_ticket(
            {
                "baseline_dir": baseline,
                "allowed_changes": [{"capture": "entry", "contains": ["old", "allowed"]}],
            }
        ),
        NOW,
    )
    assert result == StationResult(True, "prompt_snapshot", "3 captures compared, 2 intended changed lines")


def test_handler_fails_with_exact_unintended_line_and_caps_output(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    run, _ = scripted_run()
    capture_scene("1A", baseline, root=ROOT, run=run)
    failing_run, _ = scripted_run(entry="unexpected\n")
    result = snapshots.prompt_snapshot_handler(ROOT, run=failing_run)(make_ticket({"baseline_dir": baseline}), NOW)
    assert not result.passed
    assert result.output == "1A.entry.txt: -entry\n1A.entry.txt: +unexpected"

    write_capture(baseline, "1A.entry.txt", "old\n")
    huge_run, _ = scripted_run(entry="\n".join(f"line-{index}" for index in range(1000)))
    result = snapshots.prompt_snapshot_handler(ROOT, run=huge_run)(make_ticket({"baseline_dir": baseline}), NOW)
    assert not result.passed
    assert result.output.startswith("1A.entry.txt: -old\n1A.entry.txt: +line-0")
    assert "more lines cut" in result.output


def test_handler_plain_failures_and_temporary_directory_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    handler = snapshots.prompt_snapshot_handler(ROOT, run=lambda *args, **kwargs: None)
    missing_key = handler(make_ticket({}), NOW)
    assert missing_key.output == "missing payload key: baseline_dir"
    missing_dir = handler(make_ticket({"baseline_dir": tmp_path / "missing"}), NOW)
    assert "baseline directory does not exist" in missing_dir.output
    empty = tmp_path / "empty"
    empty.mkdir()
    assert "no baseline captures" in handler(make_ticket({"baseline_dir": empty}), NOW).output

    baseline = tmp_path / "baseline"
    write_capture(baseline, "1A.entry.txt", "same\n")
    temporary_paths: list[Path] = []

    def fake_capture(scene: str, out_dir: Path, **kwargs) -> list[str]:
        temporary_paths.append(out_dir)
        write_capture(out_dir, "1A.entry.txt", "same\n")
        return ["1A.entry.txt"]

    monkeypatch.setattr(snapshots, "capture_scene", fake_capture)
    result = snapshots.prompt_snapshot_handler(ROOT)(make_ticket({"baseline_dir": baseline}), NOW)
    assert result.passed
    assert temporary_paths and not temporary_paths[0].exists()


def test_real_bench_snapshot_round_trip_and_detects_baseline_edit(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    capture_scene("1A", baseline, root=ROOT)
    handler = snapshots.prompt_snapshot_handler(ROOT)
    result = handler(make_ticket({"baseline_dir": baseline}), NOW)
    assert result.passed
    assert result.output.endswith("0 intended changed lines")

    edited = sorted(baseline.glob("1A.*.txt"))[0]
    with edited.open("a", encoding="utf-8") as stream:
        stream.write("changed baseline line\n")
    result = handler(make_ticket({"baseline_dir": baseline}), NOW)
    assert not result.passed
    assert edited.name in result.output
