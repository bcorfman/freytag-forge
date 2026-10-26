from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.ringer.environment_narration import defect_probe as probe
from scripts.ringer.environment_narration import smoke_direct


def _write_rows(path: Path, *, vocabulary: str = "made-up", real_words: bool = False) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if real_words:
        a_user = (
            "A context\nCONSTRAINTS:\n"
            "- Dr. Michelle McGehee may say this aloud: Kristin finds Michelle's memory card "
            "taped beneath the drawer and pockets it.\n"
            "- Show these in your reply: binder clips, pens, spare batteries, stapler.\n"
        )
        b_user = "B context\nCONSTRAINTS:\n- What presses on Kristin now: Find evidence of Michelle's disappearance.\n"
    else:
        a_user = f"{vocabulary} A\nCONSTRAINTS:\n- {vocabulary} cue aloud\n- {vocabulary} show\n"
        b_user = f"{vocabulary} B\nCONSTRAINTS:\n- {vocabulary} pressure\n"
    document = [
        {
            "turns": [
                {
                    "turn_index": 8,
                    "input": "inspect the passenger seat",
                    "prompts": [
                        {"system": "not narrator", "user": "wrong"},
                        {"system": "You are the narrator for B", "user": b_user},
                    ],
                },
                {
                    "turn_index": 3,
                    "input": "feel under the drawer",
                    "prompts": [{"system": "You are the narrator for A", "user": a_user}],
                },
            ]
        },
        {
            "turns": [
                {
                    "turn_index": 3,
                    "input": "feel under the drawer",
                    "prompts": [{"system": "You are the narrator other replicate", "user": "wrong replicate"}],
                }
            ]
        },
    ]
    raw = json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _build(tmp_path: Path, *, real_words: bool = False) -> Path:
    rows = tmp_path / "rows.json"
    source_sha = _write_rows(rows, real_words=real_words)
    probe_dir = tmp_path / "defect_probe"
    original_arms = probe.ARMS
    if not real_words:
        probe.ARMS = (
            {"id": "A0", "defect": "A", "prompt_id": "PA", "edits": ()},
            {"id": "A1", "defect": "A", "prompt_id": "PA", "edits": ({"op": "delete", "prefix": "- made-up cue"},)},
            {
                "id": "A2",
                "defect": "A",
                "prompt_id": "PA",
                "edits": ({"op": "delete", "prefix": "- made-up cue"}, {"op": "delete", "prefix": "- made-up show"}),
            },
            {
                "id": "A3",
                "defect": "A",
                "prompt_id": "PA",
                "edits": ({"op": "delete", "prefix": "- made-up cue"}, {"op": "add", "line": "- made-up empty"}),
            },
            {"id": "B0", "defect": "B", "prompt_id": "PB", "edits": ()},
            {
                "id": "B1",
                "defect": "B",
                "prompt_id": "PB",
                "edits": ({"op": "delete", "prefix": "- made-up pressure"},),
            },
            {"id": "B2", "defect": "B", "prompt_id": "PB", "edits": ({"op": "add", "line": "- made-up empty seat"},)},
            {
                "id": "B3",
                "defect": "B",
                "prompt_id": "PB",
                "edits": (
                    {"op": "delete", "prefix": "- made-up pressure"},
                    {"op": "add", "line": "- made-up empty seat"},
                ),
            },
        )
    try:
        assert (
            probe.main(
                [
                    "--build-prompts",
                    "--rows-source",
                    str(rows),
                    "--source-sha256",
                    source_sha,
                    "--probe-dir",
                    str(probe_dir),
                ]
            )
            == 0
        )
    finally:
        probe.ARMS = original_arms
    return probe_dir


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_extraction_uses_turn_index_and_replicate_zero(tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    document = _read(probe_dir / "prompts.json")
    assert document["prompts"]["PA"]["turn_index"] == 3
    assert document["prompts"]["PA"]["input"] == "feel under the drawer"
    assert document["prompts"]["PB"]["turn_index"] == 8
    assert document["prompts"]["PB"]["input"] == "inspect the passenger seat"
    assert document["prompts"]["PA"]["user"].startswith("made-up A")
    assert document["prompts"]["PB"]["user"].startswith("made-up B")


def test_wrong_source_hash_is_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rows = tmp_path / "rows.json"
    _write_rows(rows)
    assert probe.main(["--build-prompts", "--rows-source", str(rows), "--probe-dir", str(tmp_path / "out")]) != 0
    assert "sha256" in capsys.readouterr().err


def test_delete_zero_or_two_matches_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = tmp_path / "rows.json"
    _write_rows(rows)
    source_sha = hashlib.sha256(rows.read_bytes()).hexdigest()
    bad_arm = {"id": "A1", "defect": "A", "prompt_id": "PA", "edits": [{"op": "delete", "prefix": "- absent"}]}
    monkeypatch.setattr(probe, "ARMS", (bad_arm,))
    with pytest.raises(ValueError) as error:
        probe.build_prompts(rows, source_sha, tmp_path / "out")
    assert "A1" in str(error.value)

    bad_arm["edits"] = [{"op": "delete", "prefix": "- made-up"}]
    with pytest.raises(ValueError) as error:
        probe.build_prompts(rows, source_sha, tmp_path / "out")
    assert "A1" in str(error.value)


def test_add_without_constraints_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = tmp_path / "rows.json"
    _write_rows(rows)
    document = json.loads(rows.read_text(encoding="utf-8"))
    document[0]["turns"][1]["prompts"][0]["user"] = document[0]["turns"][1]["prompts"][0]["user"].replace(
        "CONSTRAINTS:", "NO CONSTRAINTS:"
    )
    rows.write_text(json.dumps(document), encoding="utf-8")
    source_sha = hashlib.sha256(rows.read_bytes()).hexdigest()
    bad_arm = {"id": "A1", "defect": "A", "prompt_id": "PA", "edits": [{"op": "add", "line": "- added"}]}
    monkeypatch.setattr(probe, "ARMS", (bad_arm,))
    with pytest.raises(ValueError) as error:
        probe.build_prompts(rows, source_sha, tmp_path / "out")
    assert "CONSTRAINTS" in str(error.value)


def test_real_arm_diffs_have_the_preregistered_line_changes(tmp_path: Path) -> None:
    probe_dir = _build(tmp_path, real_words=True)
    arms = {item["id"]: item for item in _read(probe_dir / "prompts.json")["arms"]}
    assert sum(line.startswith("-") and not line.startswith("---") for line in arms["A1"]["diff"].splitlines()) == 1
    assert sum(line.startswith("+") and not line.startswith("+++") for line in arms["A1"]["diff"].splitlines()) == 0
    assert sum(line.startswith("-") and not line.startswith("---") for line in arms["A3"]["diff"].splitlines()) == 1
    assert sum(line.startswith("+") and not line.startswith("+++") for line in arms["A3"]["diff"].splitlines()) == 1
    assert sum(line.startswith("-") and not line.startswith("---") for line in arms["B3"]["diff"].splitlines()) == 1
    assert sum(line.startswith("+") and not line.startswith("+++") for line in arms["B3"]["diff"].splitlines()) == 1


def test_build_is_byte_identical_twice(tmp_path: Path) -> None:
    first = _build(tmp_path / "first")
    second = _build(tmp_path / "second")
    assert (first / "prompts.json").read_bytes() == (second / "prompts.json").read_bytes()
    assert (first / "prompts.lock.json").read_bytes() == (second / "prompts.lock.json").read_bytes()


def test_plans_and_order(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    probe_dir = _build(tmp_path)
    assert probe.main(["--dry-run", "--stage", "1", "--probe-dir", str(probe_dir)]) == 0
    output = capsys.readouterr().out
    assert "A0=10" in output and "B3=10" in output
    assert "total calls: 80" in output
    assert "80 calls" in output


def test_stage_two_requires_non_control_candidates(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    probe_dir = _build(tmp_path)
    assert probe.main(["--dry-run", "--stage", "2", "--probe-dir", str(probe_dir)]) != 0
    assert probe.main(["--dry-run", "--stage", "2", "--arms", "A0", "--probe-dir", str(probe_dir)]) != 0
    assert probe.main(["--dry-run", "--stage", "2", "--arms", "A1,B1", "--probe-dir", str(probe_dir)]) == 0
    assert "60 calls" in capsys.readouterr().out
    plan = probe.planned_calls(_read(probe_dir / "prompts.json"), 2, ("A1", "B1"))
    assert len(plan) == 60
    first_ten = [call["context"] for call in plan[:10]]
    assert len(set(first_ten)) > 1


def test_lock_mismatch_refuses_dry_run_and_run(tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    lock = probe_dir / "prompts.lock.json"
    lock.write_text('{"count": 8, "sha256": "bad"}\n', encoding="utf-8")
    assert probe.main(["--dry-run", "--stage", "1", "--probe-dir", str(probe_dir)]) != 0
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                "10",
                "--out",
                str(tmp_path / "rows-out.json"),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        != 0
    )


def test_run_refusals(tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    common = [
        "--stage",
        "1",
        "--max-calls",
        "80",
        "--max-usd",
        "10",
        "--out",
        str(tmp_path / "out.json"),
        "--probe-dir",
        str(probe_dir),
    ]
    assert probe.main(["--run", *common]) != 0
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--out",
                str(tmp_path / "out.json"),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        != 0
    )
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                *common[:2],
                "--max-calls",
                "1",
                "--max-usd",
                "10",
                "--out",
                str(tmp_path / "out.json"),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        != 0
    )
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                "0.000001",
                "--out",
                str(tmp_path / "out.json"),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        != 0
    )


def _fake_row(call: dict, *, status: int = 200, usable: bool = True, cost: float = 0.0) -> dict:
    return {
        "call_index": call["call_index"],
        "variant": call["variant"],
        "model": call["model"],
        "start": call["start"],
        "context": call["context"],
        "sample": call["sample"],
        "status": status,
        "usable": usable,
        "repair_usable": usable,
        "narration": "reply" if usable else None,
        "final_text": "reply" if usable else None,
        "raw_response": "{}",
        "latency_ms": 1.0,
        "actual_cost_usd": cost,
    }


def test_run_writes_partial_rows_and_stops(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account-secret")
    monkeypatch.setenv("CLOUDFLARE_AI_TOKEN", "token-secret")
    output = tmp_path / "rows.json"
    calls = []

    def fake_call(account: str, token: str, call: dict) -> dict:
        calls.append(call.copy())
        return _fake_row(call, status=429)

    monkeypatch.setattr(probe, "_call", fake_call)
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                "10",
                "--out",
                str(output),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        == 0
    )
    document = _read(output)
    assert len(document["rows"]) == 1
    assert document["stop_reason"]
    assert "account-secret" not in output.read_text()
    assert "token-secret" not in output.read_text()
    assert calls[0]["variant"] == "llama-3.3-70b-default-temp"
    assert calls[0].get("request_bytes", True)


def test_run_stops_after_three_unusable_and_budget(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    output = tmp_path / "unusable.json"
    monkeypatch.setattr(probe, "_call", lambda account, token, call: _fake_row(call, usable=False))
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                "10",
                "--out",
                str(output),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        == 0
    )
    assert len(_read(output)["rows"]) == 3

    budget_output = tmp_path / "budget.json"
    monkeypatch.setattr(probe, "_call", lambda account, token, call: _fake_row(call, cost=0.6))
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                "1",
                "--out",
                str(budget_output),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        == 0
    )
    assert _read(budget_output)["stop_reason"] == "BUDGET"
    assert len(_read(budget_output)["rows"]) == 2


def test_urlopen_is_never_used_unpatched(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    output = tmp_path / "transport.json"

    def fail_urlopen(*args, **kwargs):
        raise AssertionError("network used")

    monkeypatch.setattr(smoke_direct, "urlopen", fail_urlopen)
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                "10",
                "--out",
                str(output),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        == 0
    )
    assert len(_read(output)["rows"]) == 3


def test_sheet_key_and_blind_text(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    first = tmp_path / "first.json"
    first.write_text(
        json.dumps(
            {
                "complete": True,
                "rows": [
                    _fake_row(
                        {"call_index": 1, "variant": "v", "model": "m", "start": "PA", "context": "A1", "sample": 0},
                        usable=True,
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    second = tmp_path / "second.json"
    second.write_text(
        json.dumps(
            {
                "complete": True,
                "rows": [
                    _fake_row(
                        {"call_index": 2, "variant": "v", "model": "m", "start": "PB", "context": "B1", "sample": 1},
                        usable=True,
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    sheet = tmp_path / "sheet.md"
    key = tmp_path / "key.json"
    assert (
        probe.main(["--sheet", "--rows", str(first), "--rows", str(second), "--out", str(sheet), "--key", str(key)])
        == 0
    )
    sheet_text = sheet.read_text()
    assert "A1" not in sheet_text and "B1" not in sheet_text
    assert "sample" not in sheet_text.lower()
    assert "call_index" not in sheet_text
    assert set(_read(key)) == {"r01", "r02"}
    assert "key sha256:" in capsys.readouterr().out


def _report_fixture(tmp_path: Path, counts: dict[str, int], n: int = 10) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    rows_path = tmp_path / "report-rows.json"
    key_path = tmp_path / "report-key.json"
    labels_path = tmp_path / "labels.json"
    rows = []
    key = {}
    labels = {}
    index = 1
    for arm, fails in counts.items():
        for sample in range(n):
            row = {
                "call_index": index,
                "context": arm,
                "sample": sample,
                "latency_ms": sample + 1,
                "actual_cost_usd": 0.01,
                "usable": True,
                "repair_usable": True,
            }
            rows.append(row)
            ident = f"r{index:02d}"
            key[ident] = {"arm": arm, "sample": sample, "call_index": index, "source": str(rows_path)}
            labels[ident] = {"verdict": "fail" if sample < fails else "pass", "note": ""}
            index += 1
    rows_path.write_text(json.dumps({"complete": True, "rows": rows}), encoding="utf-8")
    key_path.write_text(json.dumps(key), encoding="utf-8")
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    return rows_path, key_path, labels_path


def test_report_rules_and_incomplete_labels(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rows, key, labels = _report_fixture(
        tmp_path, {"A0": 3, "A1": 1, "A2": 2, "A3": 0, "B0": 3, "B1": 0, "B2": 0, "B3": 0}
    )
    report = tmp_path / "report.md"
    assert (
        probe.main(["--report", "--rows", str(rows), "--key", str(key), "--labels", str(labels), "--out", str(report)])
        == 0
    )
    text = report.read_text()
    assert "A: candidate A1" in text
    assert "B: candidate B1" in text

    labels_doc = _read(labels)
    labels_doc.pop(next(iter(labels_doc)))
    labels.write_text(json.dumps(labels_doc), encoding="utf-8")
    assert (
        probe.main(["--report", "--rows", str(rows), "--key", str(key), "--labels", str(labels), "--out", str(report)])
        != 0
    )
    assert "label" in capsys.readouterr().err


def test_report_control_not_reproduced_and_stage_two_gate(tmp_path: Path) -> None:
    rows, key, labels = _report_fixture(
        tmp_path, {"A0": 2, "A1": 0, "A2": 0, "A3": 0, "B0": 3, "B1": 1, "B2": 1, "B3": 1}, n=10
    )
    report = tmp_path / "stage1.md"
    assert (
        probe.main(["--report", "--rows", str(rows), "--key", str(key), "--labels", str(labels), "--out", str(report)])
        == 0
    )
    assert "A: not reproduced" in report.read_text()

    rows2, key2, labels2 = _report_fixture(
        tmp_path / "stage2", {"A0": 8, "A1": 1, "A2": 2, "A3": 0, "B0": 8, "B1": 2, "B2": 0, "B3": 0}, n=25
    )
    report2 = tmp_path / "stage2.md"
    assert (
        probe.main(
            ["--report", "--rows", str(rows2), "--key", str(key2), "--labels", str(labels2), "--out", str(report2)]
        )
        == 0
    )
    text = report2.read_text()
    assert "A1 stage 2 gate: PASS" in text
    assert "A2 stage 2 gate: FAIL" in text
    assert "B1 stage 2 gate: FAIL" in text


def _resume_document(probe_dir: Path, output: Path, count: int = 19, cost: float = 0.0) -> dict:
    plan = probe.planned_calls(_read(probe_dir / "prompts.json"), 1)
    rows = [_fake_row(call, cost=cost if index == 0 else 0.0) for index, call in enumerate(plan[:count])]
    document = {"schema": 1, "stage": 1, "rows": rows, "stop_reason": None, "complete": False}
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return document


def _resume_args(output: Path, probe_dir: Path, *extra: str) -> list[str]:
    return [
        "--run",
        "--resume",
        "--confirm",
        "--stage",
        "1",
        "--max-calls",
        "61",
        "--max-usd",
        "10",
        "--out",
        str(output),
        "--probe-dir",
        str(probe_dir),
        *extra,
    ]


def test_fresh_full_run_marks_complete(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    monkeypatch.setattr(
        smoke_direct, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used"))
    )
    monkeypatch.setattr(probe, "_call", lambda account, token, call: _fake_row(call))
    output = tmp_path / "complete.json"
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                "10",
                "--out",
                str(output),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        == 0
    )
    document = _read(output)
    assert document["complete"] is True
    assert len(document["rows"]) == 80
    assert document["stop_reason"] is None


@pytest.mark.parametrize(
    ("row_kwargs", "max_usd", "expected_stop"),
    [
        ({"status": 429}, 10.0, "429"),
        ({"usable": False}, 10.0, "UNUSABLE"),
        ({"cost": 0.6}, 1.0, "BUDGET"),
    ],
)
def test_stopped_run_is_not_complete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    row_kwargs: dict,
    max_usd: float,
    expected_stop: str,
) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    monkeypatch.setattr(probe, "_call", lambda account, token, call: _fake_row(call, **row_kwargs))
    output = tmp_path / f"{expected_stop}.json"
    assert (
        probe.main(
            [
                "--run",
                "--confirm",
                "--stage",
                "1",
                "--max-calls",
                "80",
                "--max-usd",
                str(max_usd),
                "--out",
                str(output),
                "--probe-dir",
                str(probe_dir),
            ]
        )
        == 0
    )
    document = _read(output)
    assert document["complete"] is False
    assert document["stop_reason"] == ("HTTP_429" if expected_stop == "429" else expected_stop)


def test_resume_completes_only_remaining_calls_and_records_marker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    output = tmp_path / "resume.json"
    before = _resume_document(probe_dir, output)
    before_rows = json.dumps(before["rows"], sort_keys=True)
    seen: list[int] = []

    def fake_call(account: str, token: str, call: dict) -> dict:
        seen.append(call["call_index"])
        return _fake_row(call)

    monkeypatch.setattr(probe, "_call", fake_call)
    assert probe.main(_resume_args(output, probe_dir)) == 0
    after = _read(output)
    assert seen == list(range(20, 81))
    assert json.dumps(after["rows"][:19], sort_keys=True) == before_rows
    assert len(after["rows"]) == 80
    assert after["complete"] is True
    assert after["resumed_at_call_index"] == [20]


@pytest.mark.parametrize("mutation", ["gap", "arm", "sample", "stop", "skipped", "stage", "complete"])
def test_resume_refuses_invalid_existing_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, mutation: str) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    output = tmp_path / "invalid-resume.json"
    document = _resume_document(probe_dir, output)
    if mutation == "gap":
        document["rows"][5]["call_index"] = 7
    elif mutation == "arm":
        document["rows"][5]["context"] = "B3"
    elif mutation == "sample":
        document["rows"][5]["sample"] = 99
    elif mutation == "stop":
        document["stop_reason"] = "BUDGET"
    elif mutation == "skipped":
        document["rows"][5]["skipped"] = True
    elif mutation == "stage":
        document["stage"] = 2
    else:
        document["complete"] = True
    output.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    original = output.read_bytes()
    calls: list[int] = []
    monkeypatch.setattr(
        probe, "_call", lambda account, token, call: calls.append(call["call_index"]) or _fake_row(call)
    )
    assert probe.main(_resume_args(output, probe_dir)) != 0
    assert calls == []
    assert output.read_bytes() == original


def test_resume_max_calls_uses_remaining_count(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    output = tmp_path / "resume-cap.json"
    _resume_document(probe_dir, output)
    calls: list[int] = []
    monkeypatch.setattr(
        probe, "_call", lambda account, token, call: calls.append(call["call_index"]) or _fake_row(call)
    )
    assert probe.main(_resume_args(output, probe_dir, "--max-calls", "60")) != 0
    assert calls == []
    assert probe.main(_resume_args(output, probe_dir, "--max-calls", "61")) == 0
    assert calls == list(range(20, 81))


def test_resume_budget_is_cumulative_and_estimate_includes_existing_cost(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    probe_dir = _build(tmp_path)
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "account")
    monkeypatch.setenv("CF_API_TOKEN", "token")
    output = tmp_path / "resume-budget.json"
    _resume_document(probe_dir, output, cost=0.02)
    calls: list[int] = []
    monkeypatch.setattr(
        probe, "_call", lambda account, token, call: calls.append(call["call_index"]) or _fake_row(call, cost=0.01)
    )
    assert probe.main(_resume_args(output, probe_dir, "--max-usd", "0.000001")) != 0
    assert calls == []
    assert "existing actual cost" in capsys.readouterr().err
    monkeypatch.setattr(probe, "_estimated_call_usd", lambda call: 0.0)
    assert probe.main(_resume_args(output, probe_dir, "--max-usd", "0.025")) == 0
    document = _read(output)
    assert calls == [20]
    assert document["stop_reason"] == "BUDGET"
    assert document["complete"] is False


def test_resume_dry_run_reports_remaining_and_spent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    probe_dir = _build(tmp_path)
    output = tmp_path / "resume-dry.json"
    _resume_document(probe_dir, output, cost=0.02)
    assert (
        probe.main(["--dry-run", "--resume", "--stage", "1", "--out", str(output), "--probe-dir", str(probe_dir)]) == 0
    )
    text = capsys.readouterr().out
    assert "existing rows: 19" in text
    assert "remaining calls: 61" in text
    assert "actual cost already spent: $0.020000" in text
    assert "estimated USD for remaining" in text


def test_sheet_and_report_require_complete_rows_unless_allowed(tmp_path: Path) -> None:
    rows, key, labels = _report_fixture(tmp_path, {"A0": 0}, n=1)
    rows_document = _read(rows)
    rows_document["complete"] = False
    rows.write_text(json.dumps(rows_document), encoding="utf-8")
    sheet = tmp_path / "sheet.md"
    sheet_key = tmp_path / "sheet-key.json"
    assert probe.main(["--sheet", "--rows", str(rows), "--out", str(sheet), "--key", str(sheet_key)]) != 0
    assert (
        probe.main(["--sheet", "--allow-partial", "--rows", str(rows), "--out", str(sheet), "--key", str(sheet_key)])
        == 0
    )
    report = tmp_path / "report.md"
    assert (
        probe.main(["--report", "--rows", str(rows), "--key", str(key), "--labels", str(labels), "--out", str(report)])
        != 0
    )
    assert (
        probe.main(
            [
                "--report",
                "--allow-partial",
                "--rows",
                str(rows),
                "--key",
                str(key),
                "--labels",
                str(labels),
                "--out",
                str(report),
            ]
        )
        == 0
    )
    rows_document = _read(rows)
    rows_document["complete"] = True
    rows.write_text(json.dumps(rows_document), encoding="utf-8")
    assert probe.main(["--sheet", "--rows", str(rows), "--out", str(sheet), "--key", str(sheet_key)]) == 0
    assert (
        probe.main(["--report", "--rows", str(rows), "--key", str(key), "--labels", str(labels), "--out", str(report)])
        == 0
    )
