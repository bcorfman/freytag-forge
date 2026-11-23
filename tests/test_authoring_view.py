import json
import subprocess
import sys
from pathlib import Path

import yaml

from storygame.story_package.authoring_view import authoring_view
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
STORY_ROOT = ROOT / "data/stories/continuity-initiative"
LEGACY_ROOT = ROOT / "tests/fixtures/parity/continuity-initiative/legacy"

# Keys read by frontend/e2e/authored-spans.js, knowledge-available.js, and roleplay-judge.js.
KNOWLEDGE_KEYS_READ_BY_JS = {
    "id",
    "statement",
    "audience",
    "available_in_scenes",
    "establishes",
    "source",
    "delivery_text",
}
PACING_EVENT_KEYS_READ_BY_JS = {"id", "realizations"}
PACING_TRANSITION_KEYS_READ_BY_JS = {"id", "source_scene_id", "target_scene_id"}
ROUTE_EVENT_KEYS_READ_BY_JS = {"id", "produces", "fallback_text", "realization_storylets"}


def test_default_package_projects_all_legacy_sections():
    package = load_story_package(STORY_ROOT)
    view = authoring_view(package)

    assert set(view) == {"knowledge", "pacing", "handoffs", "routes", "frames"}
    legacy_knowledge = yaml.safe_load((LEGACY_ROOT / "knowledge.yaml").read_text())
    assert set(view["knowledge"]) == set(legacy_knowledge)
    assert all(
        item.get("delivery_text") == source.delivery_text
        for item, source in zip(view["knowledge"]["knowledge"], package.knowledge.knowledge, strict=True)
        if source.delivery_text
    )
    assert view["routes"]["canonical_bridge_events"]
    assert view["routes"]["canonical_resolution_events"]
    assert all(
        event.get("id")
        for section in ("canonical_bridge_events", "canonical_resolution_events")
        for event in view["routes"][section]
    )
    assert view["handoffs"]["deliveries"]
    assert all(delivery.get("fact_id") for delivery in view["handoffs"]["deliveries"])
    for scene in package.scenes:
        if scene.metadata.entry_text:
            assert view["frames"][scene.metadata.scene_id]["entry_text"] == scene.metadata.entry_text


def test_exported_records_cover_frontend_keys():
    package = load_story_package(STORY_ROOT)
    view = authoring_view(package)
    legacy = {
        name: yaml.safe_load((LEGACY_ROOT / name).read_text())
        for name in ("knowledge.yaml", "pacing.yaml", "storylet-routes.yaml")
    }

    assert all(set(item) >= KNOWLEDGE_KEYS_READ_BY_JS for item in view["knowledge"]["knowledge"])
    assert all(set(item) >= PACING_EVENT_KEYS_READ_BY_JS for item in view["pacing"]["events"])
    assert all(set(item) >= PACING_TRANSITION_KEYS_READ_BY_JS for item in view["pacing"]["transitions"])
    for section in ("canonical_bridge_events", "canonical_resolution_events"):
        assert all(set(item) >= ROUTE_EVENT_KEYS_READ_BY_JS for item in view["routes"][section])
    assert set(legacy["knowledge.yaml"]["knowledge"][0]) <= set(view["knowledge"]["knowledge"][0])
    assert set(legacy["pacing.yaml"]["events"][0]) <= set(view["pacing"]["events"][0])
    assert set(legacy["pacing.yaml"]["transitions"][0]) <= set(view["pacing"]["transitions"][0])


def test_export_is_json_round_trippable_and_deterministic():
    package = load_story_package(STORY_ROOT)
    first = authoring_view(package)
    second = authoring_view(package)
    assert first == second
    assert json.loads(json.dumps(first)) == first


def test_cli_prints_json_and_rejects_missing_root():
    environment = {"PYTHONPATH": f"{ROOT}:{ROOT / 'packages/worldkeeper/src'}", "TMPDIR": "/tmp"}
    command = [sys.executable, "-m", "storygame.story_package.authoring_view", str(STORY_ROOT)]
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert set(json.loads(result.stdout)) == {"knowledge", "pacing", "handoffs", "routes", "frames"}

    missing = subprocess.run(
        command[:-1] + [str(ROOT / "does-not-exist")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode != 0
    assert len(missing.stderr.strip().splitlines()) == 1
