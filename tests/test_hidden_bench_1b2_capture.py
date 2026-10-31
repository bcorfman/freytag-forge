from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ringer" / "environment_narration" / "hidden_bench_1b2_capture.py"
PACKAGE_ROOT = ROOT / "data" / "stories" / "continuity-initiative"


def _module():
    spec = importlib.util.spec_from_file_location("hidden_bench_1b2_capture", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_tampered_1b2_details_are_reported_as_exposure(tmp_path: Path) -> None:
    # A public beat detail containing a hidden clue name must be visible in Findings.
    tampered = tmp_path / "continuity-initiative"
    shutil.copytree(PACKAGE_ROOT, tampered)
    plot_path = tampered / "plot.md"
    plot = plot_path.read_text(encoding="utf-8")
    original = (
        "**Details:** stranger in the park; abandoned service tunnels; emergency patrol; Brandon Corfman; "
        "Michelle photograph; Continuity Initiative"
    )
    replacement = f"{original}; hidden clue Michelle photograph"
    assert original in plot
    plot_path.write_text(plot.replace(original, replacement, 1), encoding="utf-8")

    document = _module().capture_package(tampered)
    capture = next(
        item
        for item in document["captures"]
        if item["state"] == "unrecovered" and "michelle photograph" in item["hits"]
    )

    assert any(
        hit["section"] == "user" and "hidden clue michelle photograph" in hit["line"].casefold()
        for hit in capture["hits"]["michelle photograph"]
    )


def test_real_package_cli_writes_exactly_eight_captures(tmp_path: Path) -> None:
    # The hermetic CLI completes even when the exposure verdict is a finding.
    report_path = tmp_path / "report.md"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["TMPDIR"] = "/tmp"
    env.pop("CLOUDFLARE_WORKER_URL", None)
    env.pop("CLOUDFLARE_WORKER_TOKEN", None)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(report_path)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode in (0, 1), completed.stderr
    report = report_path.read_text(encoding="utf-8")
    rows = [line for line in report.splitlines() if line.startswith("| ") and line.split("|", 2)[1].strip().isdigit()]
    assert len(rows) == 8
    assert "Captures: 8." in report


def test_recovered_capture_state_uses_on_assert_world_effects() -> None:
    # Recovery is asserted as a fact; the package effect moves and reveals every clue.
    module = _module()
    package = load_story_package(PACKAGE_ROOT)
    state = module.build_state(package, recovered=True)
    world = world_for(package, state.facts)

    assert any(
        fact.predicate == "world_effects_applied" and fact.object == "bench_clues_recovered"
        for fact in state.facts.asserted
    )
    for item_id in ("transit_card", "number_sequence", "michelle_photograph"):
        assert world.parent(item_id) == "kristin"
        assert not world.is_hidden(item_id)


def test_json_mode_emits_capture_document(tmp_path: Path) -> None:
    # JSON mode remains machine-readable while the report file stays Markdown.
    report_path = tmp_path / "report.md"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["TMPDIR"] = "/tmp"
    env.pop("CLOUDFLARE_WORKER_URL", None)
    env.pop("CLOUDFLARE_WORKER_TOKEN", None)
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(report_path), "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode in (0, 1), completed.stderr
    assert len(json.loads(completed.stdout)["captures"]) == 8
    assert report_path.read_text(encoding="utf-8").startswith("# Scene 1B.2")
