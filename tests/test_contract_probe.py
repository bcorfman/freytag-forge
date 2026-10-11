import json
import subprocess
import sys
from pathlib import Path


def test_contract_probe_dry_run_has_six_commands(tmp_path):
    report = tmp_path / "report.json"
    result = subprocess.run(
        [sys.executable, "bench/contract_probe.py", "--dry-run", "--samples", "1", "--out", str(report)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(report.read_text())
    assert payload["dry_run"] is True
    assert len(payload["rows"]) == 6
    assert "grants/N" in result.stdout


def test_contract_probe_corpus_has_three_commands_per_label():
    corpus = json.loads(Path("bench/variations/contract-probe-2c.json").read_text())["commands"]
    assert [item["label"] for item in corpus].count("positive") == 3
    assert [item["label"] for item in corpus].count("near-miss") == 3
    assert all(not item["command"].startswith("I ") and "do not" not in item["command"].casefold() for item in corpus)
