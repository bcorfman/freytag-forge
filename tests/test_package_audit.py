from __future__ import annotations

from pathlib import Path

import yaml

from storygame.audit import _markdown, audit_package


def _package(tmp_path: Path, *, plot: str = "The house is quiet.", **files: object) -> Path:
    root = tmp_path / "package"
    root.mkdir()
    (root / "plot.md").write_text("## Scene 1A — House\n---\n" + plot, encoding="utf-8")
    defaults = {
        "knowledge.yaml": {"knowledge": [], "scene_frames": []},
        "world.yaml": {"protagonist_id": "kristin", "npcs": [], "locations": [], "items": []},
        "pacing.yaml": {"scenes": []},
        "storylet-routes.yaml": {"storylets": []},
        "storylets.md": "",
    }
    defaults.update(files)
    for name, value in defaults.items():
        path = root / name
        path.write_text(value if isinstance(value, str) else yaml.safe_dump(value), encoding="utf-8")
    return root


def _checks(report: dict) -> set[str]:
    return {finding["check"] for finding in report["findings"]}


def test_real_package_covers_all_scenes() -> None:
    report = audit_package(Path("data/stories/continuity-initiative"))
    assert report["scenes"] == ["1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"]


def test_unattested_detail_fixture(tmp_path: Path) -> None:
    root = _package(tmp_path, **{"knowledge.yaml": {"knowledge": [{"id": "k", "statement": "A ziggurat."}]}})
    report = audit_package(root)
    assert "unattested_detail" in _checks(report)
    assert "ziggurat" in str(report["findings"])


def test_frame_conflict_fixture(tmp_path: Path) -> None:
    root = _package(
        tmp_path,
        plot="The phone remains on the floor undamaged.",
        **{"knowledge.yaml": {"scene_frames": [{"scene_id": "1A", "situation": "The phone is facedown."}]}},
    )
    assert "frame_beat_conflict" in _checks(audit_package(root))


def test_absent_speaker_fixture(tmp_path: Path) -> None:
    root = _package(
        tmp_path,
        plot="participant_ids: [michelle]\nMichelle is missing.",
        **{"world.yaml": {"protagonist_id": "kristin", "npcs": [{"id": "michelle", "name": "Michelle"}]}},
    )
    assert "absent_speaker" in _checks(audit_package(root))


def test_overprojection_fixture(tmp_path: Path) -> None:
    storylets = """### SL-1A-A — Early
**Source beats:** [Early](plot.md#scene-1a1--early)
**Pacing window**
- earliest: `turn 0`
- latest: `turn 1`

### SL-1A-B — Late
**Source beats:** [Early](plot.md#scene-1a1--early)
**Pacing window**
- earliest: `turn 2`
- latest: `turn 2`
"""
    routes = {
        "storylets": [
            {"id": "SL-1A-A", "activation": {"pacing": {"earliest_turn": 0}}},
            {"id": "SL-1A-B", "activation": {"pacing": {"earliest_turn": 2}}},
        ]
    }
    root = _package(
        tmp_path,
        plot="### Scene 1A.1 — Early\nA beat.",
        **{"storylets.md": storylets, "storylet-routes.yaml": routes},
    )
    assert "beat_overprojection" in _checks(audit_package(root))


def test_prompt_hygiene_fixture(tmp_path: Path) -> None:
    root = _package(tmp_path, plot='entry_text: "hello\\n\\n"\nA house.')
    assert "prompt_hygiene" in _checks(audit_package(root))


def test_beats_without_turns_fixture(tmp_path: Path) -> None:
    root = _package(
        tmp_path,
        plot="### Scene 1A.1 — One\nA.\n### Scene 1A.2 — Two\nB.",
        **{"pacing.yaml": {"scenes": [{"scene_id": "1A", "handoff_after_turns": 1}]}},
    )
    assert "beats_without_turns" in _checks(audit_package(root))


def test_markdown_report_is_grouped_by_scene(tmp_path: Path) -> None:
    root = _package(tmp_path)
    markdown = _markdown(audit_package(root))
    assert markdown.index("## Scene 1A") < markdown.index("No findings.")
