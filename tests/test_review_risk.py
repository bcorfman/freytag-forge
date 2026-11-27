import subprocess
import sys
from pathlib import Path

import pytest

from scripts.review_risk import _matches, classify_paths, detect_weakened_assertions, is_documentation_only, load_policy


@pytest.fixture
def policy() -> dict:
    return load_policy(Path(".github/review-policy.yml"))


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        (["docs/guide.md", ".plans/plan.py"], "ordinary"),
        (["frontend/App.jsx", "data/stories/intro.md"], "high"),
        (["README.md"], "low"),
        (["notes/anything.txt"], "ordinary"),
    ],
)
def test_tier_precedence_and_default(policy: dict, paths: list[str], expected: str) -> None:
    assert classify_paths(paths, policy) == expected


def test_glob_semantics(policy: dict) -> None:
    assert classify_paths(["docs/one/two.md"], policy) == "low"
    assert classify_paths(["docs/one/two.txt"], policy) == "ordinary"
    assert _matches("docs/one/two.md", "docs/**/*.md")
    assert not _matches("docs/one/two.md", "docs/*")


def test_highest_matching_tier_wins() -> None:
    policy = {
        "tiers": {
            "low": {"paths": ["shared/*"]},
            "ordinary": {"paths": []},
            "high": {"paths": ["shared/*"]},
        }
    }
    assert classify_paths(["shared/file.txt"], policy) == "high"


def test_documentation_only() -> None:
    assert is_documentation_only(["docs/guide.md", ".plans/plan.md", "LICENSE"])
    assert not is_documentation_only([".plans/plan.py"])
    assert not is_documentation_only(["data/stories/story.md"])
    assert not is_documentation_only([".github/workflows/test.yml"])


def test_name_status_parser_includes_both_rename_paths() -> None:
    from scripts.review_risk import _parse_changed_paths

    name_status = "R100\0docs/old.md\0storygame/runtime/new.py\0"
    assert _parse_changed_paths(name_status) == ["docs/old.md", "storygame/runtime/new.py"]


@pytest.mark.parametrize(
    ("diff", "expected"),
    [
        ("diff --git a/tests/test_x.py b/tests/test_x.py\n-    assert old\n+    value = 1\n", ["tests/test_x.py"]),
        ("diff --git a/tests/test_x.py b/tests/test_x.py\n+@pytest.mark.xfail\n", ["tests/test_x.py"]),
        ("diff --git a/tests/test_x.py b/tests/test_x.py\n+@pytest.mark.skipif(condition)\n", ["tests/test_x.py"]),
        ("diff --git a/tests/test_x.py b/tests/test_x.py\n+pytest.skip('reason')\n", ["tests/test_x.py"]),
        ("diff --git a/tests/test_x.py b/tests/test_x.py\n+pytest.xfail('reason')\n", ["tests/test_x.py"]),
        ("diff --git a/tests/test_x.py b/tests/test_x.py\n+pytest.importorskip('optional')\n", ["tests/test_x.py"]),
        ("diff --git a/tests/test_x.py b/tests/test_x.py\n-    assert old\n+    assert new\n+    assert more\n", []),
        ("diff --git a/tests/test_x.py b/tests/test_x.py\ndeleted file mode 100644\n", ["tests/test_x.py"]),
    ],
)
def test_weakened_assertion_heuristic(diff: str, expected: list[str]) -> None:
    assert detect_weakened_assertions(diff) == expected


def test_cli_reports_deleted_test_path_with_spaces(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    test_path = repo / "tests" / "test deleted assertion.py"
    test_path.parent.mkdir()
    test_path.write_text("assert old\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    test_path.unlink()
    subprocess.run(["git", "add", "-u"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "delete test"], cwd=repo, check=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts/review_risk.py"),
            "--base",
            base,
            "--head",
            head,
            "--policy",
            str(Path(__file__).parents[1] / ".github/review-policy.yml"),
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "- `tests/test deleted assertion.py`" in result.stdout
