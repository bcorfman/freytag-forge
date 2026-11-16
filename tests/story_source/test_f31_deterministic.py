from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from tests.story_source.helpers import copy_fixture, load_tree, patch_source, require_story_source

_DIGEST_SCRIPT = r"""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
files = {
    path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted(root.rglob("*.yaml"))
}
payload = {"schema_version": 1, "compiler_version": "fixture-test", "files": files}
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
payload["digest"] = hashlib.sha256(canonical).hexdigest()
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
"""


def _run_digest(root: Path) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, "-c", _DIGEST_SCRIPT, str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _run_compile(root: Path) -> str:
    script = (
        "import json, sys; "
        "from pathlib import Path; "
        "from storygame.story_source import compile_source_tree; "
        "package = compile_source_tree(Path(sys.argv[1])); "
        "print(json.dumps(package.model_dump(mode='json', by_alias=True), "
        "sort_keys=True, separators=(',', ':')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script, str(root)],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_deterministic_digest_helper_covers_schema_compiler_and_every_source_file(tmp_path: Path) -> None:
    first_root = copy_fixture("mini_ok", tmp_path / "first")
    second_root = copy_fixture("mini_ok", tmp_path / "second")
    first = _run_digest(first_root)
    second = _run_digest(second_root)

    assert first == second
    assert first["schema_version"] == 1
    assert first["compiler_version"] == "fixture-test"
    assert set(first["files"]) == set(load_tree(first_root))
    assert isinstance(first["digest"], str)
    assert len(first["digest"]) == hashlib.sha256().digest_size * 2


def test_deterministic_fixture_changes_only_the_story_title(tmp_path: Path) -> None:
    baseline = copy_fixture("mini_ok", tmp_path / "baseline")
    root = copy_fixture("mini_ok", tmp_path / "changed")
    patch_source(root, "story.yaml", "title", "Story 1373 deterministic fixture")

    baseline_tree = load_tree(baseline)
    changed_tree = load_tree(root)
    assert set(changed_tree) == set(baseline_tree)
    assert changed_tree["story.yaml"]["title"] == "Story 1373 deterministic fixture"
    assert {path for path in baseline_tree if baseline_tree[path] != changed_tree[path]} == {"story.yaml"}


def test_compiling_twice_in_two_processes_is_canonical_json_deterministic(tmp_path: Path) -> None:
    story_source = require_story_source()
    root = copy_fixture("mini_ok", tmp_path)
    patch_source(root, "story.yaml", "title", "Story 1373 deterministic fixture")
    assert story_source.check_source_tree(root) == []
    _ = story_source.compile_source_tree  # skips while the compiler is not built; the subprocesses need it

    assert _run_compile(root) == _run_compile(root)
