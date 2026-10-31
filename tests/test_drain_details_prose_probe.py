from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/environment_narration/drain_details_prose_probe.py"
DRAIN_FIXTURE = ROOT / "tests/fixtures/t9h_ci/probes/drain_details_smoke_rows.json"


def _module():
    specification = importlib.util.spec_from_file_location("drain_details_prose_probe", SCRIPT)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _complete_document(module, *, samples=None):
    samples = module.SAMPLES if samples is None else samples
    payloads = [{"id": arm, "arm": arm, "system": "system", "user": "user"} for arm in module.ARMS]
    rows = [
        {
            "call_index": index,
            "payload_id": payload["id"],
            "arm": payload["arm"],
            "sample": sample,
            "response_text": json.dumps({"segments": [{"kind": "narration", "text": "A reply."}]}),
        }
        for index, (payload, sample) in enumerate(
            ((payload, sample) for payload in payloads for sample in range(1, samples + 1)),
            start=1,
        )
    ]
    return {
        "schema": 1,
        "stage": module.STAGE,
        "samples": samples,
        "calls_planned": 2 * samples,
        "payloads": payloads,
        "rows": rows,
        "stop_reason": None,
        "prompt_metadata": {"recorded_offline_control_agree": False},
    }


def _write_rows(path: Path, document: dict) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def _labels_for_rows(
    module,
    rows_path: Path,
    output: Path,
    *,
    control_defect=True,
    candidate_defect=False,
    freeze=True,
):
    module.sheets(rows_path, output)
    labels_path = output / "labels.json"
    labels = json.loads((output / "labels_template.json").read_text())
    key = json.loads((output / "blind_key.json").read_text())
    for opaque_id, entry in key.items():
        labels[opaque_id] = {name: False for name in module.LABEL_NAMES}
        if entry["arm"] == "control" and control_defect and entry["sample"] == 1:
            labels[opaque_id][module.FORBIDDEN_LABELS[0]] = True
        if entry["arm"] == "candidate" and candidate_defect and entry["sample"] == 1:
            labels[opaque_id][module.FORBIDDEN_LABELS[0]] = True
    labels_path.write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
    if freeze:
        assert module.main(["--freeze-labels", "--labels", str(labels_path)]) == 0
    return labels_path


def test_capture_finds_recorded_prompt_and_validates_offline_arms() -> None:
    module = _module()
    document = module.capture_payloads(DRAIN_FIXTURE)

    assert {payload["arm"] for payload in document["payloads"]} == set(module.ARMS)
    assert document["payloads"][0]["system"].startswith("You are the narrator")
    assert module.RECORDED_DETAILS_TEXT in document["payloads"][0]["user"]
    assert document["offline_crosscheck"]["arms_differ_only_by_suffix"]
    assert "recorded_offline_control_agree" in document["offline_crosscheck"]


def test_recorded_prompt_without_details_fails(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    source = json.loads(DRAIN_FIXTURE.read_text())
    prompt = next(
        prompt for prompt in source[0]["turns"][5]["prompts"] if prompt["system"].startswith("You are the narrator")
    )
    prompt["user"] = prompt["user"].replace(module.RECORDED_DETAILS_TEXT, "- ordinary park bench", 1)
    edited = tmp_path / "rows.json"
    edited.write_text(json.dumps(source), encoding="utf-8")
    monkeypatch.setattr(module, "RECORDED_ROWS_PATH", edited)

    with pytest.raises(ValueError) as error:
        module.capture_payloads(offline_captures=[])
    assert "details" in str(error.value)


def test_control_and_candidate_differ_only_by_suffix() -> None:
    module = _module()
    document = module.capture_payloads(DRAIN_FIXTURE)
    control, candidate = document["payloads"]

    assert control["system"] == candidate["system"]
    assert candidate["user"] == control["user"].replace(
        module.RECORDED_DETAILS_TEXT,
        module.RECORDED_DETAILS_TEXT + module.CANDIDATE_SUFFIX,
        1,
    )


def test_dry_run_counts_twenty_and_refuses_caps(monkeypatch, capsys) -> None:
    module = _module()
    monkeypatch.setattr(module, "RECORDED_ROWS_PATH", DRAIN_FIXTURE)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)

    assert module.main(["--dry-run", "--max-calls", "20", "--max-usd", "0.03"]) == 0
    assert "planned calls: 20" in capsys.readouterr().out
    assert module.main(["--dry-run", "--max-calls", "19", "--max-usd", "0.03"]) == 1
    assert "exceed --max-calls" in capsys.readouterr().err
    assert module.main(["--dry-run", "--max-calls", "20", "--max-usd", "0"]) == 1
    assert "exceeds --max-usd" in capsys.readouterr().err


def test_run_without_confirmation_refuses(monkeypatch, capsys) -> None:
    module = _module()
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN", raising=False)

    assert module.main(["--run", "--max-calls", "20", "--max-usd", "0.03", "--out", "/tmp/rows.json"]) == 2
    assert "requires --confirm" in capsys.readouterr().err


def test_run_stops_on_429_without_replacing_a_sample(monkeypatch, tmp_path: Path) -> None:
    module = _module()
    document = _complete_document(module)
    output = tmp_path / "rows.json"
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "test-token")

    calls = 0

    def quota(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise HTTPError("https://worker.invalid/turn", 429, "quota", {}, None)
        return {"segments": [{"kind": "narration", "text": "A reply."}]}

    monkeypatch.setattr("storygame.runtime.cloudflare.CloudflareTurnProvider._request", quota)
    result = module.run_rows(document, max_calls=20, max_usd=0.03, out=output)

    assert len(result["rows"]) == 1
    assert "429" in result["stop_reason"]
    assert json.loads(output.read_text())["stop_reason"] == result["stop_reason"]


def test_sheets_are_blind_and_report_gate_cases(tmp_path: Path) -> None:
    module = _module()
    rows_path = tmp_path / "rows.json"
    _write_rows(rows_path, _complete_document(module))

    labels_path = _labels_for_rows(module, rows_path, tmp_path / "pass", control_defect=True, candidate_defect=False)
    sheet = (labels_path.parent / "blind_sheet.md").read_text()
    assert "control" not in sheet and "candidate" not in sheet
    report_path = tmp_path / "pass-report.md"
    rendered, passed = module.report(rows_path, labels_path, report_path)
    assert passed
    assert "screen: PASS" in rendered

    labels_path = _labels_for_rows(module, rows_path, tmp_path / "fail", control_defect=True, candidate_defect=True)
    rendered, passed = module.report(rows_path, labels_path, tmp_path / "fail-report.md")
    assert not passed
    assert "screen: FAIL" in rendered

    labels_path = _labels_for_rows(module, rows_path, tmp_path / "inconclusive", control_defect=False)
    rendered, passed = module.report(rows_path, labels_path, tmp_path / "inconclusive-report.md")
    assert not passed
    assert "INCONCLUSIVE" in rendered


def test_partial_run_is_inconclusive(tmp_path: Path) -> None:
    module = _module()
    document = _complete_document(module)
    document["rows"] = document["rows"][:3]
    document["stop_reason"] = "http_429_quota_or_rate_limit"
    rows_path = tmp_path / "partial.json"
    _write_rows(rows_path, document)
    labels_path = _labels_for_rows(module, rows_path, tmp_path / "partial", control_defect=True)

    rendered, passed = module.report(rows_path, labels_path, tmp_path / "partial-report.md")

    assert not passed
    assert "complete: no" in rendered
    assert "INCONCLUSIVE" in rendered


def test_sheets_do_not_freeze_null_template_and_report_requires_freeze(tmp_path: Path) -> None:
    module = _module()
    rows_path = tmp_path / "rows.json"
    _write_rows(rows_path, _complete_document(module))
    labels_path = _labels_for_rows(module, rows_path, tmp_path / "unfrozen", freeze=False)

    assert not (labels_path.parent / "labels.freeze.json").exists()
    with pytest.raises(ValueError) as error:
        module.report(rows_path, labels_path, tmp_path / "unfrozen-report.md")
    assert str(error.value) == "run --freeze-labels first"


def test_freeze_labels_rejects_null_and_conflicting_freeze(tmp_path: Path, capsys) -> None:
    module = _module()
    rows_path = tmp_path / "rows.json"
    output = tmp_path / "labels"
    _write_rows(rows_path, _complete_document(module))
    module.sheets(rows_path, output)
    labels_path = output / "labels_template.json"

    assert module.main(["--freeze-labels", "--labels", str(labels_path)]) == 1
    assert "null label" in capsys.readouterr().err

    labels = json.loads(labels_path.read_text())
    for entry in labels.values():
        for name in module.LABEL_NAMES:
            entry[name] = False
    labels_path.write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
    assert module.main(["--freeze-labels", "--labels", str(labels_path)]) == 0
    frozen = (output / "labels.freeze.json").read_text()

    labels[next(iter(labels))][module.LABEL_NAMES[0]] = True
    labels_path.write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
    assert module.main(["--freeze-labels", "--labels", str(labels_path)]) == 1
    assert "different hash" in capsys.readouterr().err
    assert (output / "labels.freeze.json").read_text() == frozen


def test_edited_labels_after_freeze_fail_hash_check(tmp_path: Path) -> None:
    module = _module()
    rows_path = tmp_path / "rows.json"
    _write_rows(rows_path, _complete_document(module))
    labels_path = _labels_for_rows(module, rows_path, tmp_path / "edited")
    labels = json.loads(labels_path.read_text())
    opaque_id = next(iter(labels))
    labels[opaque_id][module.LABEL_NAMES[0]] = not labels[opaque_id][module.LABEL_NAMES[0]]
    labels_path.write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError) as error:
        module.report(rows_path, labels_path, tmp_path / "edited-report.md")
    assert str(error.value) == "labels sha256 does not match the frozen labels hash"
