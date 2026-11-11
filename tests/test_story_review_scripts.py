from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATHS = tuple(
    REPO_ROOT / "scripts" / name
    for name in ("gap_rules.py", "situation_trace.py", "impact_report.py", "branch_report.py")
)


def _load_script(path: Path):
    module_name = f"story_review_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("script_path", SCRIPT_PATHS, ids=lambda path: path.stem)
def test_story_review_scripts_use_repository_relative_defaults(script_path: Path) -> None:
    module = _load_script(script_path)
    source = script_path.read_text(encoding="utf-8")

    assert module.DEFAULT_ROOT.is_dir()
    assert module.DEFAULT_ROOT.is_relative_to(REPO_ROOT)
    assert "/home/" not in source
    assert module.main(["missing_anchor"]) == 2
