import json
import subprocess
from pathlib import Path

import pytest

from factory.frozen import (
    changed_paths,
    glob_to_regex,
    is_frozen,
    load_patterns,
    main,
    touches_frozen,
)


def test_star_matches_only_within_one_segment():
    pattern = glob_to_regex("factory/*/guard.py")

    assert pattern.fullmatch("factory/checks/guard.py")
    assert not pattern.fullmatch("factory/checks/deep/guard.py")


def test_double_star_matches_across_segments():
    pattern = glob_to_regex("factory/**/guard.py")

    assert pattern.fullmatch("factory/guard.py")
    assert pattern.fullmatch("factory/checks/deep/guard.py")


def test_double_star_has_a_segment_boundary():
    assert is_frozen("factory/config/settings.json", ["factory/config/**"])
    assert not is_frozen("factory/configs/settings.json", ["factory/config/**"])


def test_exact_file_pattern_matches_only_that_file():
    assert is_frozen("factory/frozen.py", ["factory/frozen.py"])
    assert not is_frozen("factory/frozen.py.bak", ["factory/frozen.py"])


@pytest.mark.parametrize("path", ["/factory/frozen.py", "factory/../frozen.py", "./factory/../frozen.py"])
def test_absolute_and_parent_paths_are_rejected(path):
    with pytest.raises(ValueError):
        is_frozen(path, ["factory/**"])


def test_touches_frozen_is_sorted_deduplicated_and_normalized():
    paths = ["./factory/z.py", "factory/a.py", "factory/z.py", "docs/other.md"]

    assert touches_frozen(paths, ["factory/**"]) == ["factory/a.py", "factory/z.py"]


def test_load_patterns_reads_frozen_configuration(tmp_path):
    config = tmp_path / "frozen.json"
    config.write_text(json.dumps({"frozen": ["factory/*.py"]}), encoding="utf-8")

    assert load_patterns(config) == ["factory/*.py"]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            *args,
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(repo: Path, message: str) -> None:
    _git(repo, "commit", "-m", message)


def test_changed_paths_includes_modified_and_untracked_frozen_files(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    tracked = repo / "factory" / "frozen.py"
    tracked.parent.mkdir()
    tracked.write_text("before\n", encoding="utf-8")
    _git(repo, "add", "factory/frozen.py")
    _commit(repo, "initial")
    tracked.write_text("after\n", encoding="utf-8")
    untracked = repo / "factory" / "verdicts.py"
    untracked.write_text("new\n", encoding="utf-8")

    assert changed_paths(repo, "HEAD") == ["factory/frozen.py", "factory/verdicts.py"]


def test_main_returns_one_and_prints_frozen_paths(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "factory").mkdir()
    (repo / "factory" / "guard.py").write_text("before\n", encoding="utf-8")
    (repo / "README.md").write_text("readme\n", encoding="utf-8")
    _git(repo, "add", ".")
    _commit(repo, "initial")
    (repo / "factory" / "guard.py").write_text("after\n", encoding="utf-8")
    patterns = tmp_path / "patterns.json"
    patterns.write_text(json.dumps({"frozen": ["factory/**"]}), encoding="utf-8")

    assert main(["--repo", str(repo), "--base", "HEAD", "--patterns", str(patterns)]) == 1
    assert capsys.readouterr().out.splitlines() == ["factory/guard.py"]


def test_main_returns_zero_when_no_frozen_path_changed(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "README.md").write_text("before\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _commit(repo, "initial")
    (repo / "README.md").write_text("after\n", encoding="utf-8")
    patterns = tmp_path / "patterns.json"
    patterns.write_text(json.dumps({"frozen": ["factory/**"]}), encoding="utf-8")

    assert main(["--repo", str(repo), "--base", "HEAD", "--patterns", str(patterns)]) == 0
    assert capsys.readouterr().out == "ok\n"


def test_shipped_patterns_cover_guard():
    patterns = load_patterns(Path(__file__).parents[1] / "factory" / "config" / "frozen.json")

    assert is_frozen("factory/guard.py", patterns)
