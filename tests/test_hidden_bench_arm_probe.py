from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.error import HTTPError

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/environment_narration/hidden_bench_arm_probe.py"


def _module():
    specification = importlib.util.spec_from_file_location("hidden_bench_arm_probe", SCRIPT)
    module = importlib.util.module_from_spec(specification)
    assert specification.loader is not None
    specification.loader.exec_module(module)
    return module


@pytest.fixture
def module():
    return _module()


@pytest.fixture
def document(module):
    return module.capture_payloads()


def _rows(module, document):
    rows = []
    for payload in document["payloads"]:
        if payload["state"] != "find":
            continue
        for sample in range(1, module.SAMPLES + 1):
            rows.append(
                {
                    "payload_id": payload["id"],
                    "arm": payload["arm"],
                    "state": payload["state"],
                    "sample": sample,
                    "response_text": json.dumps(
                        {
                            "segments": [{"kind": "narration", "text": "A quiet bench scene."}],
                            "selected_knowledge_ids": [],
                        }
                    ),
                    "composed_segments": payload["composed_segments"],
                }
            )
    return {"schema": 1, "stage": module.__name__, "calls_planned": 30, "rows": rows, "stop_reason": None}


def test_capture_is_hermetic_and_structurally_valid(module, monkeypatch) -> None:
    def no_http(*_args, **_kwargs):
        raise AssertionError("capture must not reach urlopen")

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", no_http)
    document = module.capture_payloads()

    assert {payload["id"] for payload in document["payloads"]} == {
        "base-opening",
        "base-inspect",
        "base-find",
        "B-opening",
        "B-inspect",
        "B-find",
        "C-inspect",
        "C-find",
    }
    assert module.validate_document(document) == []
    assert module.DELIVERY_TEXT in "\n".join(
        segment["text"] for segment in document["payloads"][-1]["composed_segments"]
    )


def test_package_tampering_and_payload_leak_fail_validation(module, document, tmp_path: Path) -> None:
    candidate = module._candidate_b(tmp_path)
    assert module._package_difference_errors(module.PACKAGE_ROOT, candidate) == []
    (candidate / "plot.md").write_text((candidate / "plot.md").read_text() + "extra\n", encoding="utf-8")
    assert module._package_difference_errors(module.PACKAGE_ROOT, candidate)

    injected = json.loads(json.dumps(document))
    opening = next(item for item in injected["payloads"] if item["id"] == "base-opening")
    opening["user"] += "\nMichelle's photograph"
    assert module.validate_document(injected)


def test_c_line_removal_requires_one_exact_match(module) -> None:
    with pytest.raises(ValueError):
        module._remove_exact_line("no matching line\n", module.REMOVED_LINE)
    with pytest.raises(ValueError):
        module._remove_exact_line(f"{module.REMOVED_LINE}\n{module.REMOVED_LINE}\n", module.REMOVED_LINE)


def test_dry_run_reports_thirty_calls_and_enforces_both_caps(module, document, monkeypatch, capsys) -> None:
    monkeypatch.setattr(module, "_capture_and_validate", lambda: document)

    assert module.main(["--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "planned calls: 30" in output
    assert "token estimate:" in output
    assert "USD ceiling:" in output
    assert module.main(["--dry-run", "--max-calls", "10"]) == 1
    assert "exceed --max-calls" in capsys.readouterr().err
    assert module.main(["--dry-run", "--max-usd", "0"]) == 1
    assert "exceeds --max-usd" in capsys.readouterr().err


def test_run_stops_on_429_without_a_sample_and_refuses_existing_or_missing_env(module, document, monkeypatch, tmp_path):
    output = tmp_path / "rows.json"
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "stub-token")

    def quota(*_args, **_kwargs):
        raise HTTPError("https://worker.invalid/turn", 429, "quota", {}, None)

    monkeypatch.setattr("storygame.runtime.cloudflare.CloudflareTurnProvider._request", quota)
    result = module.run_rows(document, max_calls=30, max_usd=0.03, out=output)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert result["rows"] == []
    assert saved["rows"] == []
    assert result["stop_reason"] == "http_429_quota_or_rate_limit"

    success_output = tmp_path / "success.json"
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.CloudflareTurnProvider._request",
        lambda *_args, **_kwargs: {
            "segments": [{"kind": "narration", "text": "Stub response."}],
            "selected_knowledge_ids": [],
        },
    )
    success = module.run_rows(document, max_calls=30, max_usd=0.03, out=success_output)
    assert success["stop_reason"] is None
    assert len(success["rows"]) == 30
    assert success["rows"][0]["composed_segments"]

    existing = tmp_path / "existing.json"
    existing.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError) as existing_error:
        module.run_rows(document, max_calls=30, max_usd=0.03, out=existing)
    assert "output file already exists" in str(existing_error.value)

    monkeypatch.delenv("CLOUDFLARE_WORKER_URL")
    monkeypatch.delenv("CLOUDFLARE_WORKER_TOKEN")
    refused = tmp_path / "refused.json"
    assert module.main(["--run", "--confirm", "--out", str(refused)]) == 1
    assert not refused.exists()


def test_sheets_hide_arm_and_key_is_bijection(module, document, monkeypatch, tmp_path: Path) -> None:
    rows_document = _rows(module, document)
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(rows_document), encoding="utf-8")
    monkeypatch.setattr(module, "_engine_segments", lambda _row: [{"kind": "narration", "text": "Engine text."}])
    output = tmp_path / "sheets"
    module.sheets(rows_path, output)

    sheet = (output / "blind_sheet.md").read_text(encoding="utf-8")
    key = json.loads((output / "blind_key.json").read_text(encoding="utf-8"))
    assert "base" not in sheet and "B" not in sheet and "C" not in sheet
    assert "Narrator:" in sheet
    assert "Engine (appended by the game):" in sheet
    module.assert_blind_key_bijection(rows_document["rows"], key)


def test_find_sheet_engine_part_keeps_delivery_without_capture_stub(module, document, tmp_path: Path) -> None:
    rows_document = _rows(module, document)
    for row in rows_document["rows"]:
        if row["arm"] == "base":
            row["response_text"] = "not valid JSON"
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(rows_document), encoding="utf-8")
    output = tmp_path / "sheets"

    module.sheets(rows_path, output)

    sheet = (output / "blind_sheet.md").read_text(encoding="utf-8")
    assert module.DELIVERY_TEXT in sheet
    assert "A short canned narration segment." not in sheet


def test_report_counts_each_arm_and_rejects_tampered_freeze(module, document, tmp_path: Path) -> None:
    rows_document = _rows(module, document)
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(json.dumps(rows_document), encoding="utf-8")
    sheets_path = tmp_path / "sheets"
    module.sheets(rows_path, sheets_path)
    template = json.loads((sheets_path / "labels_template.json").read_text(encoding="utf-8"))
    key = json.loads((sheets_path / "blind_key.json").read_text(encoding="utf-8"))
    for opaque_id, values in template.items():
        for name in module.LABEL_NAMES:
            values[name] = False
        values["attempted_lift_of_bench"] = key[opaque_id]["arm"] == "base"
    labels_path = sheets_path / "labels.json"
    module._write_json(labels_path, template)
    module.write_label_freeze(labels_path)

    report_path = tmp_path / "report.md"
    rendered = module.report(rows_path, labels_path, report_path)
    assert rendered.startswith("Diagnostic screen, 10 samples per arm. Counts only; proves no general rate.")
    assert "attempted_lift_of_bench: 10 true of 10" in rendered
    assert "attempted_lift_of_bench: 0 true of 10" in rendered
    assert report_path.read_text(encoding="utf-8") == rendered

    template[next(iter(template))]["meta_narration"] = True
    module._write_json(labels_path, template)
    with pytest.raises(ValueError) as hash_error:
        module.report(rows_path, labels_path, report_path)
    assert "sha256" in str(hash_error.value)
