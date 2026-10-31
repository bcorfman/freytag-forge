from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/ringer/environment_narration/opening_condition_v3.py"


def _tool():
    specification = importlib.util.spec_from_file_location("opening_condition_v3_test_tool", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _case(case_id: str, set_name: str, forbidden: bool, narration: str) -> dict[str, object]:
    return {
        "id": case_id,
        "set": set_name,
        "thing": "storm drain" if set_name == "drain" else "service gate",
        "command": "inspect the opening",
        "narration": narration,
        "declared": "the opening has no open or closed value, no declared contents, and is fixed in place.",
        "forbidden": forbidden,
        "source_ref": "test",
    }


def _rows(tool, cases, score_for, *, stop_reason=None):
    rows = []
    for case in cases:
        for sample in range(1, tool.SAMPLES + 1):
            rows.append(
                {
                    "case_id": case["id"],
                    "variant": "D",
                    "sample": sample,
                    "score": score_for(case),
                }
            )
    return {
        "samples": tool.SAMPLES,
        "calls_planned": len(cases) * tool.SAMPLES,
        "rows": rows,
        "stop_reason": stop_reason,
        "cases_sha256": tool._sha256(b"test-cases"),
    }


def test_lock_refuses_changed_case_hash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    tool = _tool()
    cases_path = tmp_path / "cases.jsonl"
    lock_path = tmp_path / "lock.json"
    cases_path.write_bytes(b"changed\n")
    lock_path.write_text(json.dumps({"cases_sha256": "old", "case_count": 180}))
    monkeypatch.setattr(tool, "CASES_PATH", cases_path)
    monkeypatch.setattr(tool, "LOCK_PATH", lock_path)

    with pytest.raises(ValueError, match="hash or count"):
        tool._load_cases()


def test_payload_uses_runtime_question() -> None:
    tool = _tool()
    from storygame.runtime.opening_check import OPENING_QUESTION

    state, questions = tool._payload(_case("case", "drain", False, "Only darkness."))
    assert set(state) == {"narration", "thing", "command", "declared"}
    assert questions == {"condition_consistent": OPENING_QUESTION}


def test_fake_reports_cover_pass_fail_inconclusive_and_relabelled_line(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tool = _tool()
    cases = [
        _case("drain-drain-row-030", "drain", True, "forbidden"),
        _case("drain-clean", "drain", False, "clean"),
        _case("opening-forbidden", "opening", True, "forbidden-opening"),
        _case("opening-clean", "opening", False, "clean-opening"),
        _case("heldout-clean", "heldout", False, "heldout"),
    ]
    monkeypatch.setattr(tool, "_load_cases", lambda: (cases, b"test-cases"))

    def run_report(name: str, score_for, stop_reason=None, document=None, relabelled=None) -> str:
        rows_path = tmp_path / f"{name}.json"
        report_path = tmp_path / f"{name}.md"
        relabelled_path = None
        if relabelled is not None:
            relabelled_path = tmp_path / f"{name}-relabelled.json"
            relabelled_path.write_text(json.dumps(relabelled))
        rows_path.write_text(
            json.dumps(document if document is not None else _rows(tool, cases, score_for, stop_reason=stop_reason))
        )
        tool.report_rows(rows_path, report_path, relabelled_path=relabelled_path)
        return report_path.read_text()

    class FakeClient:
        last_status = None
        last_model = "fake"
        last_version = "fake"

        def ask(self, state, questions):
            assert questions == {"condition_consistent": tool.OPENING_QUESTION}
            return {tool.QUESTION_KEY: {"noul": 0.1 if state["narration"].startswith("forbidden") else 0.9}}

    fake_run = tool._judge_rows(
        cases,
        samples=tool.SAMPLES,
        max_calls=len(cases) * tool.SAMPLES,
        max_usd=1,
        min_interval_s=0,
        out=tmp_path / "fake-run.json",
        cases_hash=tool._sha256(b"test-cases"),
        client=FakeClient(),
    )
    assert fake_run["stop_reason"] is None
    assert len(fake_run["rows"]) == len(cases) * tool.SAMPLES

    passing = run_report("pass", lambda case: 0.1 if case["forbidden"] else 0.9, document=fake_run)
    assert "Overall verdict: PASS" in passing
    assert "accepted=0 uncertain=0 rejected=1" in passing

    failing = run_report("fail", lambda case: 0.9 if case["forbidden"] else 0.1)
    assert "Overall verdict: FAIL" in failing

    partial = run_report("partial", lambda case: 0.1 if case["forbidden"] else 0.9, "max_calls")
    assert "Overall verdict: INCONCLUSIVE" in partial

    explicit = run_report("explicit", lambda case: 0.1 if case["forbidden"] else 0.9, relabelled=["drain-clean"])
    assert "accepted=1 uncertain=0 rejected=0" in explicit


def test_parser_accepts_case_lock_and_relabelled_paths(tmp_path: Path) -> None:
    tool = _tool()
    args = tool._parser().parse_args(
        [
            "--dry-run",
            "--cases",
            str(tmp_path / "cases.jsonl"),
            "--lock",
            str(tmp_path / "lock.json"),
            "--relabelled",
            str(tmp_path / "relabelled.json"),
        ]
    )
    assert args.cases == tmp_path / "cases.jsonl"
    assert args.lock == tmp_path / "lock.json"
    assert args.relabelled == tmp_path / "relabelled.json"


def test_dry_run_on_frozen_cases_plans_900_calls(capsys: pytest.CaptureFixture[str]) -> None:
    tool = _tool()
    assert tool.main(["--dry-run", "--max-usd", "0.05"]) == 0
    output = capsys.readouterr().out
    assert "planned calls: 900" in output
