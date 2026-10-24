from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"
CHECKER = ROOT / "scripts/ringer/transcript_1a/check_live_baseline.py"
PYTHON = ROOT / ".venv/bin/python"


def test_dry_run_and_checker(tmp_path: Path) -> None:
    out = tmp_path / "dry"
    subprocess.run(
        [str(PYTHON), str(SCRIPT), "--dry-run", "--replicates", "1", "--turns", "2", "--out", str(out)], check=True
    )
    subprocess.run([str(PYTHON), str(CHECKER), str(out), "1", "--mode", "dry", "--turns", "2"], check=True)


def test_call_cap_keeps_partial_rows(tmp_path: Path) -> None:
    out = tmp_path / "cap"
    subprocess.run(
        [str(PYTHON), str(SCRIPT), "--dry-run", "--replicates", "1", "--out", str(out), "--max-calls", "1"], check=True
    )
    summary = json.loads((out / "summary.json").read_text())
    assert summary["stopped_reason"] == "MAX_CALLS_EXCEEDED"
    rows = json.loads((out / "rows.json").read_text())
    assert rows and rows[0]["turns"]


def test_live_quota_http_error_is_inspected_and_readable(monkeypatch: object) -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    body = b'{"error":"quota"}'

    def fail(*_args: object, **_kwargs: object) -> None:
        raise urllib.error.HTTPError(
            "https://worker.example/turn",
            429,
            "Too Many Requests",
            {"X-Narration-Error-Code": "AI_QUOTA_EXCEEDED"},
            io.BytesIO(body),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    counter = module.CallCounter(1, False)
    try:
        counter.live_urlopen(object())
    except urllib.error.HTTPError as error:
        assert error.read() == body
    else:
        raise AssertionError("expected HTTPError")
    assert counter.stop_reason == "AI_QUOTA_EXCEEDED"


def test_live_requires_confirmation_without_urlopen(monkeypatch: object, tmp_path: Path) -> None:
    module_spec = importlib.util.spec_from_file_location("live_baseline", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    called = False

    def fail(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True
        raise AssertionError("urlopen called")

    monkeypatch.setattr("urllib.request.urlopen", fail)
    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    assert module.main(["--out", str(tmp_path / "live")]) != 0
    assert not called
