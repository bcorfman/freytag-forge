from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.frozen_decode import analyze_rows, main

ROOT = Path(__file__).resolve().parents[1]
VARIATION = ROOT / "bench" / "variations" / "richer-3a-candidate.json"
REAL_ROWS = ROOT / "bench" / "results" / "richer-3a-probe" / "d1" / "d1-rows.json"


def _row(narration: str, *, n: int = 1, sample: int = 1, error: str | None = None) -> dict:
    return {
        "n": n,
        "sample": sample,
        "command": "Look around.",
        "narration": narration,
        "error": error,
        "raw": json.dumps({"narration": narration}),
    }


def _record(narration: str, **kwargs):
    return analyze_rows([_row(narration, **kwargs)], variation_path=VARIATION)["rows"][0]


def test_well_formed_reply_decodes_with_expected_segments() -> None:
    record = _record(
        json.dumps(
            {
                "segments": [
                    {"kind": "narration", "text": "Kristin waits."},
                    {"kind": "action", "text": "The lights hum."},
                ],
                "selected_knowledge_ids": [],
            }
        )
    )

    assert record["strict_json_parse"] is True
    assert record["decoder_result"]["segments_count"] == 2
    assert record["decoder_result"]["segment_kinds"] == ["narration", "action"]
    assert record["decoder_result"]["recovered"] is False


def test_truncated_item_facts_keeps_finished_segments_without_raising() -> None:
    narration = (
        '{"segments":[{"kind":"narration","text":"Kristin waits."}],'
        '"selected_knowledge_ids":[],"item_facts":{"Kristin":{"place":"detention'
    )

    record = _record(narration)

    assert record["strict_json_parse"] is False
    assert record["decoder_result"]["recovered"] is True
    assert record["decoder_result"]["segments_count"] == 1
    assert record["decoder_result"]["exception_type"] is None


def test_repeated_item_facts_keys_use_json_decoder_result() -> None:
    narration = (
        '{"segments":[{"kind":"narration","text":"Kristin waits."}],'
        '"selected_knowledge_ids":[],"item_facts":{"Kristin":{"condition":["old"]}},'
        '"item_facts":{"Kristin":{"condition":["new"]}}}'
    )

    record = _record(narration)

    assert record["strict_json_parse"] is True
    assert record["decoder_result"]["segments_count"] == 1
    assert record["proposed_item_facts"] == {"Kristin": {"place": None, "holder": None, "condition": ["new"]}}


def test_self_custody_is_reported_and_real_application_ignores_self_holder() -> None:
    narration = json.dumps(
        {
            "segments": [{"kind": "narration", "text": "Kristin waits."}],
            "selected_knowledge_ids": [],
            "item_facts": {"Kristin": {"held_by": "Kristin", "place": "detention level"}},
        }
    )

    record = _record(narration)

    assert record["self_custody"] is True
    assert record["validation_result"]["status"] == "accepted"
    assert record["item_fact_application"]["issues"] == []
    assert record["item_fact_application"]["would_commit"] == {}


def test_error_row_is_skipped_and_noted() -> None:
    report = analyze_rows([_row("not used", error="saved transport failure")])

    assert report["rows"] == []
    assert report["skipped"] == [{"n": 1, "sample": 1, "reason": "saved transport failure"}]
    assert report["summary"]["skipped"] == 1


def test_cli_writes_report(tmp_path: Path) -> None:
    rows = tmp_path / "rows.json"
    report = tmp_path / "report.json"
    rows.write_text(json.dumps([_row('{"segments":[{"kind":"narration","text":"Kristin waits."}]}')]), encoding="utf-8")

    assert main([str(rows), "--out", str(report), "--variation", str(VARIATION)]) == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["summary"]["processed"] == 1


@pytest.mark.skipif(not REAL_ROWS.is_file(), reason="recorded D1 rows are not present")
def test_real_d1_samples_4_to_6_are_supported() -> None:
    rows = json.loads(REAL_ROWS.read_text(encoding="utf-8"))
    selected = [row for row in rows if isinstance(row, dict) and row.get("n") == 4 and row.get("sample") in {4, 5, 6}]

    assert len(selected) == 3
    report = analyze_rows(selected, variation_path=VARIATION)
    assert len(report["rows"]) == 3
