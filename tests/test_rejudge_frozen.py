from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import bench.rejudge_frozen as rejudge_frozen


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    package = repo / "data" / "stories" / "tiny"
    package.mkdir(parents=True)
    (package / "plot.md").write_text("old story\n", encoding="utf-8")
    first = _git(repo, "add", ".")
    assert first == ""
    first_revision = _git(repo, "commit", "-qm", "old")
    first_revision = _git(repo, "rev-parse", "HEAD")
    (package / "plot.md").write_text("new story\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "new")
    second_revision = _git(repo, "rev-parse", "HEAD")
    return repo, first_revision, second_revision


def _records(package_path: Path) -> dict:
    return {
        "package_path": str(package_path),
        "runs": [
            {
                "replicate": 7,
                "turns": [{"turn_number": 1, "narration": "A turn."}],
                "scene_transitions": [],
            }
        ],
    }


def test_extracts_package_at_requested_revision(tmp_path: Path) -> None:
    repo, first_revision, _ = _git_repo(tmp_path)

    extracted = rejudge_frozen.extract_package(repo, repo / "data/stories/tiny", first_revision)

    assert (extracted / "plot.md").read_text(encoding="utf-8") == "old story\n"
    assert extracted != repo / "data/stories/tiny"


def test_records_copy_and_summary_leave_source_untouched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, first_revision, _ = _git_repo(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    original = _records(repo / "data/stories/tiny")
    (source / "all-turn-records.json").write_text(json.dumps(original), encoding="utf-8")
    original_judgments = {
        "judgments": [{"turns": [{"turn": 1, "restarts_scene": "no", "protagonist_acts_beyond_command": "no"}]}],
        "judge_calls": 3,
    }
    (source / "continuity-judgments.json").write_text(json.dumps(original_judgments), encoding="utf-8")

    rejudged = {
        "judgments": [{"turns": [{"turn": 1, "restarts_scene": "yes", "protagonist_acts_beyond_command": "no"}]}],
        "judge_calls": 4,
    }

    def fake_continuity(input_path: Path, output_path: Path) -> dict:
        output_path.write_text(json.dumps(rejudged), encoding="utf-8")
        return rejudged

    monkeypatch.setattr(rejudge_frozen, "run_continuity_judges", fake_continuity)
    monkeypatch.setattr(rejudge_frozen, "run_fact_tracking_judges", pytest.fail)
    monkeypatch.setattr(rejudge_frozen, "load_story_package", lambda path: object())
    monkeypatch.setattr(
        rejudge_frozen,
        "judge_turns",
        lambda turns, transitions, package: [{"story_text_provenance": "reconstructed"} for _ in turns],
    )

    output = tmp_path / "output"
    rejudge_frozen.rejudge(source, first_revision, output, judges=("continuity",), repo_root=repo)

    copied = json.loads((output / "all-turn-records.json").read_text(encoding="utf-8"))
    assert copied["package_path"] != original["package_path"]
    assert copied["runs"] == original["runs"]
    assert copied["rejudge"] == {
        "source_records": str(source),
        "revision": first_revision,
        "original_package_path": original["package_path"],
        "provenance": "reconstructed",
    }
    assert json.loads((source / "all-turn-records.json").read_text(encoding="utf-8")) == original
    summary = json.loads((output / "rejudge-summary.json").read_text(encoding="utf-8"))
    assert summary["story_text_provenance"] == {"reconstructed": 1, "recorded": 0}
    assert summary["judges"]["continuity"] == {
        "judge_calls": 4,
        "yes_counts": {"contradicts_stated_fact": 0, "protagonist_acts_beyond_command": 0, "restarts_scene": 1},
        "original_judge_calls": 3,
        "original_yes_counts": {
            "contradicts_stated_fact": 0,
            "protagonist_acts_beyond_command": 0,
            "restarts_scene": 0,
        },
        "deltas": [{"replicate": 7, "turn": 1, "criterion": "restarts_scene", "original": "no", "rejudge": "yes"}],
    }


def test_refuses_output_equal_to_source(tmp_path: Path) -> None:
    repo, revision, _ = _git_repo(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "all-turn-records.json").write_text(json.dumps(_records(repo / "data/stories/tiny")), encoding="utf-8")

    with pytest.raises(ValueError, match="OUTDIR must differ from DIR"):
        rejudge_frozen.rejudge(source, revision, source, dry_run=True, repo_root=repo)


def test_bad_revision_has_clear_error(tmp_path: Path) -> None:
    repo, _, _ = _git_repo(tmp_path)

    with pytest.raises(ValueError, match="cannot extract package.*revision.*does-not-exist"):
        rejudge_frozen.extract_package(repo, repo / "data/stories/tiny", "does-not-exist")


def test_dry_run_does_not_call_judges(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    repo, revision, _ = _git_repo(tmp_path)
    source = tmp_path / "source"
    source.mkdir()
    (source / "all-turn-records.json").write_text(json.dumps(_records(repo / "data/stories/tiny")), encoding="utf-8")
    monkeypatch.setattr(rejudge_frozen, "run_continuity_judges", pytest.fail)
    monkeypatch.setattr(rejudge_frozen, "run_fact_tracking_judges", pytest.fail)

    output = tmp_path / "output"
    rejudge_frozen.rejudge(source, revision, output, dry_run=True, repo_root=repo)

    assert (output / "all-turn-records.json").exists()
    assert not (output / "rejudge-summary.json").exists()
    assert "would run continuity" in capsys.readouterr().out.lower()
