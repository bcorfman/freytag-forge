from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import verifier_calibration as calibration

TOKEN = "calibration-test-secret"


def _case(case_id: str, *, category: str = "positive_plain", label: str = "accept") -> dict:
    return {
        "id": case_id,
        "story": "test setting",
        "category": category,
        "narration": "A green token rests on the table.",
        "relations": [{"thing": "green token", "place": "the table", "holder": None, "label": label}],
        "undetectable_invention": category == "invention_unreported",
        "note": "test note",
    }


def _write_corpus(root: Path, cases: list[dict]) -> None:
    corpus = root / "corpus"
    corpus.mkdir(exist_ok=True)
    (corpus / "cases-a.jsonl").write_text(
        "".join(json.dumps(case, sort_keys=True) + "\n" for case in cases), encoding="utf-8"
    )


def _configure_corpus(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(calibration, "CORPUS_DIR", root / "corpus")
    monkeypatch.setattr(calibration, "MIN_CASES", 1)


def test_validate_accepts_good_tiny_corpus_and_dry_run_is_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_corpus(monkeypatch, tmp_path)
    _write_corpus(tmp_path, [_case("one"), _case("two", label="reject")])
    monkeypatch.setattr(calibration, "JevClient", None)

    assert calibration.main(["--validate-corpus"]) == 0
    assert calibration.main(["--dry-run", "--samples", "2"]) == 0
    output = capsys.readouterr().out
    assert "cases: 2" in output
    assert "relations: 2" in output
    assert "planned requests: 4" in output
    assert "positive_plain" in output


@pytest.mark.parametrize(
    "mutate",
    [
        lambda case: case.pop("story"),
        lambda case: case.update({"relations": "bad"}),
        lambda case: case.update({"category": "unknown"}),
        lambda case: case.update({"undetectable_invention": True}),
        lambda case: case["relations"][0].update({"label": "maybe"}),
        lambda case: case["relations"][0].update({"place": "table", "holder": "someone"}),
    ],
)
def test_validate_rejects_each_broken_rule(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutate: object) -> None:
    _configure_corpus(monkeypatch, tmp_path)
    case = _case("broken")
    assert callable(mutate)
    mutate(case)
    _write_corpus(tmp_path, [case])
    assert calibration.main(["--validate-corpus"]) == 1


def test_validate_rejects_duplicate_ids_and_bad_reject_share(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_corpus(monkeypatch, tmp_path)
    _write_corpus(tmp_path, [_case("same"), _case("same")])
    assert calibration.main(["--validate-corpus"]) == 1

    _write_corpus(tmp_path, [_case("accept-only")])
    assert calibration.main(["--validate-corpus"]) == 1


def test_lock_write_and_mismatch_refusal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_corpus(monkeypatch, tmp_path)
    _write_corpus(tmp_path, [_case("one"), _case("two", label="reject")])
    assert calibration.main(["--validate-corpus", "--lock"]) == 0
    lock = tmp_path / "corpus" / "corpus.lock.json"
    assert lock.exists()
    assert calibration._lock_matches(calibration._load_corpus())
    (tmp_path / "corpus" / "cases-a.jsonl").write_text("changed\n", encoding="utf-8")
    assert calibration.main(["--run", "--confirm", "--out", str(tmp_path / "rows.json")]) == 2


@pytest.mark.parametrize(
    "extra_args",
    [
        ["--max-calls", "0"],
        ["--max-usd", "0"],
    ],
)
def test_run_guards_without_confirmation_caps_or_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, extra_args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    _configure_corpus(monkeypatch, tmp_path)
    _write_corpus(tmp_path, [_case("one")])
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", TOKEN)
    args = ["--run", "--out", str(tmp_path / "rows.json"), *extra_args]
    assert calibration.main(args) == 2
    assert TOKEN not in capsys.readouterr().out
    assert calibration.main(["--run", "--confirm", "--out", str(tmp_path / "rows.json"), "--max-calls", "0"]) == 2


class FakeClient:
    last_model = "fake-model"
    last_status = None

    def __init__(self) -> None:
        self.calls = 0

    def ask(self, _state: object, questions: object) -> dict:
        self.calls += 1
        return {key: {"noul": 0.8} for key in questions}


def test_fake_run_writes_after_each_call_and_stops_after_three_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_corpus(monkeypatch, tmp_path)
    cases = [_case(f"case-{index}", label="accept" if index < 2 else "reject") for index in range(4)]
    _write_corpus(tmp_path, cases)
    assert calibration.main(["--validate-corpus", "--lock"]) == 0

    client = FakeClient()
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", TOKEN)
    monkeypatch.setattr(calibration.JevClient, "from_environment", classmethod(lambda cls: client))

    writes: list[int] = []
    original_write = calibration._write_json

    def record_write(path: Path, document: dict) -> None:
        writes.append(len(document["rows"]))
        original_write(path, document)

    monkeypatch.setattr(calibration, "_write_json", record_write)
    output = tmp_path / "rows.json"
    assert calibration.main(["--run", "--confirm", "--samples", "1", "--max-calls", "4", "--out", str(output)]) == 0
    document = json.loads(output.read_text(encoding="utf-8"))
    assert writes == [1, 2, 3, 4]
    assert len(document["rows"]) == 4
    assert client.calls == 4

    class UnavailableClient(FakeClient):
        def ask(self, _state: object, _questions: object) -> None:
            self.calls += 1
            return None

    unavailable = UnavailableClient()
    monkeypatch.setattr(calibration.JevClient, "from_environment", classmethod(lambda cls: unavailable))
    output = tmp_path / "unavailable.json"
    assert calibration.main(["--run", "--confirm", "--samples", "1", "--max-calls", "4", "--out", str(output)]) == 0
    document = json.loads(output.read_text(encoding="utf-8"))
    assert len(document["rows"]) == 3
    assert document["stop_reason"] == "three_consecutive_unusable"


def _row(case_id: str, label: str, verdict: str, score: float | None, *, category: str = "positive_plain") -> dict:
    return {
        "call_index": 1,
        "case_id": case_id,
        "sample": 0,
        "story": "test setting",
        "category": category,
        "undetectable_invention": category == "invention_unreported",
        "narration_chars": 10,
        "relations": [{"thing": "token", "label": label, "verdict": verdict, "score": score}],
        "outcome": "ok" if verdict not in {"unavailable"} else "unavailable",
        "failure": None,
        "latency_ms": 10.0,
        "jev_model": "fake-model",
        "thresholds": {"accept_above": 0.65, "reject_below": 0.35},
        "question_version": "observation-relation-v1",
        "corpus_combined_hash": "hash",
    }


def test_report_arithmetic_gate_and_invention_section(tmp_path: Path) -> None:
    rows = [
        _row("false-accept", "reject", "accept", 0.9),
        _row("false-reject", "accept", "reject", 0.1),
        _row("uncertain", "accept", "uncertain", 0.5),
        _row("unavailable", "reject", "unavailable", None),
        _row("invention", "accept", "accept", 0.9, category="invention_unreported"),
    ]
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps({"rows": rows}), encoding="utf-8")
    report_path = tmp_path / "report.md"
    assert calibration.main(["--report", "--rows", str(rows_path), "--out", str(report_path)]) == 0
    report = report_path.read_text(encoding="utf-8")
    assert "FALSE ACCEPTS" in report and "Count: 1" in report
    assert "FALSE REJECTS" in report and "Count: 1" in report
    assert "Uncertain: 1" in report
    assert "Unavailable: 1" in report
    assert "zero observed false accepts on required relations: FAIL" in report
    assert "false rejects at most 5% of accept-labelled relations: FAIL" in report
    assert (
        "Unreported inventions are not detected by this verifier; these rows only confirm the required relation."
        in report
    )
    assert report.index("Invention-unreported cases") < report.index("GATE")
    assert "not the gate; do not tune and re-score on the same corpus" in report
    assert TOKEN not in report
