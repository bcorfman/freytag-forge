from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/ringer/stage7/3c_families_offer_probe.py"
ROWS = Path("/home/bcorfman/dev/freytag-forge/bench/results/stage7-3c-escape-close-smoke/rows.json")


def load_probe():
    spec = importlib.util.spec_from_file_location("families_offer_probe", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dry_artifacts_and_exact_screen_diff(tmp_path: Path) -> None:
    probe = load_probe()
    assert probe.main(["--rows", str(ROWS), "--samples", "12", "--dry", "--out", str(tmp_path)]) == 0
    control = (tmp_path / "control.screen.txt").read_text()
    offer = (tmp_path / "offer.screen.txt").read_text()
    source_row = probe._source_row(ROWS)[0]
    expected = probe._player_screen(source_row["entry_text_shown"], probe._transcript(source_row, False))[0]
    assert control == expected
    assert control.count(probe.OLD_CUE) == 1
    assert offer.count(probe.OFFER_SENTENCE) == 1
    assert offer == control.replace(probe.OLD_CUE, probe.OFFER_CUE, 1)
    plan = json.loads((tmp_path / "plan.json").read_text())
    assert plan["call_count"] == 24 and plan["caps"]["raw_player"] == 24


def test_live_requires_confirm_and_caps_samples(tmp_path: Path) -> None:
    probe = load_probe()
    with pytest.raises(SystemExit, match="confirm"):
        probe.main(["--rows", str(ROWS), "--samples", "1", "--out", str(tmp_path)])
    with pytest.raises(SystemExit, match="12"):
        probe.main(["--rows", str(ROWS), "--samples", "13", "--confirm", "--out", str(tmp_path)])


def test_live_interleaves_24_mocked_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    probe = load_probe()
    calls = []

    def fake(screen, budget):
        calls.append(screen)
        return "Answer the families with news of the captives."

    monkeypatch.setattr(probe, "_ask_player", fake)
    assert probe.main(["--rows", str(ROWS), "--samples", "12", "--confirm", "--out", str(tmp_path)]) == 0
    rows = json.loads((tmp_path / "rows.json").read_text())
    assert len(rows) == 24
    assert [row["arm"] for row in rows[:4]] == ["control", "offer", "control", "offer"]
    assert all(probe.OFFER_SENTENCE not in calls[i] for i in range(0, 24, 2))
    assert all(probe.OFFER_SENTENCE in calls[i] for i in range(1, 24, 2))


def test_live_error_keeps_partial_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    probe = load_probe()
    count = 0

    def fake(screen, budget):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("child failed")
        return "Walk through the tunnel to the surface."

    monkeypatch.setattr(probe, "_ask_player", fake)
    with pytest.raises(RuntimeError, match="child failed"):
        probe.main(["--rows", str(ROWS), "--samples", "12", "--confirm", "--out", str(tmp_path)])
    rows = json.loads((tmp_path / "rows.json").read_text())
    assert len(rows) == 2 and "error" in rows[-1]
    assert (tmp_path / "run-failure.txt").exists()


def test_score_uses_real_post_c_selector(tmp_path: Path) -> None:
    probe = load_probe()
    (tmp_path / "rows.json").write_text(
        json.dumps(
            [
                {"arm": "control", "sample": 1, "command": "Answer the families with news of the captives."},
                {"arm": "offer", "sample": 1, "command": "Walk through the tunnel to the surface."},
            ]
        )
    )
    assert probe.main(["--score", "--out", str(tmp_path)]) == 0
    score = json.loads((tmp_path / "score.json").read_text())
    assert [item["reveal_id"] for item in score] == ["k_sl_3c_d_r2", None]
