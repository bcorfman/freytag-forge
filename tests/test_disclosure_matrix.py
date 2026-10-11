"""Checks for the generated disclosure review artifact."""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "disclosure_matrix.py"
PLANS = ROOT / ".plans"


def _run(out_dir: Path) -> None:
    subprocess.run(
        [sys.executable, str(SCRIPT), "--out-dir", str(out_dir)],
        cwd=ROOT,
        check=True,
        env={"PYTHONPATH": str(ROOT)},
    )


def _table_size(markdown: str, heading: str) -> int:
    section = markdown.split(f"### {heading}\n", 1)[1].split("### ", 1)[0]
    return sum(line.startswith("| ") for line in section.splitlines()) - 2


def test_matrix_is_deterministic_and_fresh(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _run(first)
    first_json = (first / "disclosure-matrix.json").read_bytes()
    _run(second)
    assert first_json == (second / "disclosure-matrix.json").read_bytes()
    assert (first / "disclosure-matrix.md").read_bytes() == (second / "disclosure-matrix.md").read_bytes()
    assert first_json == (PLANS / "disclosure-matrix.json").read_bytes()
    assert (first / "disclosure-matrix.md").read_bytes() == (PLANS / "disclosure-matrix.md").read_bytes()


def test_inventory_and_matrix_cover_guards_and_summary_tables() -> None:
    data = json.loads((PLANS / "disclosure-matrix.json").read_text(encoding="utf-8"))
    markdown = (PLANS / "disclosure-matrix.md").read_text(encoding="utf-8")
    kinds = {row["guard_kind"] for row in data["inventory"]}
    expected_kinds = {
        "entity_name",
        "identifier_fragment",
        "leak_term",
        "knowledge_alias",
        "must_convey_phrase",
        "scoped_alias",
    }
    assert kinds
    assert kinds <= expected_kinds
    assert all(row["guard_kind"] in kinds for row in data["matrix"])
    assert all(
        row[state]["verdict"] in {"accepted", "rejected"}
        for row in data["matrix"]
        for state in ("early", "earned", "skipped")
    )

    by_key = {(row["term"], row["guard_kind"]): row for row in data["inventory"]}
    earned_rejected = [row for row in data["matrix"] if row["earned"]["verdict"] == "rejected"]
    early_public = [
        row
        for row in data["matrix"]
        if row["early"]["verdict"] == "rejected"
        and by_key[(row["term"], row["guard_kind"])]["suggested_class"] == "public_candidate"
    ]
    early_secret = [
        row
        for row in data["matrix"]
        if row["early"]["verdict"] == "accepted"
        and by_key[(row["term"], row["guard_kind"])]["suggested_class"] == "secret_with_unlock_fact"
    ]
    assert _table_size(markdown, "Earned rejected") == len(earned_rejected)
    assert _table_size(markdown, "Early rejected public candidates") == len(early_public)
    assert _table_size(markdown, "Early accepted secret candidates") == len(early_secret)
    assert Counter(row["guard_kind"] for row in data["inventory"])
