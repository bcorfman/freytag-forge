from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/ringer/stage7/3c_families_offer_probe.py"
ROWS = Path("/home/bcorfman/dev/freytag-forge/bench/results/stage7-3c-escape-close-smoke/rows.json")


def load_probe():
    spec = importlib.util.spec_from_file_location("families_offer_probe", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
