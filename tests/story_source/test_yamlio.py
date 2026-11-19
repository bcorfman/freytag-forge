"""Tests for round-trip YAML source formatting."""

from __future__ import annotations

from pathlib import Path

import yaml

from storygame.story_source.yamlio import dumps_document, load_document

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "data" / "stories" / "continuity-initiative" / "source"


def test_committed_story_source_round_trips_byte_identically() -> None:
    for path in sorted(SOURCE_ROOT.rglob("*.yaml")):
        source = path.read_text(encoding="utf-8")

        assert dumps_document(load_document(path)) == source


def test_comments_and_key_order_survive_a_scalar_change(tmp_path: Path) -> None:
    path = tmp_path / "commented.yaml"
    path.write_text(
        "# file comment\nfirst: one # trailing comment\nsecond: two\nthird: three\n",
        encoding="utf-8",
    )

    document = load_document(path)
    document["second"] = "changed"
    dumped = dumps_document(document)

    assert "# file comment" in dumped
    assert "# trailing comment" in dumped
    assert list(document) == ["first", "second", "third"]
    assert dumped.index("first:") < dumped.index("second:") < dumped.index("third:")


def test_multiline_scalars_keep_their_values(tmp_path: Path) -> None:
    path = tmp_path / "multiline.yaml"
    source = 'block: |\n  first line\n  second line\n\nquoted: "quoted line\\n\\n"\n'
    path.write_text(source, encoding="utf-8")

    dumped = dumps_document(load_document(path))

    assert yaml.safe_load(dumped) == yaml.safe_load(source)
